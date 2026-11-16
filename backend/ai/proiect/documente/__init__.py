"""Documents of a proposal, for download (P1 serves them, the web shows them in the "Documente" tab):

    build_documente(proiect, space) -> {"plan.svg": (bytes, media), "plan.dxf", "plansa.pdf", "dosar.pdf",
                                        "materiale.xlsx", "materiale.csv"}
    plan_json(proiect, space) -> dict        # Scene + suprafata_ocupata_mp
    materiale_json(proiect, space) -> dict   # ListaMateriale

`proiect` and `space` are dicts or ORM rows in the contract shape. The specification stored on the project is
used when present (so documents match what the user saw); otherwise it is rebuilt from the kind. Deterministic,
offline, no AI: the same project always gives the same bytes. Plots from the city hall's list are drawn 12 m wide.
"""
import csv
import io
import json
from typing import Any

from backend.ai.proiect.design import PLAN_DISCLAIMER, Scene, build_plan_dxf, build_plan_svg, build_scene
from backend.ai.proiect.design.scene import fmt
from backend.ai.proiect.design.svg import COLORS
from backend.ai.proiect.documente.pdf import MARGIN, PAGE_H, PAGE_W, Pdf
from backend.ai.proiect.documente.plansa import balance, build_plansa_pdf, indicators
from backend.ai.proiect.documente.xlsx import build_materiale_xlsx
from backend.ai.proiect.materiale import SURSE_RO, ListaMateriale, lista_materiale
from backend.ai.proiect.memoriu import CAPITOLE
from backend.ai.proiect.plots import LOT_WIDTH_M, from_city_hall_list
from backend.ai.proiect.spec import Specificatie, get_specificatie
from backend.ai.proiect.spec.model import CATEGORII_RO

MEDIA = {"plan.svg": "image/svg+xml", "plan.dxf": "application/dxf", "plansa.pdf": "application/pdf",
         "dosar.pdf": "application/pdf",
         "materiale.xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
         "materiale.csv": "text/csv; charset=utf-8"}
CONTRACT_DISCLAIMER = ("Estimare orientativă, bazată pe proiecte de referință. Nu reprezintă o autorizație; "
                       "acordul din aplicație este un acord de principiu simulat.")
STARI = {"draft": "ciornă", "publicat": "publicat (în vot)", "trimis": "trimis", "in_verificare": "în verificare",
         "clarificari": "clarificări", "acord_de_principiu": "acord de principiu (simulat)", "respins": "respins"}
NIVEL_RO = {"ok": "realistă", "atentie": "posibilă, cu aspecte de clarificat", "nerealist": "nerealistă pe acest teren"}


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
        if value not in (None, "", [], {}):
            return value
    return default


