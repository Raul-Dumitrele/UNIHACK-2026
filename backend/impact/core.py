"""Impact dashboard numbers. Pure function over approved bookings; formulas documented in docs/DATA.md.

Signature is a proposal for docs/CONTRACT.md: P1 maps approved Booking rows to ApprovedBooking.
"""
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from backend.ai.geo import city_centre, distance_km, nearest_neighborhood, neighborhood_point
from backend.ai.matching import KIND_LABELS

# Assumption (estimate): when we do not know where a participant lives, using a local space instead
# of travelling to a central venue avoids KM_PER_PARTICIPANT km of car travel (round trip).
KM_PER_PARTICIPANT = 4.0


@dataclass(frozen=True)
class ApprovedBooking:
    idea_id: str
    space_id: str
    starts_at: datetime
    ends_at: datetime
    participants: int  # confirmed community interest for the idea (interest count)
    space_kind: str | None = None
    space_lat: float | None = None
    space_lon: float | None = None
    participant_neighborhoods: tuple[str, ...] = ()  # where known; the rest use KM_PER_PARTICIPANT


class WeekStats(BaseModel):
    saptamana: str  # ISO week, e.g. "2026-W47"
    rezervari: int
    ore: float
    participanti: int


class ImpactReport(BaseModel):
    idei_realizate: int
    spatii_activate: int
    rezervari_aprobate: int
    ore_folosite: float
    participanti: int
    km_economisiti: float
    km_economisiti_estimare: bool = True  # always an estimate; UI must label it so
    ipoteze: dict[str, float | str]
    pe_cartiere: dict[str, int] = {}  # approved bookings per district of the space
    pe_tip_spatiu: dict[str, int] = {}  # approved bookings per space type (Romanian label)
    pe_saptamani: list[WeekStats] = []
    proiecte_trimise: int = 0  # proposals past draft (sent to the city hall, in any later state)
    proiecte_cu_acord: int = 0  # proposals with a (simulated) agreement in principle


PROIECT_DRAFT = "draft"
PROIECT_ACORD = "acord_de_principiu"


def _stare(p: Any) -> str:
    """A project row, dict or plain state string -> its state."""
    if isinstance(p, str):
        return p
    return str(p.get("stare") if isinstance(p, dict) else getattr(p, "stare", ""))


def _hours(b: ApprovedBooking) -> float:
    return max((b.ends_at - b.starts_at).total_seconds(), 0) / 3600


def _km_saved(b: ApprovedBooking) -> float:
    """Round trip km avoided: per known participant, (home->centre) - (home->space), never negative."""
    people = max(b.participants, 0)
    homes = [p for p in map(neighborhood_point, b.participant_neighborhoods[:people]) if p]
    if not homes or b.space_lat is None or b.space_lon is None:
        return people * KM_PER_PARTICIPANT
    space, centre = (b.space_lat, b.space_lon), city_centre()
    known = sum(max(distance_km(h, centre) - distance_km(h, space), 0.0) * 2 for h in homes)
    return known + (people - len(homes)) * KM_PER_PARTICIPANT


def _by_week(bookings: list[ApprovedBooking]) -> list[WeekStats]:
    weeks: dict[str, list[ApprovedBooking]] = {}
    for b in bookings:
        year, week, _ = b.starts_at.isocalendar()
        weeks.setdefault(f"{year}-W{week:02d}", []).append(b)
    return [
        WeekStats(saptamana=w, rezervari=len(bs), ore=round(sum(map(_hours, bs)), 1),
                  participanti=sum(max(b.participants, 0) for b in bs))
        for w, bs in sorted(weeks.items())
    ]


def compute_impact(bookings: Iterable[ApprovedBooking], proiecte: Iterable[Any] = ()) -> ImpactReport:
    """`proiecte`: Proiect rows/dicts (or their `stare` strings), in any state; optional."""
    bookings = list(bookings)
    stari = [_stare(p) for p in proiecte]
    located = [b for b in bookings if b.space_lat is not None and b.space_lon is not None]
    return ImpactReport(
        idei_realizate=len({b.idea_id for b in bookings}),
        spatii_activate=len({b.space_id for b in bookings}),
        rezervari_aprobate=len(bookings),
        ore_folosite=round(sum(map(_hours, bookings)), 1),
        participanti=sum(max(b.participants, 0) for b in bookings),
        km_economisiti=round(sum(map(_km_saved, bookings)), 1),
        ipoteze={
            "km_per_participant": KM_PER_PARTICIPANT,
            "metoda": "dus-întors; din cartierul participantului: (distanța până în centru - distanța până "
                      "la spațiu); altfel km_per_participant",
        },
        pe_cartiere=dict(sorted(Counter(nearest_neighborhood((b.space_lat, b.space_lon)) for b in located).items())),
        pe_tip_spatiu=dict(sorted(Counter(KIND_LABELS.get(b.space_kind, b.space_kind)
                                          for b in bookings if b.space_kind).items())),
        pe_saptamani=_by_week(bookings),
        proiecte_trimise=sum(1 for s in stari if s and s != PROIECT_DRAFT),
        proiecte_cu_acord=sum(1 for s in stari if s == PROIECT_ACORD),
    )
