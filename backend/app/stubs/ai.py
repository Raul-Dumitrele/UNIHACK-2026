"""Stub for backend.ai (P3). Deterministic, no network."""
from backend.app.schemas import Slot, Structurat


def structure_idea(text: str) -> Structurat:
    return Structurat(
        categorie="altele",
        persoane=10,
        dotari=[],
        program=[Slot(zi="sambata", de_la="10:00", pana_la="12:00")],
        zgomot="mediu",
        rezumat=text.strip()[:80],
    )


def owner_message(idea, space, slot) -> str:
    return f"Bună ziua! Aș dori să rezerv „{space.nume}” pentru: {idea.titlu}."
