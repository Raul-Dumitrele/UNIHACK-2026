from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from backend.app.db import get_session
from backend.app.models import Space
from backend.app.schemas import Categorie, Dotare, SpaceOut

router = APIRouter(tags=["spaces"])


@router.get("/spaces", response_model=list[SpaceOut])
def list_spaces(
    categorie: Categorie | None = None,
    dotari: list[Dotare] = Query(default=[]),
    capacitate_min: int | None = Query(default=None, ge=0),
    session: Session = Depends(get_session),
):
    spaces = session.exec(select(Space)).all()
    if capacitate_min is not None:
        spaces = [s for s in spaces if s.capacitate >= capacitate_min]
    if dotari:
        spaces = [s for s in spaces if set(dotari) <= set(s.dotari)]
    # TODO(faza 1): filtrul `categorie` (spatiile nu au categorie in contract; de stabilit cu echipa).
    return spaces
