"""Idea dossier schema (proposal for docs/CONTRACT.md; P1 owns the contract)."""
from enum import Enum
from typing import Literal

from pydantic import BaseModel, field_validator


class Category(str, Enum):
    atelier = "atelier"
    sport = "sport"
    cultura = "cultura"
    educatie = "educatie"
    comunitate = "comunitate"
    mediu = "mediu"
    altele = "altele"


class Setting(str, Enum):
    interior = "interior"
    exterior = "exterior"
    oricare = "oricare"


def _clip(value: str, limit: int) -> str:
    value = " ".join(str(value).split())
    if len(value) <= limit:
        return value
    cut = value[: limit - 1].rsplit(" ", 1)[0] or value[: limit - 1]  # room for the ellipsis
    return cut.rstrip(" ,.;:") + "…"


class DossierBase(BaseModel):
    """Fields Gemini fills. Plain types only (no JSON-schema constraints Gemini may reject);
    validators clamp values instead of failing."""

    title: str
    summary: str
    category: Category
    audience: str
    expected_participants: int
    duration_hours: float
    needs: list[str]
    setting: Setting
    tags: list[str]

    @field_validator("title")
    @classmethod
    def _title(cls, v: str) -> str:
        v = _clip(v, 80)
        if not v:
            raise ValueError("empty title")
        return v

    @field_validator("summary")
    @classmethod
    def _summary(cls, v: str) -> str:
        return _clip(v, 400)

    @field_validator("audience")
    @classmethod
    def _audience(cls, v: str) -> str:
        return _clip(v, 80) or "comunitatea locală"

    @field_validator("expected_participants")
    @classmethod
    def _participants(cls, v: int) -> int:
        return min(max(v, 1), 500)

    @field_validator("duration_hours")
    @classmethod
    def _duration(cls, v: float) -> float:
        return round(min(max(v, 0.5), 12.0), 1)

    @field_validator("needs", "tags")
    @classmethod
    def _short_list(cls, v: list[str]) -> list[str]:
        seen: list[str] = []
        for item in v:
            item = _clip(item, 40).lower()
            if item and item not in seen:
                seen.append(item)
        return seen[:10]


class IdeaDossier(DossierBase):
    """Return type of backend.ai.structure_idea."""

    source: Literal["gemini", "fallback"]
