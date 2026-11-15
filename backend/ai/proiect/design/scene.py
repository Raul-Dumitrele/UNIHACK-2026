"""build_scene(tip_amenajare, suprafata_mp, latime_m=None, spec=None) -> Scene: a schematic site plan.

Deterministic, no AI. Coordinates in metres, origin at the bottom-left corner of the plot, y up (as in CAD).
Elements come from the technical specification (backend.ai.proiect.spec): mandatory ones first, then the rest,
placed row by row (first fit). Each element keeps its free zone clear of every other element. Whatever does
not fit is listed in Scene.omise with the reason; nothing is ever drawn overlapping.
"""
import math

from pydantic import BaseModel

from backend.ai.proiect.design.catalog import ALEE_LATIME_M, MARGINE_M, PISTA_LATIME_M, Spec, generic, specs_for
from backend.ai.proiect.spec import Specificatie, get_specificatie, resolve_type
from backend.ai.references.core import label_for

PLAN_DISCLAIMER = ("Plan schematic orientativ, generat automat. Nu este un proiect tehnic: dimensiunile "
                   "sunt ipoteze de lucru, iar amplasarea reală o stabilește un proiectant autorizat, "
                   "după măsurători pe teren.")
ASPECT = 1.5  # plot length / width when only the area is known
EPS = 1e-6


class Element(BaseModel):
    id: str
    nume: str
    tip: str
    x: float
    y: float
    latime_m: float
    lungime_m: float
    zona_libera_m: float = 0.0
    obligatoriu: bool = False
    categorie: str = "echipament"
    inaltime_m: float = 0.0  # schematic height, for the 3D view and the elevation sheet
    componenta: str | None = None  # specification component drawn by this element

    @property
    def suprafata_mp(self) -> float:
        return self.latime_m * self.lungime_m


class Omis(BaseModel):
    nume: str
    bucati: int = 1
    obligatoriu: bool = False
    motiv: str


class Scene(BaseModel):
    tip_amenajare: str
    eticheta: str
    suprafata_mp: float
    latime_m: float
    lungime_m: float
    elemente: list[Element]
    omise: list[Omis]
    complet: bool  # every mandatory element is on the plan
    ipoteze: list[str]
    sursa_specificatie: str = "model_verificat"
    disclaimer: str = PLAN_DISCLAIMER

    @property
    def suprafata_ocupata_mp(self) -> float:
        return round(sum(e.suprafata_mp for e in self.elemente), 2)

    def by_componenta(self, nume: str) -> list[Element]:
        return [e for e in self.elemente if e.componenta == nume]


def numere(scene: "Scene", mic) -> list[tuple[str, float, float, bool]]:
    """Labels for the drawings: (text, x, y, outside), in metres. A big element carries its number in the middle.
    Elements too small for a number (mic(e) is True) are labelled once per run of the same component, above the
    run ("11–13"), so numbers never pile up on top of each other. The legend still lists every element."""
    out: list[tuple[str, float, float, bool]] = []
    run: list[tuple[int, Element]] = []

    def flush() -> None:
        if not run:
            return
        first, last = run[0][0], run[-1][0]
        xs0 = min(e.x for _i, e in run)
        xs1 = max(e.x + e.latime_m for _i, e in run)
        top = max(e.y + e.lungime_m for _i, e in run)
        out.append((str(first) if first == last else f"{first}–{last}", (xs0 + xs1) / 2, top, True))
        run.clear()

    for i, e in enumerate(scene.elemente, 1):
        if not mic(e):
            flush()
            out.append((str(i), e.x + e.latime_m / 2, e.y + e.lungime_m / 2, False))
            continue
        if run and (run[-1][1].componenta != e.componenta or abs(run[-1][1].y - e.y) > 0.01):
            flush()
        run.append((i, e))
    flush()
    return out


def fmt(value: float) -> str:
    """12.5 -> '12,5'; 12.0 -> '12'."""
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


