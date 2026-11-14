from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, or_, select

from backend.app.db import get_session
from backend.app.deps import ERRORS, current_user, optional_user
from backend.app.models import Proiect, Space, User
from backend.app.schemas import Categorie, Dotare, ProiectOut, SpaceOut, TerenCreate

router = APIRouter(tags=["spaces"])


@router.get("/spaces", response_model=list[SpaceOut])
def list_spaces(
    categorie: Categorie | None = None,
    dotari: list[Dotare] = Query(default=[]),
    capacitate_min: int | None = Query(default=None, ge=0),
    tip: str | None = Query(default=None, description="ex. teren_liber"),
    session: Session = Depends(get_session),
):
    q = select(Space) if tip is None else select(Space).where(Space.tip == tip)
    spaces = session.exec(q).all()
    if capacitate_min is not None:
        spaces = [s for s in spaces if s.capacitate >= capacitate_min]
    if dotari:
        spaces = [s for s in spaces if set(dotari) <= set(s.dotari)]
    # `categorie` is accepted per contract but has no effect: Space has no category field (see report).
    return spaces


def _cartier(lat: float, lng: float) -> str | None:
    try:
        from backend.ai.geo import nearest_neighborhood
        return nearest_neighborhood((lat, lng))
    except Exception:  # district data unavailable: the plot is still valid without it
        return None


@router.post("/spaces", response_model=SpaceOut, status_code=201, responses=ERRORS)
def mark_plot(body: TerenCreate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """A free plot marked on the map by a user. Unverified: owner, legal status and availability are unknown."""
    space = Space(
        nume=body.nume, tip="teren_liber", lat=body.lat, lng=body.lng, capacitate=0, dotari=[], sloturi=[],
        owner_id=user.id, is_demo=False, suprafata_mp=body.suprafata_mp, descriere=body.descriere,
        cartier=_cartier(body.lat, body.lng), sursa="marcat_de_utilizator", status_verificare="neverificat",
    )
    session.add(space)
    session.commit()
    session.refresh(space)
    return space


@router.get("/spaces/{space_id}/proiecte", response_model=list[ProiectOut], responses=ERRORS)
def space_projects(space_id: str, user: User | None = Depends(optional_user), session: Session = Depends(get_session)):
    """Projects proposed on a plot: every submitted one (not a draft) plus the caller's own drafts."""
    if session.get(Space, space_id) is None:
        raise HTTPException(404, "Spațiul nu există.")
    visible = Proiect.stare != "draft"
    if user is not None:
        visible = or_(visible, Proiect.autor_id == user.id)
    q = select(Proiect).where(Proiect.space_id == space_id, visible).order_by(Proiect.updated_at.desc())
    return session.exec(q).all()
