from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from backend.app import p3
from backend.app.db import get_session
from backend.app.deps import ERRORS, current_user
from backend.app.models import Idea, Interest, Space, User
from backend.app.services.matching import score_space
from backend.app.services.notify import notify
from backend.app.schemas import IdeaCreate, IdeaOut, MatchOut, OwnerMessageIn, OwnerMessageOut

router = APIRouter(tags=["ideas"])


def get_idea_or_404(session: Session, idea_id: str) -> Idea:
    idea = session.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(404, "Ideea nu există.")
    return idea


@router.post("/ideas", response_model=IdeaOut, status_code=201, responses=ERRORS)
def create_idea(body: IdeaCreate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    structurat = p3.structure_idea(body.descriere)
    idea = Idea(
        author_id=user.id,
        titlu=(body.titlu or structurat.rezumat)[:80],
        descriere=body.descriere,
        structurat=structurat.model_dump(),
        prag=body.prag or 5,
    )
    session.add(idea)
    session.commit()
    session.refresh(idea)
    return idea


@router.get("/ideas", response_model=list[IdeaOut])
def list_ideas(session: Session = Depends(get_session)):
    return session.exec(select(Idea).order_by(Idea.created_at.desc())).all()


@router.get("/ideas/{idea_id}", response_model=IdeaOut, responses=ERRORS)
def get_idea(idea_id: str, session: Session = Depends(get_session)):
    return get_idea_or_404(session, idea_id)


@router.get("/ideas/{idea_id}/matches", response_model=list[MatchOut], responses=ERRORS)
def idea_matches(idea_id: str, session: Session = Depends(get_session)):
    idea = get_idea_or_404(session, idea_id)
    interested = session.exec(select(User).join(Interest, Interest.user_id == User.id).where(Interest.idea_id == idea.id)).all()
    people = interested or [session.get(User, idea.author_id)]
    points = [(u.lat, u.lng) for u in people if u]
    matches = []
    for space in session.exec(select(Space)).all():
        if not space.sloturi:  # only spaces that still have free slots
            continue
        r = score_space(idea.structurat, space, points, len(interested))
        matches.append(MatchOut(space=space, **r))
    return sorted(matches, key=lambda m: m.scor, reverse=True)


@router.post("/ideas/{idea_id}/interest", response_model=IdeaOut, status_code=201, responses=ERRORS)
def add_interest(idea_id: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    idea = get_idea_or_404(session, idea_id)
    try:
        session.add(Interest(user_id=user.id, idea_id=idea.id))
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Ți-ai exprimat deja interesul pentru această idee.")
    idea.interesati += 1
    if idea.interesati >= idea.prag and idea.stare == "deschisa":
        idea.stare = "prag_atins"
        notify(session, idea.author_id, idea.id, f"Ideea „{idea.titlu}” a atins pragul de interes ({idea.prag}). Poți cere o rezervare.")
    session.add(idea)
    session.commit()
    session.refresh(idea)
    return idea


@router.post("/ideas/{idea_id}/owner-message", response_model=OwnerMessageOut, responses=ERRORS)
def owner_message(
    idea_id: str,
    body: OwnerMessageIn,
    _: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    idea = get_idea_or_404(session, idea_id)
    space = session.get(Space, body.space_id)
    if space is None:
        raise HTTPException(404, "Spațiul nu există.")
    return OwnerMessageOut(mesaj=p3.owner_message(idea, space, body.slot))
