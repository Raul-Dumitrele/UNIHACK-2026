"""Stub for backend.impact (P3)."""
from backend.app.schemas import Impact


def compute_impact(session) -> Impact:
    return Impact(ore_recuperate=0, oameni_conectati=0, km_economisiti=0, proiecte_active=0)
