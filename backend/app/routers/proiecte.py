from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from backend.app import p3
from backend.app.db import get_session
from backend.app.deps import ERRORS, current_user, optional_user
from backend.app.models import Idea, Proiect, ProiectEveniment, Space, User, Vot, now_utc
from backend.app.schemas import (
    AnalizaIn, AnalizaOut, DecizieIn, InainteazaIn, ListaMateriale, PlanOut, ProiectCreate, ProiectDetaliuOut,
    ProiectDirectCreate, ProiectOut, TrimiteIn, VotOut,
)
from backend.app.services.notify import notify, users_with_role

router = APIRouter(tags=["proiecte"])
PUBLIC_STATES = ("publicat", "trimis", "in_verificare", "clarificari", "acord_de_principiu", "respins")


def get_proiect_or_404(session: Session, proiect_id: str) -> Proiect:
    p = session.get(Proiect, proiect_id)
    if p is None:
        raise HTTPException(404, "Proiectul nu există.")
    return p


def _can_see(user: User | None, p: Proiect) -> bool:
    """Drafts belong to their author; everything published is public (the community votes on it)."""
    if p.stare != "draft":
        return True
    return user is not None and user.id == p.autor_id


def _transition(session: Session, p: Proiect, user: User, stare: str, mesaj: str | None) -> None:
    """Apply the new state and record a ProiectEveniment. The caller commits."""
    p.stare = stare
    p.updated_at = now_utc()
    session.add(p)
    session.add(ProiectEveniment(proiect_id=p.id, user_id=user.id, stare_noua=stare, mesaj=mesaj))


def _titlu(p: Proiect) -> str:
    return p.dosar.get("titlu", "proiect")


def _send_to_city_hall(session: Session, p: Proiect, user: User, mesaj: str | None) -> None:
    _transition(session, p, user, "trimis", mesaj)
    for primarie in users_with_role(session, "primarie"):
        notify(session, primarie.id, p.idea_id, f"Proiect nou trimis spre analiză: „{_titlu(p)}” "
                                                f"({p.voturi} susținători).", proiect_id=p.id)


@router.post("/proiecte/analiza", response_model=AnalizaOut, responses=ERRORS)
def analiza(body: AnalizaIn, _: User = Depends(current_user), session: Session = Depends(get_session)):
    """Specification + feasibility for a proposal on a plot, before generating the project (no dossier, no cost)."""
    space = session.get(Space, body.space_id) if body.space_id else None
    if body.space_id and space is None:
        raise HTTPException(404, "Spațiul nu există.")
    area = body.suprafata_mp or (space.suprafata_mp if space else None)
    return p3.analiza_proiect(body.tip_amenajare, area, space, body.descriere)


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


