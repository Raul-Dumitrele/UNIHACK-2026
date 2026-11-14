"""backend.ai.costs.estimate_cost(referinte, suprafata_mp) -> Cost. Deterministic, no AI.

Cost per m² of each usable reference (total cost / its area) -> min, median, max, times the
proposed area. Only references with both cost and area count; with fewer than MIN_REFERENCES
the answer is "insufficient" and carries no figures at all.
"""
from collections.abc import Iterable
from statistics import median
from typing import Any, Literal

from pydantic import BaseModel

from backend.ai.references import Referinta

MIN_REFERENCES = 2
ROUND_TO_LEI = 100


class Cost(BaseModel):
    suficient: bool
    min_lei: float | None = None
    mediana_lei: float | None = None
    max_lei: float | None = None
    moneda: Literal["RON"] = "RON"
    ipoteze: list[str] = []
    referinte_folosite: list[str] = []
    motiv: str | None = None


def _round(value: float) -> float:
    return float(round(value / ROUND_TO_LEI) * ROUND_TO_LEI)


def _projects(n: int) -> str:
    return "un proiect" if n == 1 else f"{n} proiecte"


def estimate_cost(referinte: Iterable[Any], suprafata_mp: float | None) -> Cost:
    refs = [r if isinstance(r, Referinta) else Referinta.model_validate(r) for r in referinte]
    usable = [r for r in refs if r.usable_for_cost]
    if not suprafata_mp or suprafata_mp <= 0:
        return Cost(suficient=False, motiv="Suprafața propusă lipsește, deci costul nu poate fi raportat la ea.")
    if len(usable) < MIN_REFERENCES:
        return Cost(
            suficient=False,
            referinte_folosite=[r.id for r in usable],
            motiv=(f"Doar {_projects(len(usable))} de referință {'are' if len(usable) == 1 else 'au'} "
                   f"atât costul, cât și suprafața publicate; sunt necesare cel puțin {MIN_REFERENCES}."
                   if usable else "Niciun proiect de referință nu are atât costul, cât și suprafața publicate."),
        )

    per_mp = sorted(r.cost_total_lei / r.suprafata_mp for r in usable)
    years = sorted(r.an for r in usable)
    cities = ", ".join(dict.fromkeys(r.oras for r in usable))
    period = f"anul {years[0]}" if years[0] == years[-1] else f"anii {years[0]}–{years[-1]}"
    ipoteze = [
        f"Bazat pe {_projects(len(usable))} de referință din {period} ({cities}).",
        "Cost pe mp = valoarea totală a proiectului de referință împărțită la suprafața lui, "
        f"înmulțit cu suprafața propusă ({suprafata_mp:g} mp).",
        "Prețuri nominale, fără actualizare la inflație.",
        "TVA inclus sau nu, așa cum apare în sursă (deseori nu e precizat).",
        "Multe valori sunt estimări din licitații sau bugete aprobate, nu costuri finale.",
        "Proiectele de referință pot include lucrări care nu sunt cerute aici, și invers.",
    ]
    live = sum(r.sursa_tip == "cautare_ai_verificata" for r in usable)
    if live:
        ipoteze.append(f"{_projects(live)} {'a fost găsit' if live == 1 else 'au fost găsite'} prin căutare automată; "
                       "suma și suprafața au fost regăsite automat în pagina sursei.")
    return Cost(
        suficient=True,
        min_lei=_round(per_mp[0] * suprafata_mp),
        mediana_lei=_round(median(per_mp) * suprafata_mp),
        max_lei=_round(per_mp[-1] * suprafata_mp),
        ipoteze=ipoteze,
        referinte_folosite=[r.id for r in usable],
    )
