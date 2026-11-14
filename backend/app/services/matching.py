"""Idea -> space matching (docs/CONTRACT.md, regula 5). Haversine, no PostGIS."""
from math import asin, cos, radians, sin, sqrt

from backend.app.models import Space
from backend.app.services import slots as sl

W_CAPACITATE, W_SUPRAPUNERE, W_DOTARI, W_DISTANTA = 0.30, 0.30, 0.20, 0.20
DISTANCE_ZERO_KM = 5.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = radians(lat1), radians(lat2)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lng2 - lng1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def common_slots(program: list[dict], space_slots: list[dict]) -> list[dict]:
    out = []
    for p in program:
        for s in space_slots:
            o = sl.overlap(p, s)
            if o:
                out.append(o)
    return out


def _distance_text(km: float) -> str:
    if km < 1:
        return f"{max(round(km * 100) * 10, 10)} m"
    return f"{km:.1f}".replace(".", ",") + " km"


def score_space(structurat: dict, space: Space, points: list[tuple[float, float]], n_interested: int) -> dict:
    """Returns {scor, motiv, suprapunere}. `points` = interested users (or the author when none)."""
    persoane = max(int(structurat.get("persoane") or 1), 1)
    capacitate = min(1.0, space.capacitate / persoane)

    program = structurat.get("program") or []
    common = common_slots(program, space.sloturi)
    requested = sum(sl.duration(p) for p in program)
    # No requested program: any availability counts as a full match.
    suprapunere = 1.0 if not requested else min(1.0, sum(sl.duration(c) for c in common) / requested)

    cerute = structurat.get("dotari") or []
    dotari = 1.0 if not cerute else sum(1 for d in cerute if d in space.dotari) / len(cerute)

    km = sum(haversine_km(space.lat, space.lng, la, lo) for la, lo in points) / len(points) if points else 0.0
    distanta = max(0.0, 1 - km / DISTANCE_ZERO_KM)

    scor = round(100 * (W_CAPACITATE * capacitate + W_SUPRAPUNERE * suprapunere + W_DOTARI * dotari + W_DISTANTA * distanta))

    shown = common or ([] if program else space.sloturi[:2])
    liber = ", ".join(sl.fmt_slot(s) for s in shown) if shown else "fără suprapunere cu programul cerut"
    de = f"{n_interested} interesați" if n_interested else "autor"
    motiv = f"{space.capacitate} locuri, liber {liber}, la {_distance_text(km)} de {de}"
    return {"scor": max(0, min(100, scor)), "motiv": motiv, "suprapunere": common}
