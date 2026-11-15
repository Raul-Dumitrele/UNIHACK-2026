"""lista_materiale(scene, spec=None) -> ListaMateriale: the bill of quantities of a proposal.

Quantities come from the technical specification and from the schematic plan (what was actually placed, the
remaining green area, the perimeter). Unit prices come from backend.ai.proiect.preturi_surse (SEAP, programme
ceilings, verified catalogue), each line naming its source. Deterministic, no AI.

A line gets a value only when its article has a price; everything else is "de cotat", with the reason. The
subtotal covers only the priced lines and is always labelled as incomplete: it is never the cost of the project.
"""
from pydantic import BaseModel

from backend.ai.proiect.design import Scene
from backend.ai.proiect.design.scene import fmt
from backend.ai.proiect.preturi import SURSA, TVA, PretUnitar
from backend.ai.proiect.preturi_surse import motiv_necotat, nume_articol, rezolva_pret
from backend.ai.proiect.spec import Specificatie, get_specificatie
from backend.ai.proiect.spec.model import CATEGORII_RO, Componenta

MATERIALE_DISCLAIMER = (
    "Listă orientativă. Cantitățile rezultă din specificația tehnică și din planul schematic, iar prețurile unitare "
    "sunt mediane ale unor achiziții directe publice din SEAP, plafoane de program sau prețuri de catalog verificate, "
    "nu oferte. Subtotalul nu este costul proiectului: articolele „de cotat” lipsesc din el, iar manopera, "
    "transportul și proiectarea pot să nu fie incluse.")
SURSE_RO = {"seap": "SEAP (achiziții directe, date deschise)", "plafon": "plafon de program oficial",
            "catalog": "preț de catalog verificat"}


class LinieMaterial(BaseModel):
    articol: str | None  # price article key, None when the app has no price source for it
    nume: str
    unitate: str
    cantitate: float
    ipoteza: str
    categorie: str = "echipament"
    capitol: str = "Echipamente"
    pret_unitar: PretUnitar | None = None
    valoare_lei: int | None = None
    stare: str  # cotat | de_cotat
    tip_sursa: str | None = None  # seap | plafon | catalog
    motiv: str = ""


class ListaMateriale(BaseModel):
    linii: list[LinieMaterial]
    capitole: list[str]
    subtotal_cotat_lei: int
    linii_de_cotat: int
    articole_necotate: list[str] = []
    pe_surse: dict[str, int] = {}
    eticheta_subtotal: str
    sursa_preturi: str = SURSA
    surse: dict[str, str] = SURSE_RO
    tva: str = TVA
    ipoteze: list[str]
    disclaimer: str = MATERIALE_DISCLAIMER


def _line(c: Componenta, cantitate: float, ipoteza: str, nume: str | None = None) -> LinieMaterial:
    cantitate = round(cantitate) if c.unitate in ("buc", "set") else round(cantitate, 1)
    info = nume_articol(c.articol)
    label = nume or c.nume
    price = rezolva_pret(c.articol)
    base = dict(articol=c.articol, nume=label, unitate=c.unitate, cantitate=cantitate, ipoteza=ipoteza,
                categorie=c.categorie, capitol=CATEGORII_RO.get(c.categorie, c.categorie))
    if price:
        return LinieMaterial(**base, pret_unitar=price, valoare_lei=round(cantitate * price.mediana_lei),
                             stare="cotat", tip_sursa=price.tip_sursa)
    return LinieMaterial(**base, stare="de_cotat", motiv=motiv_necotat(c.articol if info or c.articol else None))


def lista_materiale(scene: Scene, spec: Specificatie | None = None) -> ListaMateriale:
    spec = spec or get_specificatie(scene.tip_amenajare, scene.suprafata_mp)
    lines: list[LinieMaterial] = []
    notes: list[str] = list(scene.ipoteze)

    alee = sum(e.suprafata_mp for e in scene.elemente if e.tip == "alee")
    perimeter = 2 * (scene.latime_m + scene.lungime_m)
    zone_eq = sum((e.latime_m + 2 * e.zona_libera_m) * (e.lungime_m + 2 * e.zona_libera_m)
                  for e in scene.elemente if e.categorie == "echipament")
    finish_areas = 0.0  # mp of finishes derived from zones, excluded from the green remainder

    for c in spec.componente:
        placed = scene.by_componenta(c.nume)
        if c.derivat_din == "fix":
            if c.are_amprenta:
                n = len(placed)
                if n == 0:
                    notes.append(f"„{c.nume}” nu încape pe plan și nu apare în listă.")
                    continue
                if c.unitate in ("buc", "set"):
                    lines.append(_line(c, n, f"{n} pe planul schematic"))
                else:
                    lines.append(_line(c, sum(e.suprafata_mp for e in placed), "suprafața din planul schematic"))
            else:
                lines.append(_line(c, c.cantitate, "cantitate din specificația tehnică (ipoteză)"))
        elif c.derivat_din == "plan_element":
            area = sum(e.suprafata_mp for e in placed)
            if area <= 0:
                notes.append(f"„{c.nume}” nu încape pe plan și nu apare în listă.")
                continue
            lines.append(_line(c, area, "suprafața din planul schematic"))
        elif c.derivat_din == "plan_alee":
            if alee > 0:
                lines.append(_line(c, alee, "suprafața aleii de acces din plan"))
        elif c.derivat_din == "plan_zona_libera":
            if zone_eq > 0:
                finish_areas += zone_eq
                lines.append(_line(c, zone_eq, "echipamentele împreună cu zona liberă din jurul lor (ipoteză de plan)"))
        elif c.derivat_din == "plan_perimetru":
            lines.append(_line(c, perimeter, "pe tot conturul terenului (ipoteză)"))
            notes.append(f"Împrejmuirea are {fmt(perimeter)} m (perimetrul dreptunghiului din plan).")
        elif c.derivat_din == "plan_rest":
            occupied = scene.suprafata_ocupata_mp
            eq_only = sum(e.suprafata_mp for e in scene.elemente if e.categorie == "echipament")
            green = scene.suprafata_mp - occupied - max(0.0, finish_areas - eq_only)
            if green > 0:
                lines.append(_line(c, green, "suprafața rămasă liberă pe plan (ipoteză)"))

    order = [CATEGORII_RO[k] for k in CATEGORII_RO]
    lines.sort(key=lambda l: order.index(l.capitol) if l.capitol in order else len(order))
    priced = [l for l in lines if l.valoare_lei is not None]
    todo = [l.nume for l in lines if l.valoare_lei is None]
    pe_surse: dict[str, int] = {}
    for l in priced:
        pe_surse[l.tip_sursa or "seap"] = pe_surse.get(l.tip_sursa or "seap", 0) + 1
    notes.append("Prețul unitar este mediana prețurilor din sursa indicată pe fiecare rând; intervalul min–max arată "
                 "cât de mult diferă produsele între ele.")
    return ListaMateriale(
        linii=lines, capitole=[c for c in order if any(l.capitol == c for l in lines)],
        subtotal_cotat_lei=sum(l.valoare_lei for l in priced), linii_de_cotat=len(todo), articole_necotate=todo,
        pe_surse=pe_surse,
        eticheta_subtotal=(f"Subtotal articole cotate (incomplet: {len(todo)} articole de cotat)" if todo else
                           "Subtotal articole cotate"),
        ipoteze=notes,
    )