class _Packer:
    """First-fit shelves inside the rectangle [x0, x1] × [y0, y1]; footprints include the free zone."""

    def __init__(self, x0: float, y0: float, x1: float, y1: float):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.shelves: list[list[float]] = []  # [y, height, x cursor]
        self.last = 0

    def place(self, w: float, h: float, pad: float, new_shelf: bool = False,
              prefer: int | None = None) -> tuple[float, float] | None:
        """new_shelf: open a new row instead of filling an existing one. prefer: try this row first.
        self.last is the index of the row the element went to."""
        fw, fh = w + 2 * pad, h + 2 * pad
        order = [] if new_shelf else list(range(len(self.shelves)))
        if prefer is not None and prefer in order:
            order.remove(prefer)
            order.insert(0, prefer)
        for index in order:
            y, height, cursor = self.shelves[index]
            if cursor + fw <= self.x1 + EPS and fh <= height + EPS:
                self.shelves[index][2] = cursor + fw
                self.last = index
                return cursor + pad, y + pad
        top = self.shelves[-1][0] + self.shelves[-1][1] if self.shelves else self.y0
        if self.x0 + fw <= self.x1 + EPS and top + fh <= self.y1 + EPS:
            self.shelves.append([top, fh, self.x0 + fw])
            self.last = len(self.shelves) - 1
            return self.x0 + pad, top + pad
        return None


def _sizes(spec: Spec) -> list[tuple[float, float]]:
    sizes = [(spec.latime_m, spec.lungime_m), (spec.lungime_m, spec.latime_m)]
    if spec.min_latime_m and spec.min_lungime_m:
        sizes += [(spec.min_latime_m, spec.min_lungime_m), (spec.min_lungime_m, spec.min_latime_m)]
    return list(dict.fromkeys(sizes))


def _plot_size(suprafata_mp: float, latime_m: float | None) -> tuple[float, float]:
    if latime_m and latime_m > 0:
        w = round(latime_m, 2)
    else:
        w = round(math.sqrt(suprafata_mp / ASPECT), 1) or 0.1
    return w, round(suprafata_mp / w, 2)


def _loop_track(x0: float, y0: float, x1: float, y1: float, add) -> tuple[float, float, float, float] | None:
    """Bicycle loop along the usable area; returns the free area inside it, or None if it does not fit."""
    p = PISTA_LATIME_M
    if x1 - x0 < 2 * p + 2 or y1 - y0 < 2 * p + 2:
        return None
    loop = "pistă de biciclete în buclă"
    add("pistă de biciclete (latura de jos)", "pista", x0, y0, x1 - x0, p, True, 0.0, "finisaj", 0.05, loop)
    add("pistă de biciclete (latura de sus)", "pista", x0, y1 - p, x1 - x0, p, True, 0.0, "finisaj", 0.05, loop)
    add("pistă de biciclete (latura stângă)", "pista", x0, y0 + p, p, y1 - y0 - 2 * p, True, 0.0, "finisaj", 0.05, loop)
    add("pistă de biciclete (latura dreaptă)", "pista", x1 - p, y0 + p, p, y1 - y0 - 2 * p, True, 0.0, "finisaj", 0.05, loop)
    return x0 + p, y0 + p, x1 - p, y1 - p


