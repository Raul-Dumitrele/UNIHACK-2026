from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from backend.app.db import get_session
from backend.app.models import User


def current_user(
    x_user_id: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    if not x_user_id:
        raise HTTPException(401, "Lipsește antetul X-User-Id.")
    user = session.get(User, x_user_id)
    if user is None:
        raise HTTPException(401, "Utilizator necunoscut.")
    return user



def optional_user(
    x_user_id: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User | None:
    """Like current_user, but anonymous callers get None instead of 401."""
    return session.get(User, x_user_id) if x_user_id else None


ERRORS = {
    401: {"description": "X-User-Id lipsă sau necunoscut"},
    403: {"description": "Acțiune interzisă"},
    404: {"description": "Resursa nu există"},
    409: {"description": "Conflict"},
}
