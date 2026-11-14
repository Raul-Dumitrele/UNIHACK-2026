"""build_scene(tip_amenajare, suprafata_mp) -> Scene: a schematic site plan on a rectangular plot.

Deterministic, no AI. Coordinates in metres, origin at the bottom-left corner of the plot, y up (as in CAD).
Elements are placed row by row (first fit), in catalog order, so the main element comes first. Each
element keeps its free zone (zona_libera_m) clear of every other element. Whatever does not fit is left
out and listed in Scene.omise with the reason; nothing is ever drawn overlapping.
"""
import math

from pydantic import BaseModel

from backend.ai.proiect.design.catalog import (
    ALEE_LATIME_M, CATALOG, MARGINE_M, PISTA_LATIME_M, Spec, generic,
)
from backend.ai.references.core import canonical_type, label_for

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
    disclaimer: str = PLAN_DISCLAIMER

    @property
    def suprafata_ocupata_mp(self) -> float:
        return round(sum(e.suprafata_mp for e in self.elemente), 2)


def fmt(value: float) -> str:
    """12.5 -> '12,5'; 12.0 -> '12'."""
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


class _Packer:
    """First-fit shelves inside the rectangle [x0, x1] × [y0, y1]; footprints include the free zone."""

    def __init__(self, x0: float, y0: float, x1: float, y1: float):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.shelves: list[list[float]] = []  # [y, height, x cursor]

    def place(self, w: float, h: float, pad: float) -> tuple[float, float] | None:
        fw, fh = w + 2 * pad, h + 2 * pad
        for shelf in self.shelves:
            y, height, cursor = shelf
            if cursor + fw <= self.x1 + EPS and fh <= height + EPS:
                shelf[2] = cursor + fw
                return cursor + pad, y + pad
        top = self.shelves[-1][0] + self.shelves[-1][1] if self.shelves else self.y0
        if self.x0 + fw <= self.x1 + EPS and top + fh <= self.y1 + EPS:
            self.shelves.append([top, fh, self.x0 + fw])
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
    add("pistă de biciclete (latura de jos)", "pista", x0, y0, x1 - x0, p, True)
    add("pistă de biciclete (latura de sus)", "pista", x0, y1 - p, x1 - x0, p, True)
    add("pistă de biciclete (latura stângă)", "pista", x0, y0 + p, p, y1 - y0 - 2 * p, True)
    add("pistă de biciclete (latura dreaptă)", "pista", x1 - p, y0 + p, p, y1 - y0 - 2 * p, True)
    return x0 + p, y0 + p, x1 - p, y1 - p


def build_scene(tip_amenajare: str, suprafata_mp: float, latime_m: float | None = None) -> Scene:
    """Any proposal: known kinds use the catalog, anything else gets one main zone plus furniture.
    latime_m: plot width when known (e.g. a 12 m lot); otherwise a 2:3 rectangle of the given area."""
    if not suprafata_mp or suprafata_mp <= 0:
        raise ValueError("suprafata_mp trebuie să fie pozitivă")
    tip = canonical_type(tip_amenajare) or "amenajare"
    eticheta = label_for(tip_amenajare)
    w, h = _plot_size(float(suprafata_mp), latime_m)
    x0, y0, x1, y1 = MARGINE_M, MARGINE_M, w - MARGINE_M, h - MARGINE_M
    elements: list[Element] = []
    omitted: list[Omis] = []

    def add(nume, kind, x, y, ew, eh, mandatory=False, pad=0.0):
        elements.append(Element(id=f"e{len(elements) + 1}", nume=nume, tip=kind, x=round(x, 2), y=round(y, 2),
                                latime_m=round(ew, 2), lungime_m=round(eh, 2), zona_libera_m=pad,
                                obligatoriu=mandatory))

    ipoteze = [
        (f"Lățimea terenului: {fmt(w)} m (dată); lungimea rezultă din suprafață: {fmt(h)} m."
         if latime_m else
         f"Forma reală a terenului nu e cunoscută: planul folosește un dreptunghi de {fmt(w)} × {fmt(h)} m "
         f"cu aceeași suprafață."),
        "Dimensiunile elementelor și zonele libere din jurul lor sunt ipoteze schematice ale aplicației, "
        "nu valori din standarde sau din fișe de produs.",
        f"Pe contur rămâne o margine liberă de {fmt(MARGINE_M)} m (împrejmuire, vegetație).",
    ]
    specs = CATALOG.get(tip)
    if specs is None:
        specs = generic(eticheta, max(x1 - x0, 0.1), max(y1 - y0 - ALEE_LATIME_M, 0.1))
        ipoteze.append(f"Pentru „{eticheta}” aplicația nu are un model de amenajare: planul arată doar zona "
                       "propusă și mobilierul de bază.")

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
    elif y1 - y0 > ALEE_LATIME_M + 1:
        add("alee de acces", "alee", x0, y0, x1 - x0, ALEE_LATIME_M)
        ipoteze.append(f"Intrarea e pe latura de jos, cu o alee de {fmt(ALEE_LATIME_M)} m.")
        area = (x0, y0 + ALEE_LATIME_M, x1, y1)
    else:
        area = (x0, y0, x1, y1)

    packer = _Packer(*area) if area else None
    for spec in specs:
        placed = 0
        for i in range(spec.bucati):
            spot = None
            for ew, eh in _sizes(spec):
                spot = packer.place(ew, eh, spec.zona_libera_m) if packer else None
                if spot:
                    break
            if not spot:
                break
            nume = f"{spec.nume} {i + 1}" if spec.bucati > 1 else spec.nume
            add(nume, spec.tip, spot[0], spot[1], ew, eh, spec.obligatoriu, spec.zona_libera_m)
            placed += 1
        if placed < spec.bucati:
            missing = spec.bucati - placed
            smallest = _sizes(spec)[-1]
            need = f"{fmt(smallest[0] + 2 * spec.zona_libera_m)} × {fmt(smallest[1] + 2 * spec.zona_libera_m)} m"
            omitted.append(Omis(nume=spec.nume, bucati=missing, obligatoriu=spec.obligatoriu,
                                motiv=f"nu mai încape pe teren (are nevoie de cel puțin {need}, "
                                      "cu zona liberă din jur)"))

    complet = not any(o.obligatoriu for o in omitted)
    return Scene(tip_amenajare=tip, eticheta=eticheta, suprafata_mp=float(suprafata_mp), latime_m=w,
                 lungime_m=h, elemente=elements, omise=omitted, complet=complet, ipoteze=ipoteze)
