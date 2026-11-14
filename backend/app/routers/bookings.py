from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.app.db import get_session
from backend.app.deps import ERRORS, current_user
from backend.app.models import Booking, Idea, Space, User
from backend.app.schemas import BookingCreate, BookingOut, BookingUpdate

router = APIRouter(tags=["bookings"])


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
    # TODO(faza 1): slotul trebuie sa fie continut intr-un slot din Space.sloturi (409) + notificare catre proprietar.
    booking = Booking(idea_id=idea.id, space_id=space.id, slot=body.slot.model_dump())
    session.add(booking)
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
    # TODO(faza 1): la aprobat -> idee rezervata, slot scos din Space.sloturi, cereri suprapuse refuzate;
    # notificare catre autor la aprobat si la refuzat.
    booking.stare = body.stare
    session.add(booking)
    session.commit()
    session.refresh(booking)
    return booking
