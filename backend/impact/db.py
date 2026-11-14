"""Contract function backend.impact.compute_impact(session) -> Impact (docs/CONTRACT.md).

Reads P1's tables. Only approved bookings count (Booking.stare == "aprobat"):
  ore_recuperate   Σ hours of the approved weekly slots (Booking.slot de_la -> pana_la)
  oameni_conectati distinct people around ideas with an approved booking (authors + interested users)
  km_economisiti   ESTIMATE, round trip per participant: max(0, home->centre - home->space) × 2 when the
                   user's lat/lng is known, else KM_PER_PARTICIPANT; "centre" = Cetate (see backend.ai.geo)
  proiecte_active  ideas that came to life: an approved booking (state "rezervata")
"""
from collections import defaultdict

from backend.ai.geo import city_centre, distance_km
from backend.impact.core import KM_PER_PARTICIPANT


def _hours(slot: dict) -> float:
    try:
        (h1, m1), (h2, m2) = (map(int, slot[k].split(":")) for k in ("de_la", "pana_la"))
    except (KeyError, ValueError, AttributeError):
        return 0.0
    return max((h2 * 60 + m2) - (h1 * 60 + m1), 0) / 60


def _km(home: tuple[float, float] | None, space: tuple[float, float] | None) -> float:
    if home is None or space is None:
        return KM_PER_PARTICIPANT
    return max(distance_km(home, city_centre()) - distance_km(home, space), 0.0) * 2


def compute_impact(session):
    from sqlmodel import select

    from backend.app.models import Booking, Idea, Interest, Space, User
    from backend.app.schemas import Impact

    approved = session.exec(select(Booking).where(Booking.stare == "aprobat")).all()
    spaces = {s.id: s for s in session.exec(select(Space)).all()}
    users = {u.id: u for u in session.exec(select(User)).all()}
    ideas = {i.id: i for i in session.exec(select(Idea)).all()}
    interested: dict[str, set[str]] = defaultdict(set)
    for it in session.exec(select(Interest)).all():
        interested[it.idea_id].add(it.user_id)

    def point(obj) -> tuple[float, float] | None:
        lat, lng = getattr(obj, "lat", None), getattr(obj, "lng", None)
        return (lat, lng) if lat is not None and lng is not None else None

    people: set[str] = set()
    km = 0.0
    for b in approved:
        participants = interested[b.idea_id]
        idea = ideas.get(b.idea_id)
        people |= participants | ({idea.author_id} if idea else set())
        space = point(spaces.get(b.space_id))
        km += sum(_km(point(users.get(u)), space) for u in participants)
    active = {b.idea_id for b in approved} | {i.id for i in ideas.values() if i.stare == "rezervata"}
    return Impact(
        ore_recuperate=round(sum(_hours(b.slot or {}) for b in approved), 1),
        oameni_conectati=len(people),
        km_economisiti=round(km, 1),
        proiecte_active=len(active),
    )