def _plain(value: Any) -> Any:
    """Pydantic model / JSON text / dict -> plain dict or list."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value or {}


def lei(value: float | None) -> str:
    return "-" if value is None else f"{round(value):,}".replace(",", ".") + " lei"


def spec_for(proiect: Any) -> Specificatie:
    stored = _plain(_get(proiect, "specificatie", default={}))
    if stored and stored.get("componente"):
        try:
            return Specificatie.model_validate(stored)
        except Exception:
            pass
    return get_specificatie(_get(proiect, "tip_amenajare", default="amenajare"), _get(proiect, "suprafata_mp"))


def scene_for(proiect: Any, space: Any = None, spec: Specificatie | None = None) -> Scene:
    area = _get(proiect, "suprafata_mp") or (_get(space, "suprafata_mp") if space is not None else None)
    if not area:
        raise ValueError("proiectul nu are suprafata_mp")
    listed = space is not None and from_city_hall_list(space)
    return build_scene(_get(proiect, "tip_amenajare", default="amenajare"), float(area),
                       LOT_WIDTH_M if listed else None, spec or spec_for(proiect))


def _title(proiect: Any, scene: Scene) -> str:
    return _plain(_get(proiect, "dosar", default={})).get("titlu") or f"Amenajare: {scene.eticheta}"


def plan_json(proiect: Any, space: Any = None) -> dict:
    scene = scene_for(proiect, space)
    pot, cut = indicators(scene)
    return {**scene.model_dump(), "suprafata_ocupata_mp": scene.suprafata_ocupata_mp,
            "bilant": [{"zona": z, "mp": mp, "procent": pct} for z, mp, pct in balance(scene)],
            "pot_procent": pot, "cut": cut}


def materiale_json(proiect: Any, space: Any = None) -> dict:
    spec = spec_for(proiect)
    return lista_materiale(scene_for(proiect, space, spec), spec).model_dump()


def _num(value: float | None) -> str:
    return "" if value is None else fmt(value)


def materiale_csv(lista: ListaMateriale) -> bytes:
    """Semicolon-separated, decimal comma, UTF-8 with BOM: opens directly in a Romanian Excel."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    w.writerow(["capitol", "articol", "denumire", "cantitate", "unitate", "pret_unitar_median_lei", "pret_min_lei",
                "pret_max_lei", "tip_sursa", "observatii", "valoare_lei", "stare", "motiv", "ipoteza_cantitate", "surse"])
    for l in lista.linii:
        p = l.pret_unitar
        w.writerow([l.capitol, l.articol or "", l.nume, _num(l.cantitate), l.unitate, _num(p.mediana_lei if p else None),
                    _num(p.min_lei if p else None), _num(p.max_lei if p else None), l.tip_sursa or "",
                    p.observatii if p else "", _num(l.valoare_lei), l.stare.replace("_", " "), l.motiv, l.ipoteza,
                    " ".join(p.surse) if p else ""])
    w.writerow([])
    w.writerow([lista.eticheta_subtotal, "", "", "", "", "", "", "", "", "", _num(lista.subtotal_cotat_lei)])
    for note in (lista.sursa_preturi, lista.tva, lista.disclaimer):
        w.writerow([note])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _draw_plan(pdf: Pdf, scene: Scene) -> None:
    pdf.new_page()
    pdf.heading("Plan schematic (extras; planșele A3 sunt în plansa.pdf)")
    box_w, box_h = PAGE_W - 2 * MARGIN - 30, 400.0
    s = min(box_w / scene.latime_m, box_h / scene.lungime_m)
    x0, y0 = MARGIN + 30, pdf.y + 4
    X = lambda x: x0 + x * s  # noqa: E731
    Y = lambda y: y0 + (scene.lungime_m - y) * s  # noqa: E731  (plan y is up)
    pdf.rect(X(0), Y(scene.lungime_m), scene.latime_m * s, scene.lungime_m * s, fill="#eef4e8",
             stroke="#2f4f2f", width=1.2)
    for i, e in enumerate(scene.elemente, 1):
        z = e.zona_libera_m
        if z:
            pdf.rect(X(e.x - z), Y(e.y + e.lungime_m + z), (e.latime_m + 2 * z) * s, (e.lungime_m + 2 * z) * s,
                     stroke="#888888", width=0.4, dash=True)
        pdf.rect(X(e.x), Y(e.y + e.lungime_m), e.latime_m * s, e.lungime_m * s,
                 fill=COLORS.get(e.tip, "#cccccc"), stroke="#333333", width=0.5)
        size = 7 if min(e.latime_m, e.lungime_m) * s >= 9 else 5
        pdf.text_at(X(e.x + e.latime_m / 2) - 3, Y(e.y + e.lungime_m / 2) - size / 2, str(i), size)
    bottom = Y(0)
    pdf.line(X(0), bottom + 10, X(scene.latime_m), bottom + 10, 0.6)
    pdf.text_at(X(scene.latime_m / 2) - 12, bottom + 13, f"{fmt(scene.latime_m)} m", 8)
    pdf.line(x0 - 12, Y(0), x0 - 12, Y(scene.lungime_m), 0.6)
    pdf.text_at(MARGIN - 6, Y(scene.lungime_m / 2) - 4, f"{fmt(scene.lungime_m)} m", 8)
    pdf.y = bottom + 30
    pdf.paragraph("Legendă", size=10, bold=True, after=2)
    for i, e in enumerate(scene.elemente, 1):
        pdf.paragraph(f"{i}. {e.nume} ({fmt(e.latime_m)} × {fmt(e.lungime_m)} m)", size=8.5, after=0)
    for o in scene.omise:
        pdf.paragraph(f"Nu încape: {o.nume}" + (f" (× {o.bucati})" if o.bucati > 1 else "") + f" – {o.motiv}",
                      size=8.5, color="#a33a1d", after=0)
    pdf.y += 4
    pdf.paragraph("Bilanț teritorial (orientativ): " + "; ".join(f"{z} {fmt(mp)} mp ({fmt(pct)} %)"
                                                                 for z, mp, pct in balance(scene)), size=8, after=2)
    pot, cut = indicators(scene)
    pdf.paragraph(f"POT propus ≈ {fmt(pot)} %, CUT propus ≈ {fmt(cut)} (un nivel; valori orientative).", size=8, after=4)
    for note in (*scene.ipoteze, PLAN_DISCLAIMER):
        pdf.paragraph(note, size=8, color="#555555", after=1)


