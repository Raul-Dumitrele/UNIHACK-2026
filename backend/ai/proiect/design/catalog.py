"""What goes on a plot, per kind of proposal. Every size here is a SCHEMATIC DESIGN ASSUMPTION of this app
(typical order of magnitude, chosen so the plan is readable), not taken from a standard or a product sheet:
a designer sets the real dimensions and safety zones. The plan says so (PLAN_DISCLAIMER, Scene.ipoteze).

Each spec: preferred size, a smaller size tried when the preferred one does not fit, free zone kept around
the element (no other element inside it), how many, and whether the proposal makes sense without it.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Spec:
    nume: str
    tip: str  # element kind, used for colours and material lists
    latime_m: float
    lungime_m: float
    min_latime_m: float | None = None  # smaller fallback; None = no fallback
    min_lungime_m: float | None = None
    zona_libera_m: float = 0.5
    bucati: int = 1
    obligatoriu: bool = False


ALEE_LATIME_M = 1.5  # access path along the entrance side
MARGINE_M = 1.0  # strip kept free along the plot boundary (fence, planting)
PISTA_LATIME_M = 2.5  # bicycle loop track width

_MOBILIER = [
    Spec("bancă", "banca", 1.8, 0.6, zona_libera_m=0.5, bucati=3),
    Spec("coș de gunoi", "cos", 0.6, 0.6, zona_libera_m=0.3, bucati=2),
]

CATALOG: dict[str, list[Spec]] = {
    "skatepark": [
        Spec("zonă de skate (rampe și obstacole)", "skate", 20, 15, 10, 8, zona_libera_m=1.0, obligatoriu=True),
        Spec("zonă pentru începători", "skate", 8, 6, 5, 4, zona_libera_m=1.0),
        *_MOBILIER,
    ],
    "loc_de_joaca": [
        Spec("structură de joacă cu tobogan", "joaca", 6, 4, 4, 3, zona_libera_m=1.5, obligatoriu=True),
        Spec("leagăne", "joaca", 4, 2.5, zona_libera_m=1.5),
        Spec("nisipar", "joaca", 3, 3, 2, 2, zona_libera_m=0.5),
        Spec("balansoar", "joaca", 3, 0.6, zona_libera_m=1.5),
        *_MOBILIER,
    ],
    "parc_caini": [
        Spec("zonă de alergare și agility", "caini", 12, 8, 6, 5, zona_libera_m=0.5, obligatoriu=True),
        Spec("zonă separată pentru câini mici", "caini", 8, 6, 4, 4, zona_libera_m=0.5),
        Spec("adăpătoare", "apa", 1, 1, zona_libera_m=0.5),
        Spec("dozator de pungi", "cos", 0.5, 0.5, zona_libera_m=0.3, bucati=2),
        *_MOBILIER,
    ],
    "pista_biciclete": [  # the loop track itself is laid out by scene._loop_track
        Spec("rastel pentru biciclete", "rastel", 3, 1, zona_libera_m=0.5),
        Spec("zonă de învățare pentru copii", "pista", 8, 6, 5, 4, zona_libera_m=0.5),
        *_MOBILIER,
    ],
    "gradina_comunitara": [
        Spec("strat înălțat", "strat", 3, 1.2, zona_libera_m=0.6, bucati=10, obligatoriu=True),
        Spec("magazie de unelte", "magazie", 2.5, 2, zona_libera_m=0.5),
        Spec("zonă de compost", "compost", 2, 1.5, zona_libera_m=0.5),
        Spec("rezervor de apă", "apa", 1, 1, zona_libera_m=0.3),
        *_MOBILIER,
    ],
    "teren_sport": [
        Spec("teren multisport", "sport", 30, 15, 15, 11, zona_libera_m=1.0, obligatoriu=True),
        *_MOBILIER,
    ],
    "foisor": [
        Spec("foișor", "foisor", 5, 5, 4, 4, zona_libera_m=1.0, obligatoriu=True),
        Spec("masă cu bănci", "masa", 2, 1.8, zona_libera_m=0.6, bucati=2),
        *_MOBILIER,
    ],
}


def generic(eticheta: str, latime_m: float, lungime_m: float) -> list[Spec]:
    """Any other proposal (fântână, parc acvatic...): one main zone sized to the usable area, plus furniture.
    Nothing specific is invented about what the zone contains."""
    w, h = round(latime_m * 0.8, 1), round(lungime_m * 0.6, 1)
    return [Spec(f"zona propusă: {eticheta}", "zona", w, h, round(w * 0.6, 1), round(h * 0.6, 1),
                 zona_libera_m=1.0, obligatoriu=True), *_MOBILIER]