def build_scene(tip_amenajare: str, suprafata_mp: float, latime_m: float | None = None,
                spec: Specificatie | None = None) -> Scene:
    """Any proposal: the specification decides what is drawn (hand-written model, LLM, or generic).
    latime_m: plot width when known (e.g. a 12 m lot); otherwise a 2:3 rectangle of the given area."""
    if not suprafata_mp or suprafata_mp <= 0:
        raise ValueError("suprafata_mp trebuie să fie pozitivă")
    spec = spec or get_specificatie(tip_amenajare, suprafata_mp)
    tip = spec.tip_amenajare or resolve_type(tip_amenajare) or "amenajare"
    eticheta = spec.eticheta or label_for(tip_amenajare)
    w, h = _plot_size(float(suprafata_mp), latime_m)
    margin = min(MARGINE_M, round(min(w, h) / 8, 2))
    x0, y0, x1, y1 = margin, margin, w - margin, h - margin
    elements: list[Element] = []
    omitted: list[Omis] = []

    def add(nume, kind, x, y, ew, eh, mandatory=False, pad=0.0, categorie="echipament", height=0.0, comp=None):
        elements.append(Element(id=f"e{len(elements) + 1}", nume=nume, tip=kind, x=round(x, 2), y=round(y, 2),
                                latime_m=round(ew, 2), lungime_m=round(eh, 2), zona_libera_m=pad,
                                obligatoriu=mandatory, categorie=categorie, inaltime_m=height, componenta=comp))

    ipoteze = [
        (f"Lățimea terenului: {fmt(w)} m (dată); lungimea rezultă din suprafață: {fmt(h)} m."
         if latime_m else
         f"Forma reală a terenului nu e cunoscută: planul folosește un dreptunghi de {fmt(w)} × {fmt(h)} m "
         f"cu aceeași suprafață."),
        "Dimensiunile elementelor și zonele libere din jurul lor sunt ipoteze schematice ale aplicației, "
        "nu valori din standarde sau din fișe de produs.",
        f"Pe contur rămâne o margine liberă de {fmt(margin)} m (împrejmuire, vegetație).",
    ]
    specs = specs_for(spec)
    if not specs:
        specs = generic(eticheta, max(x1 - x0, 0.1), max(y1 - y0 - ALEE_LATIME_M, 0.1))
    if spec.sursa_specificatie == "generic":
        ipoteze.append(f"Pentru „{eticheta}” aplicația nu are un model de amenajare verificat: planul arată doar zona "
                       "propusă și mobilierul de bază.")
    elif spec.sursa_specificatie == "llm":
        ipoteze.append("Componentele au fost propuse automat (model de limbaj) și validate doar ca formă.")
    wants_alee = any(c.derivat_din == "plan_alee" for c in spec.componente)

    if x1 - x0 <= 0 or y1 - y0 <= 0:
        area = None
    elif tip == "pista_biciclete":
        area = _loop_track(x0, y0, x1, y1, add)
        if area is None:
            omitted.append(Omis(nume="pistă de biciclete în buclă", obligatoriu=True,
                                motiv="terenul e prea îngust pentru o buclă de "
                                      f"{fmt(PISTA_LATIME_M)} m lățime"))
            area = (x0, y0, x1, y1)
        ipoteze.append(f"Pista e o buclă de {fmt(PISTA_LATIME_M)} m lățime pe conturul terenului.")
    elif wants_alee and y1 - y0 > ALEE_LATIME_M + 1:
        add("alee de acces", "alee", x0, y0, x1 - x0, ALEE_LATIME_M, False, 0.0, "finisaj", 0.0, "alee de acces pavată")
        ipoteze.append(f"Intrarea e pe latura de jos, cu o alee de {fmt(ALEE_LATIME_M)} m.")
        area = (x0, y0 + ALEE_LATIME_M, x1, y1)
    else:
        area = (x0, y0, x1, y1)

    packer = _Packer(*area) if area else None
    rows: dict[str, int] = {}  # component name -> row it was placed in (for Spec.langa)
    for s in specs:
        placed = 0
        for i in range(s.bucati):
            spot = None
            for ew, eh in _sizes(s):
                spot = packer.place(ew, eh, s.zona_libera_m, s.rand_nou and i == 0,
                                    rows.get(s.langa) if s.langa else None) if packer else None
                if spot:
                    rows.setdefault(s.nume, packer.last)
                    break
            if not spot:
                break
            nume = f"{s.nume} {i + 1}" if s.bucati > 1 else s.nume
            add(nume, s.tip, spot[0], spot[1], ew, eh, s.obligatoriu, s.zona_libera_m, s.categorie, s.inaltime_m,
                s.componenta)
            placed += 1
        if placed < s.bucati:
            missing = s.bucati - placed
            smallest = _sizes(s)[-1]
            need = f"{fmt(smallest[0] + 2 * s.zona_libera_m)} × {fmt(smallest[1] + 2 * s.zona_libera_m)} m"
            omitted.append(Omis(nume=s.nume, bucati=missing, obligatoriu=s.obligatoriu,
                                motiv=f"nu mai încape pe teren (are nevoie de cel puțin {need}, "
                                      "cu zona liberă din jur)"))

    complet = not any(o.obligatoriu for o in omitted)
    return Scene(tip_amenajare=tip, eticheta=eticheta, suprafata_mp=float(suprafata_mp), latime_m=w,
                 lungime_m=h, elemente=elements, omise=omitted, complet=complet, ipoteze=ipoteze,
                 sursa_specificatie=spec.sursa_specificatie)
