"""The technical specification of a proposal: the single source for the plan, the material list, the dossier
and the 3D view. Pydantic, strict on shape; every size is an assumption and says so."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Categorie = Literal["echipament", "instalatie", "constructie", "terasament", "finisaj", "mobilier", "siguranta",
                    "semnalizare", "vegetatie", "servicii"]
Unitate = Literal["buc", "mp", "ml", "set"]
Derivare = Literal["fix", "plan_rest", "plan_perimetru", "plan_alee", "plan_zona_libera", "plan_element"]

CATEGORII_RO: dict[str, str] = {
    "echipament": "Echipamente", "instalatie": "Instalații și utilități", "constructie": "Construcții",
    "terasament": "Terasamente și platforme", "finisaj": "Finisaje și suprafețe", "mobilier": "Mobilier urban",
    "siguranta": "Siguranță", "semnalizare": "Semnalizare", "vegetatie": "Spații verzi", "servicii": "Servicii și sisteme",
}


class Componenta(BaseModel):
    nume: str = Field(min_length=2, max_length=120)
    categorie: Categorie
    cantitate: float = Field(default=1, gt=0, le=100000)
    unitate: Unitate = "buc"
    latime_m: float | None = Field(default=None, gt=0, le=500)
    lungime_m: float | None = Field(default=None, gt=0, le=500)
    inaltime_m: float | None = Field(default=None, ge=0, le=60)
    min_latime_m: float | None = Field(default=None, gt=0, le=500)
    min_lungime_m: float | None = Field(default=None, gt=0, le=500)
    zona_libera_m: float = Field(default=0.5, ge=0, le=20)
    rol: str = Field(default="", max_length=300)
    obligatoriu: bool = False
    pe_plan: bool = True  # drawn on the plan when it has a footprint
    tip_desen: str = "zona"  # colour / hatch kind on drawings
    utilitati: list[str] = []
    articol: str | None = None  # key of a priced article (SEAP / plafon / catalog); None = no price source
    derivat_din: Derivare = "fix"  # how the quantity is obtained: fixed, or measured on the plan
    bucati_plan: int = Field(default=1, ge=1, le=200)  # footprints drawn when the unit is not buc/set

    @field_validator("nume", "rol")
    @classmethod
    def _tidy(cls, v: str) -> str:
        return " ".join(v.split())

    @property
    def are_amprenta(self) -> bool:
        return self.pe_plan and bool(self.latime_m and self.lungime_m)


class Specificatie(BaseModel):
    tip_amenajare: str
    eticheta: str
    suprafata_minima_mp: float = Field(gt=0)
    suprafata_recomandata_mp: float | None = Field(default=None, gt=0)
    utilitati_necesare: list[str] = []
    categorie_lucrare: list[str] = []  # tags used by acte.py (instalatie_electrica, instalatie_apa, constructie...)
    componente: list[Componenta] = Field(min_length=1)
    beneficii: list[str] = []
    riscuri_specifice: list[str] = []
    ipoteze: list[str] = []
    surse: list[str] = []
    sursa_specificatie: Literal["model_verificat", "llm", "generic"] = "model_verificat"
    disclaimer: str = ("Specificație orientativă: dimensiunile și cantitățile sunt ipoteze schematice ale aplicației, "
                       "nu valori din standarde sau fișe de produs. Proiectul tehnic le stabilește.")

    @property
    def obligatorii(self) -> list[Componenta]:
        return [c for c in self.componente if c.obligatoriu]

    def utilitati_toate(self) -> list[str]:
        seen = list(self.utilitati_necesare)
        for c in self.componente:
            for u in c.utilitati:
                if u not in seen:
                    seen.append(u)
        return seen
