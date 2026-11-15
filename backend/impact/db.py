"""Contract function backend.impact.compute_impact(session) -> Impact (docs/CONTRACT.md).

Reads P1's tables; definitions agreed with P1 (backend/app/services/impact.py, same counts):
  ore_recuperate    Σ hours of approved bookings (Booking.stare == "aprobat", slot de_la -> pana_la)
  oameni_conectati  distinct users interested in ideas that came to life (approved booking / "rezervata")
  km_economisiti    ESTIMATE, round trip, per participant of an approved booking (Idea.interesati):
                    max(0, home->centre - home->space) × 2 for interested users living in the city
                    (lat/lng within CITY_RADIUS_KM of Cetate), KM_PER_PARTICIPANT for everyone else
  proiecte_active   ideas past the interest threshold: "prag_atins" or "rezervata"
  proiecte_trimise / proiecte_cu_acord  city-hall proposals past draft / with an agreement in principle
"""
from collections import defaultdict

from backend.ai.geo import city_centre, distance_km
from backend.impact.core import KM_PER_PARTICIPANT, PROIECT_ACORD, PROIECT_DRAFT

CITY_RADIUS_KM = 25.0  # a home farther than this from the centre is not in Timișoara: use the constant


def _hours(slot: dict) -> float:
    try:
        (h1, m1), (h2, m2) = (map(int, slot[k].split(":")) for k in ("de_la", "pana_la"))
    except (KeyError, ValueError, AttributeError):
        return 0.0
    return max((h2 * 60 + m2) - (h1 * 60 + m1), 0) / 60


def _in_city(home: tuple[float, float] | None) -> bool:
    return home is not None and distance_km(home, city_centre()) <= CITY_RADIUS_KM


def compute_impact(session):
    from sqlmodel import select

    from backend.app import models
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

    km = 0.0
    for b in approved:
        idea = ideas.get(b.idea_id)
        space = point(spaces.get(b.space_id))
        homes = [h for h in (point(users.get(u)) for u in interested[b.idea_id]) if _in_city(h)]
        count = max(idea.interesati if idea else 0, len(interested[b.idea_id]))
        if space is not None:
            km += sum(max(distance_km(h, city_centre()) - distance_km(h, space), 0.0) * 2 for h in homes)
        else:
            homes = []
        km += max(count - len(homes), 0) * KM_PER_PARTICIPANT
    alive = {b.idea_id for b in approved} | {i.id for i in ideas.values() if i.stare == "rezervata"}
    people = set().union(*(interested[i] for i in alive)) if alive else set()
    proiecte = list(session.exec(select(models.Proiect)).all()) if hasattr(models, "Proiect") else []
    stari = [p.stare for p in proiecte]
    voturi = list(session.exec(select(models.Vot)).all()) if hasattr(models, "Vot") else []
    terenuri = session.exec(select(Space).where(Space.tip == "teren_liber")).all()
    return Impact(
        proiecte_propuse=len(proiecte),
        proiecte_publicate=sum(1 for s in stari if s == "publicat"),
        proiecte_peste_prag=sum(1 for p in proiecte if getattr(p, "voturi", 0) >= getattr(p, "prag_voturi", 3)),
        voturi_total=len(voturi),
        oameni_implicati=len({v.user_id for v in voturi} | {p.autor_id for p in proiecte}),
        terenuri_libere=len(terenuri),
        ore_recuperate=round(sum(_hours(b.slot or {}) for b in approved), 1),
        oameni_conectati=len(people),
        km_economisiti=round(km, 1),
        proiecte_active=sum(1 for i in ideas.values() if i.stare in ("prag_atins", "rezervata")),
        proiecte_trimise=sum(1 for s in stari if s not in (PROIECT_DRAFT, "publicat")),
        proiecte_cu_acord=sum(1 for s in stari if s == PROIECT_ACORD),
    )
