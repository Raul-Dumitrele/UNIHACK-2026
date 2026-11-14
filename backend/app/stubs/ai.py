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


# --- Propunere catre Primarie (stubs; P3 livreaza backend.ai.references / costs / proiect) ---
from datetime import date  # noqa: E402

from backend.app.schemas import DISCLAIMER, Cost, Dosar, Etapa, Referinta  # noqa: E402


def find_references(tip_amenajare: str, suprafata_mp: int | None, k: int = 5) -> list[Referinta]:
    base = suprafata_mp or 1000
    return [
        Referinta(
            id=f"stub-ref-{i}", tip_amenajare=tip_amenajare, oras="Oras exemplu", an=2023,
            suprafata_mp=base + i * 100, cost_total_lei=(base + i * 100) * 800,
            componente=["suprafata", "iluminat"], sursa_url="https://example.com/referinta",
            sursa_tip="stub", data_accesarii=date.today(),
        )
        for i in (1, 2)
    ][:k]


def estimate_cost(referinte: list[Referinta], suprafata_mp: int) -> Cost:
    usable = [r for r in referinte if r.suprafata_mp and r.cost_total_lei]
    if len(usable) < 2:
        return Cost(suficient=False, motiv="Mai puțin de 2 referințe cu suprafață și cost.")
    per_mp = sorted(r.cost_total_lei / r.suprafata_mp for r in usable)
    mid = per_mp[len(per_mp) // 2]
    return Cost(
        suficient=True, min_lei=round(per_mp[0] * suprafata_mp), mediana_lei=round(mid * suprafata_mp),
        max_lei=round(per_mp[-1] * suprafata_mp), ipoteze=["Cost/mp al referințelor, scalat la suprafață."],
        referinte_folosite=[r.id for r in usable],
    )


def generate_dosar(idea, space, tip_amenajare: str, suprafata_mp: int, referinte, cost) -> Dosar:
    return Dosar(
        titlu=idea.titlu, descriere=idea.descriere,
        justificare=f"Propunere de {tip_amenajare} pe {suprafata_mp} mp la {space.nume}. {DISCLAIMER}",
        componente=["suprafata", "iluminat"], etape=[Etapa(nume="Proiectare", durata_luni=2)],
        riscuri=[], lista_verificare=["Verificare teren", "Avize"],
        referinte_citate=[r.id for r in referinte],
    )
