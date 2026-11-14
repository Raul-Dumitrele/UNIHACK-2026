from sqlmodel import Session, select

from backend.app.models import Notification, User


def notify(
    session: Session, user_id: str, idea_id: str, mesaj: str,
    booking_id: str | None = None, proiect_id: str | None = None,
) -> None:
    """In-app notification only. The caller commits."""
    session.add(Notification(user_id=user_id, idea_id=idea_id, mesaj=mesaj, booking_id=booking_id, proiect_id=proiect_id))


def users_with_role(session: Session, rol: str) -> list[User]:
    return list(session.exec(select(User).where(User.rol == rol)).all())