def _build_proiect(session: Session, user: User, idea: Idea, space: Space, tip: str, suprafata_ceruta: int | None,
                   descriere: str | None = None) -> Proiect:
    """specificatie -> fezabilitate -> referinte -> materiale -> cost -> acte -> memoriu -> dosar (backend.ai pipeline)."""
    suprafata = suprafata_ceruta or space.suprafata_mp
    if not suprafata:
        raise HTTPException(422, "Date invalide - suprafata_mp: lipsește și spațiul nu are suprafață.")
    r = p3.build_proiect(idea, space, tip, suprafata, descriere or idea.descriere)
    proiect = Proiect(
        idea_id=idea.id, space_id=space.id, autor_id=idea.author_id, tip_amenajare=r["tip_amenajare"],
        suprafata_mp=suprafata, dosar=r["dosar"], referinte=r["referinte"], cost=r["cost"],
        specificatie=r["specificatie"], fezabilitate=r["fezabilitate"],
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
    p = _build_proiect(session, user, idea, space, body.tip_amenajare, body.suprafata_mp, body.descriere)
    return _detaliu(session, p, user)


@router.get("/proiecte/publice", response_model=list[ProiectOut])
def list_publice(session: Session = Depends(get_session)):
    """Every project the community can see and vote on (anything past draft), newest activity first."""
    q = select(Proiect).where(Proiect.stare != "draft").order_by(Proiect.updated_at.desc())
    return session.exec(q).all()


@router.get("/proiecte", response_model=list[ProiectOut], responses=ERRORS)
def list_proiecte(user: User = Depends(current_user), session: Session = Depends(get_session)):
    q = select(Proiect)
    if user.rol == "primarie":
        q = q.where(Proiect.stare.in_(("trimis", "in_verificare", "clarificari", "acord_de_principiu", "respins")))
    elif user.rol == "verificator":
        q = q.where(Proiect.verificator_id == user.id)
    else:
        q = q.where(Proiect.autor_id == user.id)
    return session.exec(q.order_by(Proiect.updated_at.desc())).all()


@router.get("/proiecte/{proiect_id}", response_model=ProiectDetaliuOut, responses=ERRORS)
def get_proiect(proiect_id: str, user: User | None = Depends(optional_user), session: Session = Depends(get_session)):
    p = get_proiect_or_404(session, proiect_id)
    if not _can_see(user, p):
        raise HTTPException(403, "Nu ai acces la acest proiect.")
    return _detaliu(session, p, user)


def _detaliu(session: Session, p: Proiect, user: User | None = None) -> ProiectDetaliuOut:
    ev = session.exec(
        select(ProiectEveniment).where(ProiectEveniment.proiect_id == p.id).order_by(ProiectEveniment.created_at)
    ).all()
    voted = False
    if user is not None:
        voted = session.exec(select(Vot).where(Vot.proiect_id == p.id, Vot.user_id == user.id)).first() is not None
    return ProiectDetaliuOut.model_validate({**p.model_dump(), "evenimente": ev, "votat_de_mine": voted},
                                            from_attributes=True)


@router.post("/proiecte/{proiect_id}/publica", response_model=ProiectOut, responses=ERRORS)
def publica(proiect_id: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """The author publishes the draft: everyone can see it and vote; at prag_voturi it goes to the city hall."""
    p = get_proiect_or_404(session, proiect_id)
    if p.autor_id != user.id:
        raise HTTPException(403, "Doar autorul proiectului îl poate publica.")
    if p.stare != "draft":
        raise HTTPException(409, "Doar o ciornă poate fi publicată.")
    _transition(session, p, user, "publicat", None)
    session.commit()
    session.refresh(p)
    return p


@router.post("/proiecte/{proiect_id}/vot", response_model=VotOut, status_code=201, responses=ERRORS)
def voteaza(proiect_id: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """One vote per user per project (409 on a second one). Reaching the threshold sends the project to the city hall."""
    p = get_proiect_or_404(session, proiect_id)
    if p.stare == "draft":
        raise HTTPException(409, "Proiectul nu este publicat încă.")
    if p.stare in ("acord_de_principiu", "respins"):
        raise HTTPException(409, "Proiectul are deja o decizie; votul s-a încheiat.")
    try:
        session.add(Vot(proiect_id=p.id, user_id=user.id))
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Ai votat deja acest proiect.")
    p.voturi += 1
    p.updated_at = now_utc()
    session.add(p)
    if p.stare == "publicat" and p.voturi >= p.prag_voturi:
        _send_to_city_hall(session, p, user, f"Pragul de {p.prag_voturi} susținători a fost atins.")
        notify(session, p.autor_id, p.idea_id, f"Proiectul „{_titlu(p)}” a strâns {p.voturi} susținători și a fost "
                                               "trimis automat către Primărie.", proiect_id=p.id)
    session.commit()
    session.refresh(p)
    return VotOut(proiect_id=p.id, voturi=p.voturi, prag_voturi=p.prag_voturi, stare=p.stare)


@router.post("/proiecte/{proiect_id}/trimite", response_model=ProiectOut, responses=ERRORS)
def trimite(proiect_id: str, body: TrimiteIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Direct send by the author (from draft, publicat or clarificari); the community path is publica + vot."""
    p = get_proiect_or_404(session, proiect_id)
    if p.autor_id != user.id:
        raise HTTPException(403, "Doar autorul proiectului îl poate trimite.")
    if p.stare not in ("draft", "publicat", "clarificari"):
        raise HTTPException(409, "Proiectul nu poate fi trimis din starea curentă.")
    _send_to_city_hall(session, p, user, body.mesaj)
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
    notify(session, p.autor_id, p.idea_id, f"Proiectul „{_titlu(p)}” a fost înaintat unui verificator.", proiect_id=p.id)
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
    voters = {v.user_id for v in session.exec(select(Vot).where(Vot.proiect_id == p.id)).all()}
    for target in {p.autor_id, *(u.id for u in users_with_role(session, "primarie")), *voters}:
        notify(session, target, p.idea_id, mesaj, proiect_id=p.id)
    session.commit()
    session.refresh(p)
    return p


DOCUMENTE = ("plan.svg", "plan.dxf", "plansa.pdf", "dosar.pdf", "materiale.xlsx", "materiale.csv")


def _visible_with_space(session: Session, proiect_id: str, user: User | None) -> tuple[Proiect, Space | None]:
    p = get_proiect_or_404(session, proiect_id)
    if not _can_see(user, p):
        raise HTTPException(403, "Nu ai acces la acest proiect.")
    return p, session.get(Space, p.space_id)


@router.get("/proiecte/{proiect_id}/plan", response_model=PlanOut, responses=ERRORS)
def proiect_plan(proiect_id: str, user: User | None = Depends(optional_user), session: Session = Depends(get_session)):
    p, space = _visible_with_space(session, proiect_id, user)
    return p3.plan_json(p, space)


@router.get("/proiecte/{proiect_id}/materiale", response_model=ListaMateriale, responses=ERRORS)
def proiect_materiale(proiect_id: str, user: User | None = Depends(optional_user), session: Session = Depends(get_session)):
    p, space = _visible_with_space(session, proiect_id, user)
    return p3.materiale_json(p, space)


@router.get(
    "/proiecte/{proiect_id}/documente/{nume}",
    responses={**ERRORS, 200: {"description": "fișierul (SVG, DXF, PDF, XLSX sau CSV)", "content": {
        "image/svg+xml": {}, "application/dxf": {}, "application/pdf": {},
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}, "text/csv": {}}}},
    response_class=Response,
)
def proiect_document(proiect_id: str, nume: str, user: User | None = Depends(optional_user),
                     session: Session = Depends(get_session)):
    if nume not in DOCUMENTE:
        raise HTTPException(404, "Documentul nu există. Variante: " + ", ".join(DOCUMENTE) + ".")
    p, space = _visible_with_space(session, proiect_id, user)
    content, media = p3.build_documente(p, space)[nume]
    return Response(content, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="proiect-{p.id}-{nume}"'})
