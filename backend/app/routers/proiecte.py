from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from backend.app import p3
from backend.app.db import get_session
from backend.app.deps import ERRORS, current_user
from backend.app.models import Idea, Proiect, ProiectEveniment, Space, User, now_utc
from backend.app.schemas import (
    DecizieIn, InainteazaIn, ListaMateriale, PlanOut, ProiectCreate, ProiectDetaliuOut, ProiectDirectCreate,
    ProiectOut, TrimiteIn,
)
from backend.app.services.notify import notify, users_with_role

router = APIRouter(tags=["proiecte"])


def get_proiect_or_404(session: Session, proiect_id: str) -> Proiect:
    p = session.get(Proiect, proiect_id)
    if p is None:
        raise HTTPException(404, "Proiectul nu există.")
    return p


def _can_see(user: User, p: Proiect) -> bool:
    if user.id == p.autor_id:
        return True
    if user.rol == "primarie":
        return p.stare != "draft"
    return user.rol == "verificator" and p.verificator_id == user.id


def _transition(session: Session, p: Proiect, user: User, stare: str, mesaj: str | None) -> None:
    """Apply the new state and record a ProiectEveniment. The caller commits."""
    p.stare = stare
    p.updated_at = now_utc()
    session.add(p)
    session.add(ProiectEveniment(proiect_id=p.id, user_id=user.id, stare_noua=stare, mesaj=mesaj))


def _titlu(p: Proiect) -> str:
    return p.dosar.get("titlu", "proiect")


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
    if idea.author_id != user.id:
        raise HTTPException(403, "Doar autorul ideii poate crea un proiect.")
    if idea.stare not in ("prag_atins", "rezervata"):
        raise HTTPException(409, "Ideea trebuie să fi atins pragul de interes sau să fie rezervată.")
    return _build_proiect(session, user, idea, space, body.tip_amenajare, body.suprafata_mp)


def _build_proiect(session: Session, user: User, idea: Idea, space: Space, tip: str, suprafata_ceruta: int | None) -> Proiect:
    """find_references -> estimate_cost -> generate_dosar, then a draft Proiect with its first event."""
    suprafata = suprafata_ceruta or space.suprafata_mp
    if not suprafata:
        raise HTTPException(422, "Date invalide - suprafata_mp: lipsește și spațiul nu are suprafață.")
    referinte = p3.find_references(tip, suprafata)
    cost = p3.estimate_cost(referinte, suprafata)
    dosar = p3.generate_dosar(idea, space, tip, suprafata, referinte, cost)
    proiect = Proiect(
        idea_id=idea.id, space_id=space.id, autor_id=idea.author_id, tip_amenajare=tip,
        suprafata_mp=suprafata, dosar=dosar.model_dump(mode="json"),
        referinte=[r.model_dump(mode="json") for r in referinte], cost=cost.model_dump(mode="json"),
    )
    session.add(proiect)
    session.flush()
    session.add(ProiectEveniment(proiect_id=proiect.id, user_id=user.id, stare_noua="draft"))
    session.commit()
    session.refresh(proiect)
    return proiect


