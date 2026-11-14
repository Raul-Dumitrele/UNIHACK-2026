from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.app.db import get_session
from backend.app.deps import ERRORS, current_user
from backend.app.models import Notification, User
from backend.app.schemas import NotificationOut

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationOut], responses=ERRORS)
def list_notifications(user: User = Depends(current_user), session: Session = Depends(get_session)):
    q = select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())
    return session.exec(q).all()


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut, responses=ERRORS)
def mark_read(notification_id: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    n = session.get(Notification, notification_id)
    if n is None:
        raise HTTPException(404, "Notificarea nu există.")
    if n.user_id != user.id:
        raise HTTPException(403, "Notificarea nu îți aparține.")
    n.citita = True
    session.add(n)
    session.commit()
    session.refresh(n)
    return n
