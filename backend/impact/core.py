"""Impact dashboard numbers. Pure function over approved bookings; formulas documented in docs/DATA.md.

Signature is a proposal for docs/CONTRACT.md: P1 maps approved Booking rows to ApprovedBooking.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel

# Assumption (estimate): each participant who uses a space in their own area instead of travelling
# to a central venue avoids KM_PER_PARTICIPANT km of car travel (round trip). See docs/DATA.md.
KM_PER_PARTICIPANT = 4.0


@dataclass(frozen=True)
class ApprovedBooking:
    idea_id: str
    space_id: str
    starts_at: datetime
    ends_at: datetime
    participants: int  # confirmed community interest for the idea (interest count)


class ImpactReport(BaseModel):
    idei_realizate: int
    spatii_activate: int
    rezervari_aprobate: int
    ore_folosite: float
    participanti: int
    km_economisiti: float
    km_economisiti_estimare: bool = True  # always an estimate; UI must label it so
    ipoteze: dict[str, float] = {"km_per_participant": KM_PER_PARTICIPANT}


def compute_impact(bookings: Iterable[ApprovedBooking]) -> ImpactReport:
    bookings = list(bookings)
    hours = sum(max((b.ends_at - b.starts_at).total_seconds(), 0) / 3600 for b in bookings)
    participants = sum(max(b.participants, 0) for b in bookings)
    return ImpactReport(
        idei_realizate=len({b.idea_id for b in bookings}),
        spatii_activate=len({b.space_id for b in bookings}),
        rezervari_aprobate=len(bookings),
        ore_folosite=round(hours, 1),
        participanti=participants,
        km_economisiti=round(participants * KM_PER_PARTICIPANT, 1),
    )
