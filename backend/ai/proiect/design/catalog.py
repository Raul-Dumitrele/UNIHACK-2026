"""Drawing specs derived from the technical specification (backend.ai.proiect.spec): what gets a footprint on
the plan, with the preferred and the fallback size, the free zone around it, how many, whether mandatory.

Every size is a SCHEMATIC DESIGN ASSUMPTION of this app (see spec/modele.py), not a standard. CATALOG keeps the
seven original kinds for callers and tests that iterate it; new kinds come through specs_for(spec).
"""
from dataclasses import dataclass

from backend.ai.proiect.spec.model import Componenta, Specificatie
from backend.ai.proiect.spec.modele import MODELE


@dataclass(frozen=True)
class Spec:
    nume: str
    tip: str  # element kind, used for colours and hatches
    latime_m: float
    lungime_m: float
    min_latime_m: float | None = None  # smaller fallback; None = no fallback
    min_lungime_m: float | None = None
    zona_libera_m: float = 0.5
    bucati: int = 1
    obligatoriu: bool = False
    categorie: str = "echipament"
    inaltime_m: float = 0.0
    componenta: str | None = None  # name of the specification component this spec draws


ALEE_LATIME_M = 1.5  # access path along the entrance side
MARGINE_M = 1.0  # strip kept free along the plot boundary (fence, planting)
PISTA_LATIME_M = 2.5  # bicycle loop track width
ORIGINAL_KINDS = ("skatepark", "loc_de_joaca", "parc_caini", "pista_biciclete", "gradina_comunitara", "teren_sport",
                  "foisor")


def spec_from(c: Componenta) -> Spec | None:
    if not c.are_amprenta:
        return None
    count = int(round(c.cantitate)) if c.unitate in ("buc", "set") else c.bucati_plan
    return Spec(c.nume, c.tip_desen, float(c.latime_m), float(c.lungime_m), c.min_latime_m, c.min_lungime_m,
                c.zona_libera_m, max(count, 1), c.obligatoriu, c.categorie, float(c.inaltime_m or 0.0), c.nume)


def specs_for(spec: Specificatie) -> list[Spec]:
    """Mandatory components first (they must get room), then the rest in specification order."""
    drawn = [s for s in (spec_from(c) for c in spec.componente) if s is not None]
    return [s for s in drawn if s.obligatoriu] + [s for s in drawn if not s.obligatoriu]


CATALOG: dict[str, list[Spec]] = {kind: specs_for(MODELE[kind]) for kind in ORIGINAL_KINDS}


def generic(eticheta: str, latime_m: float, lungime_m: float) -> list[Spec]:
    """One main zone sized to the usable area plus furniture, when nothing specific is known."""
    w, h = round(latime_m * 0.8, 1), round(lungime_m * 0.6, 1)
    return [Spec(f"zona propusă: {eticheta}", "zona", w, h, round(w * 0.6, 1), round(h * 0.6, 1),
                 zona_libera_m=1.0, obligatoriu=True, inaltime_m=1.0, componenta=f"zona propusă: {eticheta}"),
            Spec("bancă", "banca", 1.8, 0.6, zona_libera_m=0.5, bucati=3, categorie="mobilier", inaltime_m=0.9,
                 componenta="bancă"),
            Spec("coș de gunoi", "cos", 0.6, 0.6, zona_libera_m=0.3, bucati=2, categorie="mobilier", inaltime_m=1.0,
                 componenta="coș de gunoi")]
