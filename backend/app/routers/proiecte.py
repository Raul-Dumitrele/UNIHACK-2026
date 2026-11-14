from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.app import p3
from backend.app.db import get_session
from backend.app.deps import ERRORS, current_user
from backend.app.models import Idea, Proiect, ProiectEveniment, Space, User
from backend.app.schemas import (
    DecizieIn, InainteazaIn, ProiectCreate, ProiectDetaliuOut, ProiectOut, TrimiteIn,
)

router = APIRouter(tags=["proiecte"])


def get_proiect_or_404(session: Session, proiect_id: str) -> Proiect:
    p = session.get(Proiect, proiect_id)
    if p is None:
        raise HTTPException(404, "Proiectul nu există.")
    return p


@router.post("/ideas/{idea_id}/proiect", response_model=ProiectOut, status_code=201, responses=ERRORS)
def create_proiect(
    idea_id: str,
    body: ProiectCreate,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    idea = session.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(404, "Ideea nu există.")
    space = session.get(Space, body.space_id)
    if space is None:
        raise HTTPException(404, "Spațiul nu există.")
    # TODO(faza B): doar autorul (403); idea.stare in {prag_atins, rezervata} (409);
    # suprafata din cerere sau Space.suprafata_mp, altfel 422.
    suprafata = body.suprafata_mp or space.suprafata_mp
    if not suprafata:
        raise HTTPException(422, "Date invalide - suprafata_mp: lipsește și spațiul nu are suprafață.")
    referinte = p3.find_references(body.tip_amenajare, suprafata)
    cost = p3.estimate_cost(referinte, suprafata)
    dosar = p3.generate_dosar(idea, space, body.tip_amenajare, suprafata, referinte, cost)
    proiect = Proiect(
        idea_id=idea.id, space_id=space.id, autor_id=idea.author_id, tip_amenajare=body.tip_amenajare,
        suprafata_mp=suprafata, dosar=dosar.model_dump(mode="json"),
        referinte=[r.model_dump(mode="json") for r in referinte], cost=cost.model_dump(mode="json"),
    )
    session.add(proiect)
    session.commit()
    session.refresh(proiect)
    return proiect


@router.get("/proiecte", response_model=list[ProiectOut], responses=ERRORS)
def list_proiecte(user: User = Depends(current_user), session: Session = Depends(get_session)):
    # TODO(faza B): autor -> ale lui; primarie -> toate cu stare != draft; verificator -> desemnat.
    return []


@router.get("/proiecte/{proiect_id}", response_model=ProiectDetaliuOut, responses=ERRORS)
def get_proiect(proiect_id: str, _: User = Depends(current_user), session: Session = Depends(get_session)):
    p = get_proiect_or_404(session, proiect_id)
    ev = session.exec(
        select(ProiectEveniment).where(ProiectEveniment.proiect_id == p.id).order_by(ProiectEveniment.created_at)
    ).all()
    return ProiectDetaliuOut.model_validate({**p.model_dump(), "evenimente": ev}, from_attributes=True)


@router.post("/proiecte/{proiect_id}/trimite", response_model=ProiectOut, responses=ERRORS)
def trimite(proiect_id: str, body: TrimiteIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    p = get_proiect_or_404(session, proiect_id)
    # TODO(faza B): autor (403); draft|clarificari -> trimis (409); eveniment; notificare catre rolul primarie.
    return p


@router.post("/proiecte/{proiect_id}/inainteaza", response_model=ProiectOut, responses=ERRORS)
def inainteaza(proiect_id: str, body: InainteazaIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    p = get_proiect_or_404(session, proiect_id)
    # TODO(faza B): rol primarie (403); trimis -> in_verificare (409); verificator_id valid (422);
    # eveniment; notificare catre verificator.
    return p


@router.post("/proiecte/{proiect_id}/decizie", response_model=ProiectOut, responses=ERRORS)
def decizie(proiect_id: str, body: DecizieIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    p = get_proiect_or_404(session, proiect_id)
    # TODO(faza B): doar verificatorul desemnat (403); in_verificare -> decizie (409);
    # eveniment; notificare catre autor si primarie.
    return p
