from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from backend.app import p3
from backend.app.db import get_session
from backend.app.models import Space
from backend.app.schemas import LEGEA_15_AVERTISMENT, PlotCandidateOut

router = APIRouter(tags=["terenuri"])


@router.get("/terenuri/potrivite", response_model=list[PlotCandidateOut])
def terenuri_potrivite(
    tip_amenajare: str = Query(min_length=2, description="tipul amenajării (vocabularul tip_amenajare sau text liber)"),
    suprafata_minima: float | None = Query(default=None, ge=0),
    cartier: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    """Free plots (Space.tip = teren_liber) ranked for a proposal, best first, with a score and a reason."""
    plots = session.exec(select(Space).where(Space.tip == "teren_liber")).all()
    found = p3.find_plots(tip_amenajare, suprafata_minima, cartier=cartier, spaces=plots, limit=limit)
    return [
        PlotCandidateOut(**c.model_dump(), avertisment=LEGEA_15_AVERTISMENT if c.din_lista_primarie else None)
        for c in found
    ]
