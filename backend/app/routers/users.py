from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from backend.app.db import get_session
from backend.app.models import User
from backend.app.schemas import UserOut

router = APIRouter(tags=["users"])


@router.get("/users", response_model=list[UserOut])
def list_users(session: Session = Depends(get_session)):
    return session.exec(select(User)).all()
