from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlmodel import Session, select

from backend.app.db import get_session
from backend.app.deps import ERRORS, current_user
from backend.app.models import Booking, Idea, Space, User
from backend.app.schemas import BookingCreate, BookingOut, BookingUpdate
from backend.app.services import slots as sl
from backend.app.services.notify import notify

router = APIRouter(tags=["bookings"])


@router.get("/bookings", response_model=list[BookingOut], responses=ERRORS)
def list_bookings(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Requests I made (author of the idea) plus requests for spaces I own."""
    mine = select(Idea.id).where(Idea.author_id == user.id)
    owned = select(Space.id).where(Space.owner_id == user.id)
    q = select(Booking).where(or_(Booking.idea_id.in_(mine), Booking.space_id.in_(owned)))
    return session.exec(q.order_by(Booking.created_at.desc())).all()


@router.post("/bookings", response_model=BookingOut, status_code=201, responses=ERRORS)
def create_booking(body: BookingCreate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    idea = session.get(Idea, body.idea_id)
    if idea is None:
        raise HTTPException(404, "Ideea nu există.")
    space = session.get(Space, body.space_id)
    if space is None:
        raise HTTPException(404, "Spațiul nu există.")
    if idea.author_id != user.id:
        raise HTTPException(403, "Doar autorul ideii poate cere o rezervare.")
    if idea.stare != "prag_atins":
        raise HTTPException(409, "Ideea nu a atins încă pragul de interes.")
    slot = body.slot.model_dump()
    if not any(sl.contains(free, slot) for free in space.sloturi):
        raise HTTPException(409, "Slotul cerut nu este liber în acest spațiu.")
    booking = Booking(idea_id=idea.id, space_id=space.id, slot=slot, mesaj=body.mesaj)
    session.add(booking)
    session.flush()
    notify(session, space.owner_id, idea.id, f"Cerere nouă de rezervare pentru „{space.nume}” ({sl.fmt_slot(slot)}): {idea.titlu}.", booking_id=booking.id)
    session.commit()
    session.refresh(booking)
    return booking


@router.patch("/bookings/{booking_id}", response_model=BookingOut, responses=ERRORS)
def decide_booking(
    booking_id: str,
    body: BookingUpdate,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(404, "Rezervarea nu există.")
    space = session.get(Space, booking.space_id)
    if space is None or space.owner_id != user.id:
        raise HTTPException(403, "Doar proprietarul spațiului poate aproba sau refuza.")
    if booking.stare != "cerut":
        raise HTTPException(409, "Cererea a fost deja soluționată.")
    idea = session.get(Idea, booking.idea_id)
    booking.stare = body.stare
    session.add(booking)
    if body.stare == "aprobat":
        idea.stare = "rezervata"
        session.add(idea)
        space.sloturi = sl.subtract(space.sloturi, booking.slot)  # reassign so the JSON change is saved
        session.add(space)
        others = session.exec(
            select(Booking).where(Booking.space_id == space.id, Booking.stare == "cerut", Booking.id != booking.id)
        ).all()
        for other in others:
            if sl.overlap(other.slot, booking.slot):
                other.stare = "refuzat"
                session.add(other)
                notify(session, session.get(Idea, other.idea_id).author_id, other.idea_id,
                       f"Cererea ta pentru „{space.nume}” a fost refuzată: slotul a fost deja rezervat.", booking_id=other.id)
        notify(session, idea.author_id, idea.id, f"Rezervarea pentru „{space.nume}” ({sl.fmt_slot(booking.slot)}) a fost aprobată.", booking_id=booking.id)
    else:
        notify(session, idea.author_id, idea.id, f"Rezervarea pentru „{space.nume}” ({sl.fmt_slot(booking.slot)}) a fost refuzată.", booking_id=booking.id)
    session.commit()
    session.refresh(booking)
    return booking