def _draw_materials(pdf: Pdf, lista: ListaMateriale) -> None:
    pdf.new_page()
    pdf.heading("Listă de materiale (orientativă; detaliu în materiale.xlsx)")
    cols = [MARGIN, MARGIN + 215, MARGIN + 290, MARGIN + 395]
    for x, head in zip(cols, ("Articol", "Cantitate", "Preț unitar (mediană)", "Valoare")):
        pdf.text_at(x, pdf.y, head, 8.5, bold=True)
    pdf.y += 14
    current = None
    for l in lista.linii:
        if l.capitol != current:
            current = l.capitol
            pdf.ensure(30)
            pdf.y += 4
            pdf.paragraph(current, size=9, bold=True, after=2)
        p = l.pret_unitar
        pdf.ensure(34)
        top = pdf.y
        pdf.text_at(cols[0], top, l.nume[:48], 8.5)
        pdf.text_at(cols[1], top, f"{fmt(l.cantitate)} {l.unitate}", 8.5)
        if p:
            pdf.text_at(cols[2], top, f"{lei(p.mediana_lei)}/{l.unitate}", 8.5)
            pdf.text_at(cols[3], top, lei(l.valoare_lei), 8.5)
            src = SURSE_RO.get(p.tip_sursa, p.tip_sursa)
            detail = (f"{src}; min–max {lei(p.min_lei)} – {lei(p.max_lei)}, {p.observatii} observații ({p.perioada}); "
                      f"{', '.join(p.surse)}. Cantitate: {l.ipoteza}.")
        else:
            pdf.text_at(cols[2], top, "de cotat", 8.5, bold=True, color="#a33a1d")
            detail = f"{l.motiv}. Cantitate: {l.ipoteza}."
        pdf.y = top + 12
        pdf.paragraph(detail, size=7, indent=8, color="#555555", after=3)
    pdf.y += 4
    pdf.paragraph(f"{lista.eticheta_subtotal}: {lei(lista.subtotal_cotat_lei)}", size=10, bold=True)
    if lista.articole_necotate:
        pdf.paragraph("De cotat (fără sursă de preț verificată): " + "; ".join(lista.articole_necotate), size=8,
                      color="#a33a1d")
    for note in (lista.sursa_preturi + ". " + lista.tva + ".", lista.disclaimer):
        pdf.paragraph(note, size=8, color="#555555", after=2)


def _draw_spec(pdf: Pdf, spec: Specificatie) -> None:
    pdf.heading("Specificație tehnică orientativă")
    pdf.paragraph(f"Tip: {spec.eticheta}. Suprafață minimă considerată: {fmt(spec.suprafata_minima_mp)} mp"
                  + (f"; recomandată: {fmt(spec.suprafata_recomandata_mp)} mp" if spec.suprafata_recomandata_mp else "")
                  + ". Utilități necesare: " + (", ".join(spec.utilitati_toate()) or "niciuna") + ".", size=9)
    for key, label in CATEGORII_RO.items():
        comps = [c for c in spec.componente if c.categorie == key]
        if not comps:
            continue
        pdf.paragraph(label, size=9, bold=True, after=1)
        for c in comps:
            dims = (f"{fmt(c.latime_m)} × {fmt(c.lungime_m)}" + (f" × h {fmt(c.inaltime_m)}" if c.inaltime_m else "") + " m"
                    if c.are_amprenta else f"{fmt(c.cantitate)} {c.unitate}")
            pdf.paragraph(f"{c.nume} ({dims})" + (" – obligatoriu" if c.obligatoriu else "") + (f": {c.rol}" if c.rol else ""),
                          size=8.5, bullet="•", after=0)
        pdf.y += 3
    for note in (*spec.ipoteze, spec.disclaimer):
        pdf.paragraph(note, size=8, color="#555555", after=1)


