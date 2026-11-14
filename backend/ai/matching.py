"""Idea dossier -> ranked free spaces, each with a 0-100 score and a reason in Romanian.

Deterministic and offline (no Gemini), so it is fast and explainable. Proposal for the
"formula de scor" left TBD in docs/CONTRACT.md; weights documented in docs/DATA.md.
P1 calls match_spaces() from GET /ideas/{id}/matches with the spaces that still have free slots.
"""
import re
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict

from backend.ai.fallback import NEEDS, normalize
from backend.ai.geo import Point, distance_km, nearest_neighborhood, neighborhood_point
from backend.ai.schemas import Category, DossierBase, Setting

WEIGHTS = {"capacity": 30, "needs": 35, "setting": 15, "kind": 10, "distance": 10}
MIN_CAPACITY_RATIO = 0.8  # below 80% of expected participants a space is not suggested
OVERSIZED_RATIO = 4  # more than 4x the participants: suggested, but scored lower
FULL_DISTANCE_KM, ZERO_DISTANCE_KM = 1.0, 8.0

KIND_LABELS = {
    "library": "bibliotecă",
    "community_centre": "centru comunitar",
    "social_centre": "centru social",
    "arts_centre": "centru cultural",
    "cultural_centre": "centru cultural",
    "coworking_space": "spațiu de coworking",
    "sports_centre": "bază sportivă",
    "sports_hall": "sală de sport",
}
KIND_FIT: dict[Category, set[str]] = {
    Category.atelier: {"community_centre", "social_centre", "arts_centre", "coworking_space"},
    Category.sport: {"sports_centre", "sports_hall"},
    Category.cultura: {"arts_centre", "cultural_centre", "library", "community_centre"},
    Category.educatie: {"library", "coworking_space", "community_centre", "cultural_centre"},
    Category.comunitate: {"community_centre", "social_centre", "cultural_centre"},
    Category.mediu: {"community_centre", "social_centre", "sports_centre"},
    Category.altele: set(KIND_LABELS),
}


class SpaceCandidate(BaseModel):
    """What matching needs from a space. Accepts dicts or ORM objects (from_attributes)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    kind: str
    capacity: int
    amenities: list[str] = []
    setting: Setting = Setting.interior
    lat: float | None = None
    lon: float | None = None


class Match(BaseModel):
    space_id: str
    space_name: str
    score: int
    reason: str
    distance_km: float | None = None
    neighborhood: str | None = None
    missing_needs: list[str] = []


def canonical_needs(needs: Iterable[str]) -> tuple[list[str], list[str]]:
    """Free-text needs -> (amenity labels we can check, needs no space lists, e.g. 'ceai')."""
    known: list[str] = []
    unknown: list[str] = []
    for need in needs:
        norm = normalize(need)
        labels = [label for pattern, label in NEEDS.items() if re.search(r"\b" + pattern, norm)]
        if labels:
            known += [label for label in labels if label not in known]
        elif need not in unknown:
            unknown.append(need)
    return known, unknown


def _km(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def _origin_point(origin: Point | str | None) -> Point | None:
    return neighborhood_point(origin) if isinstance(origin, str) else origin


def score_space(dossier: DossierBase, space: SpaceCandidate, origin: Point | None = None) -> Match | None:
    """Score one space, or None when it cannot host the idea (too small)."""
    people, cap = dossier.expected_participants, space.capacity
    parts: list[str] = []
    score = 0.0

    if cap < MIN_CAPACITY_RATIO * people:
        return None
    if cap < people:
        score += WEIGHTS["capacity"] / 2
        parts.append(f"{cap} locuri, puțin sub cei {people} participanți estimați")
    elif cap > OVERSIZED_RATIO * people:
        score += WEIGHTS["capacity"] * 2 / 3
        parts.append(f"{cap} locuri, mai mare decât e nevoie pentru {people} persoane")
    else:
        score += WEIGHTS["capacity"]
        parts.append(f"încape {people} persoane ({cap} locuri)")

    known, unknown = canonical_needs(dossier.needs)
    have = [n for n in known if n in space.amenities]
    missing = [n for n in known if n not in space.amenities]
    score += WEIGHTS["needs"] * (len(have) / len(known) if known else 1)
    if have:
        parts.append("are " + ", ".join(have))
    if missing:
        parts.append("lipsește: " + ", ".join(missing))
    if unknown:
        parts.append("de verificat cu proprietarul: " + ", ".join(unknown))

    if dossier.setting in (Setting.oricare, space.setting):
        score += WEIGHTS["setting"]
    else:
        parts.append(f"spațiu {space.setting.value}, ideea cere {dossier.setting.value}")

    label = KIND_LABELS.get(space.kind, space.kind)
    if space.kind in KIND_FIT[dossier.category]:
        score += WEIGHTS["kind"]
        parts.append(f"tip de spațiu potrivit: {label}")

    dist = hood = None
    if space.lat is not None and space.lon is not None:
        hood = nearest_neighborhood((space.lat, space.lon))
        if origin is not None:
            dist = round(distance_km(origin, (space.lat, space.lon)), 1)
    if dist is None:
        score += WEIGHTS["distance"] / 2  # unknown distance: neutral
    else:
        span = ZERO_DISTANCE_KM - FULL_DISTANCE_KM
        score += WEIGHTS["distance"] * min(1.0, max(0.0, (ZERO_DISTANCE_KM - dist) / span))
        parts.append(f"la {_km(dist)} km" + (f", în {hood}" if hood else ""))

    reason = "; ".join(parts)
    return Match(
        space_id=space.id,
        space_name=space.name,
        score=round(score),
        reason=reason[:1].upper() + reason[1:],
        distance_km=dist,
        neighborhood=hood,
        missing_needs=missing,
    )


def match_spaces(
    dossier: DossierBase | dict[str, Any],
    spaces: Iterable[Any],
    origin: Point | str | None = None,
    limit: int = 10,
) -> list[Match]:
    """Rank spaces for an idea. `origin` is (lat, lon) or a district name (e.g. the author's)."""
    if not isinstance(dossier, DossierBase):
        dossier = DossierBase.model_validate(dossier)
    point = _origin_point(origin)
    matches = [m for s in spaces if (m := score_space(dossier, SpaceCandidate.model_validate(s), point))]
    far = float("inf")
    matches.sort(key=lambda m: (-m.score, m.distance_km if m.distance_km is not None else far, m.space_id))
    return matches[:limit]
