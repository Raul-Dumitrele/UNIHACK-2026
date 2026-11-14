"""Impact numbers computed from the database (P1 fallback when the P3 function does not take a Session)."""
from sqlmodel import Session, select

from backend.app.models import Booking, Idea, Interest, Proiect
from backend.app.schemas import Impact
from backend.app.services import slots as sl

KM_PER_PARTICIPANT = 4.0  # estimate, same assumption as docs/DATA.md (P3)


def compute_local(session: Session) -> Impact:
    approved = session.exec(select(Booking).where(Booking.stare == "aprobat")).all()
    ore = sum(sl.duration(b.slot) for b in approved) / 60
    ideas = {i.id: i for i in session.exec(select(Idea)).all()}
    participants = 0
    for b in approved:
        idea = ideas.get(b.idea_id)
        participants += idea.interesati if idea else 0
    booked_idea_ids = {i.id for i in ideas.values() if i.stare == "rezervata"}
    interested = {
        r.user_id for r in session.exec(select(Interest)).all() if r.idea_id in booked_idea_ids
    }
    proiecte = session.exec(select(Proiect)).all()
    return Impact(
        ore_recuperate=round(ore, 1),
        oameni_conectati=len(interested),
        km_economisiti=round(participants * KM_PER_PARTICIPANT, 1),
        # "active" = ideas that reached the interest threshold or are booked.
        proiecte_active=sum(1 for i in ideas.values() if i.stare in ("prag_atins", "rezervata")),
        proiecte_trimise=sum(1 for p in proiecte if p.stare != "draft"),
        proiecte_cu_acord=sum(1 for p in proiecte if p.stare == "acord_de_principiu"),
    )