def build_dosar_pdf(proiect: Any, space: Any = None, scene: Scene | None = None,
                    lista: ListaMateriale | None = None) -> bytes:
    spec = spec_for(proiect)
    scene = scene or scene_for(proiect, space, spec)
    lista = lista or lista_materiale(scene, spec)
    dosar = _plain(_get(proiect, "dosar", default={}))
    cost = _plain(_get(proiect, "cost", default={}))
    fez = _plain(_get(proiect, "fezabilitate", default={}))
    refs = _plain(_get(proiect, "referinte", default=[])) or []
    demo = bool(_get(proiect, "is_demo", default=False))
    pdf = Pdf(footer="Loc Comun · dosar generat automat" + (" · exemplu (date demonstrative)" if demo else ""))

    pdf.paragraph(_title(proiect, scene), size=17, bold=True, after=2)
    place = _get(space, "nume", "name") if space is not None else None
    meta = [scene.eticheta, f"{fmt(scene.suprafata_mp)} mp"]
    if place:
        meta.append(str(place))
    if _get(space or {}, "cartier", "neighborhood"):
        meta.append(f"cartierul {_get(space, 'cartier', 'neighborhood')}")
    if _get(proiect, "stare"):
        meta.append(f"stare: {STARI.get(_get(proiect, 'stare'), _get(proiect, 'stare'))}")
    if _get(proiect, "voturi") is not None:
        meta.append(f"susținători: {_get(proiect, 'voturi', default=0)}")
    pdf.paragraph(" · ".join(meta), size=9.5, color="#555555", after=8)
    if space is not None and from_city_hall_list(space):
        pdf.paragraph("Teren din lista Primăriei (Legea 15/2003), de confirmat: poate fi atribuit între timp.",
                      size=9, color="#a33a1d")
    pdf.paragraph(CONTRACT_DISCLAIMER, size=9, bold=True, color="#8a4b00", after=8)

    if fez:
        pdf.heading("Analiza fezabilității (orientativă)")
        pdf.paragraph(f"Concluzie: propunere {NIVEL_RO.get(fez.get('nivel'), fez.get('nivel'))} (scor orientativ "
                      f"{fez.get('scor')}/100). {fez.get('rezumat', '')}", bold=True)
        for item in fez.get("motive") or []:
            pdf.paragraph(item, size=9, bullet="•", after=1)
        if fez.get("recomandari"):
            pdf.paragraph("Recomandări:", size=9, bold=True, after=1)
            for item in fez["recomandari"]:
                pdf.paragraph(item, size=9, bullet="•", after=1)
        pdf.paragraph(fez.get("disclaimer", ""), size=8, color="#555555")

    memoriu = dosar.get("memoriu") or {}
    if memoriu:
        pdf.heading("Memoriu descriptiv")
        for key, label in CAPITOLE:
            if memoriu.get(key):
                pdf.paragraph(label, size=10.5, bold=True, after=2)
                pdf.paragraph(memoriu[key], size=9.5)
    else:
        for head, key in (("Descriere", "descriere"), ("Justificare", "justificare")):
            if dosar.get(key):
                pdf.heading(head)
                pdf.paragraph(dosar[key])
    for head, key in (("Componente", "componente"), ("Riscuri", "riscuri"),
                      ("De clarificat cu Primăria", "lista_verificare")):
        if dosar.get(key):
            pdf.heading(head)
            for item in dosar[key]:
                pdf.paragraph(item, bullet="•", after=1)
    if dosar.get("etape"):
        pdf.heading("Etape")
        for e in dosar["etape"]:
            n = e.get("durata_luni")
            pdf.paragraph(f"{e.get('nume')} – {n} {'lună' if n == 1 else 'luni'}", bullet="•", after=1)

    _draw_spec(pdf, spec)

    pdf.heading("Estimare de cost")
    # Same rule as in the UI: the headline is the reference interval, or the plain statement that the total cannot be
    # estimated. The sum of the priced lines is partial: never bold, never called the cost.
    if cost.get("suficient"):
        pdf.paragraph(f"{cost.get('titlu') or 'Cost estimat din proiecte de referință'}: între {lei(cost.get('min_lei'))} și "
                      f"{lei(cost.get('max_lei'))}, mediană {lei(cost.get('mediana_lei'))}.", bold=True)
    else:
        pdf.paragraph(cost.get("titlu") or "Cost total: nu poate fi estimat din datele disponibile", bold=True)
        pdf.paragraph(cost.get("motiv") or "Date insuficiente pentru un interval din proiecte de referință.")
    if cost.get("suma_cotata_lei") is not None and cost.get("articole_cotate"):
        pdf.paragraph(f"Informație parțială – {cost.get('eticheta_suma')}: {lei(cost.get('suma_cotata_lei'))}.")
        if cost.get("nota_suma"):
            pdf.paragraph(cost["nota_suma"], color="#a33a1d")
    if cost.get("articole_necotate"):
        pdf.paragraph("Fără preț (de cotat): " + "; ".join(cost["articole_necotate"]), size=8.5, color="#a33a1d")
    pdf.paragraph(cost.get("metoda", ""), size=8.5, color="#555555")
    for note in cost.get("ipoteze") or []:
        pdf.paragraph(note, size=8.5, bullet="•", color="#555555", after=1)
    if refs:
        pdf.heading("Proiecte de referință")
        for r in refs:
            area = f", {fmt(r['suprafata_mp'])} mp" if r.get("suprafata_mp") else ""
            value = f", {lei(r['cost_total_lei'])}" if r.get("cost_total_lei") else ""
            pdf.paragraph(f"{r.get('oras')}, {r.get('an')}{area}{value}", size=9, bullet="•", after=0)
            pdf.paragraph(str(r.get("sursa_url", "")), size=7, indent=12, color="#555555", after=2)

    acte = dosar.get("acte") or []
    if acte:
        pdf.heading("Documente și avize necesare (orientativ)")
        for a in acte:
            pdf.paragraph(f"{a.get('ordine')}. {a.get('nume')} – {a.get('emitent')}", size=9, bold=True, after=0)
            pdf.paragraph(a.get("descriere", "") + (f" Când: {a['conditie']}." if a.get("conditie") else "")
                          + f" Temei: {a.get('temei', '')}.", size=8, indent=12, color="#444444", after=3)
        pdf.paragraph(dosar.get("acte_disclaimer", ""), size=8, color="#555555")
    for cerere in dosar.get("cereri_tip") or []:
        pdf.heading(f"Model: {cerere.get('titlu')}")
        pdf.paragraph(f"Către: {cerere.get('catre')}", size=9, bold=True)
        pdf.paragraph(cerere.get("text", ""), size=9)

    _draw_plan(pdf, scene)
    _draw_materials(pdf, lista)
    pdf.heading("Notă")
    pdf.paragraph(CONTRACT_DISCLAIMER, bold=True)
    return pdf.to_bytes()


def build_documente(proiect: Any, space: Any = None) -> dict[str, tuple[bytes, str]]:
    spec = spec_for(proiect)
    scene = scene_for(proiect, space, spec)
    lista = lista_materiale(scene, spec)
    title = _title(proiect, scene)
    demo = bool(_get(proiect, "is_demo", default=False))
    files = {
        "plan.svg": build_plan_svg(scene, title).encode("utf-8"),
        "plan.dxf": build_plan_dxf(scene, title).encode("ascii"),
        "plansa.pdf": build_plansa_pdf(scene, spec, title, space, demo),
        "dosar.pdf": build_dosar_pdf(proiect, space, scene, lista),
        "materiale.xlsx": build_materiale_xlsx(lista, title, _plain(_get(proiect, "cost", default={}))),
        "materiale.csv": materiale_csv(lista),
    }
    return {name: (content, MEDIA[name]) for name, content in files.items()}


__all__ = ["MEDIA", "build_documente", "build_dosar_pdf", "materiale_csv", "materiale_json", "plan_json",
           "scene_for", "spec_for"]
