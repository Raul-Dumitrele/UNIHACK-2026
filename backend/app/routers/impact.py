from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.app import p3
from backend.app.db import get_session
from backend.app.schemas import Impact

router = APIRouter(tags=["impact"])


@router.get("/impact", response_model=Impact)
def get_impact(session: Session = Depends(get_session)):
    return p3.compute_impact(session)