@router.post("/proiecte", response_model=ProiectDetaliuOut, status_code=201, responses=ERRORS)
def create_proiect_direct(body: ProiectDirectCreate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """A project straight on a free plot: the description becomes a (hidden) idea owned by the author."""
    space = session.get(Space, body.space_id)
    if space is None:
        raise HTTPException(404, "Spațiul nu există.")
    if not (body.suprafata_mp or space.suprafata_mp):
        raise HTTPException(422, "Date invalide - suprafata_mp: lipsește și spațiul nu are suprafață.")
    structurat = p3.structure_idea(body.descriere)
    idea = Idea(
        author_id=user.id, titlu=structurat.rezumat[:80], descriere=body.descriere,
        structurat=structurat.model_dump(), prag=1, interesati=0, stare="prag_atins",
    )
    session.add(idea)
    session.flush()
    p = _build_proiect(session, user, idea, space, body.tip_amenajare, body.suprafata_mp)
    return _detaliu(session, p)


@router.get("/proiecte", response_model=list[ProiectOut], responses=ERRORS)
def list_proiecte(user: User = Depends(current_user), session: Session = Depends(get_session)):
    q = select(Proiect)
    if user.rol == "primarie":
        q = q.where(Proiect.stare != "draft")
    elif user.rol == "verificator":
        q = q.where(Proiect.verificator_id == user.id)
    else:
        q = q.where(Proiect.autor_id == user.id)
    return session.exec(q.order_by(Proiect.updated_at.desc())).all()


@router.get("/proiecte/{proiect_id}", response_model=ProiectDetaliuOut, responses=ERRORS)
def get_proiect(proiect_id: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    p = get_proiect_or_404(session, proiect_id)
    if not _can_see(user, p):
        raise HTTPException(403, "Nu ai acces la acest proiect.")
    return _detaliu(session, p)


def _detaliu(session: Session, p: Proiect) -> ProiectDetaliuOut:
    ev = session.exec(
        select(ProiectEveniment).where(ProiectEveniment.proiect_id == p.id).order_by(ProiectEveniment.created_at)
    ).all()
    return ProiectDetaliuOut.model_validate({**p.model_dump(), "evenimente": ev}, from_attributes=True)


@router.post("/proiecte/{proiect_id}/trimite", response_model=ProiectOut, responses=ERRORS)
def trimite(proiect_id: str, body: TrimiteIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    p = get_proiect_or_404(session, proiect_id)
    if p.autor_id != user.id:
        raise HTTPException(403, "Doar autorul proiectului îl poate trimite.")
    if p.stare not in ("draft", "clarificari"):
        raise HTTPException(409, "Proiectul nu poate fi trimis din starea curentă.")
    _transition(session, p, user, "trimis", body.mesaj)
    for primarie in users_with_role(session, "primarie"):
        notify(session, primarie.id, p.idea_id, f"Proiect nou trimis spre analiză: „{_titlu(p)}”.", proiect_id=p.id)
    session.commit()
    session.refresh(p)
    return p


@router.post("/proiecte/{proiect_id}/inainteaza", response_model=ProiectOut, responses=ERRORS)
def inainteaza(proiect_id: str, body: InainteazaIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    p = get_proiect_or_404(session, proiect_id)
    if user.rol != "primarie":
        raise HTTPException(403, "Doar Primăria poate înainta un proiect la verificare.")
    if p.stare != "trimis":
        raise HTTPException(409, "Doar un proiect trimis poate fi înaintat la verificare.")
    verificator = session.get(User, body.verificator_id)
    if verificator is None or verificator.rol != "verificator":
        raise HTTPException(422, "Date invalide - verificator_id: utilizatorul nu există sau nu este verificator.")
    p.verificator_id = verificator.id
    _transition(session, p, user, "in_verificare", None)
    notify(session, verificator.id, p.idea_id, f"Ai de verificat proiectul „{_titlu(p)}”.", proiect_id=p.id)
    session.commit()
    session.refresh(p)
    return p


@router.post("/proiecte/{proiect_id}/decizie", response_model=ProiectOut, responses=ERRORS)
def decizie(proiect_id: str, body: DecizieIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    p = get_proiect_or_404(session, proiect_id)
    if p.verificator_id != user.id:
        raise HTTPException(403, "Doar verificatorul desemnat poate decide.")
    if p.stare != "in_verificare":
        raise HTTPException(409, "Proiectul nu este în verificare.")
    _transition(session, p, user, body.stare, body.mesaj)
    text = {
        "acord_de_principiu": "a primit acord de principiu (simulat)",
        "respins": "a fost respins",
        "clarificari": "necesită clarificări",
    }[body.stare]
    mesaj = f"Proiectul „{_titlu(p)}” {text}." + (f" {body.mesaj}" if body.mesaj else "")
    for target in {p.autor_id, *(u.id for u in users_with_role(session, "primarie"))}:
        notify(session, target, p.idea_id, mesaj, proiect_id=p.id)
    session.commit()
    session.refresh(p)
    return p


DOCUMENTE = ("plan.svg", "plan.dxf", "dosar.pdf", "materiale.csv")


def _visible_with_space(session: Session, proiect_id: str, user: User) -> tuple[Proiect, Space | None]:
    p = get_proiect_or_404(session, proiect_id)
    if not _can_see(user, p):
        raise HTTPException(403, "Nu ai acces la acest proiect.")
    return p, session.get(Space, p.space_id)


@router.get("/proiecte/{proiect_id}/plan", response_model=PlanOut, responses=ERRORS)
def proiect_plan(proiect_id: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    p, space = _visible_with_space(session, proiect_id, user)
    return p3.plan_json(p, space)


@router.get("/proiecte/{proiect_id}/materiale", response_model=ListaMateriale, responses=ERRORS)
def proiect_materiale(proiect_id: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    p, space = _visible_with_space(session, proiect_id, user)
    return p3.materiale_json(p, space)


@router.get(
    "/proiecte/{proiect_id}/documente/{nume}",
    responses={**ERRORS, 200: {"description": "fișierul (SVG, DXF, PDF sau CSV)", "content": {
        "image/svg+xml": {}, "application/dxf": {}, "application/pdf": {}, "text/csv": {}}}},
    response_class=Response,
)
def proiect_document(proiect_id: str, nume: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if nume not in DOCUMENTE:
        raise HTTPException(404, "Documentul nu există. Variante: " + ", ".join(DOCUMENTE) + ".")
    p, space = _visible_with_space(session, proiect_id, user)
    content, media = p3.build_documente(p, space)[nume]
    return Response(content, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="proiect-{p.id}-{nume}"'})
