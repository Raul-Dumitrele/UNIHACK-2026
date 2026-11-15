"""backend.ai.costs.estimate_cost(referinte, suprafata_mp, lista=None) -> Cost. Deterministic, no AI.

Two independent views, both always reported:
- the REFERENCE interval: cost per m² of each usable reference project (total / area) -> min, median, max,
  times the proposed area. Only references with both cost and area count; with fewer than MIN_REFERENCES the
  interval is "insufficient" and carries no figures;
- the ITEMISED sum: the priced lines of the material list (SEAP / programme ceiling / verified catalogue),
  with the explicit list of articles that have no price. The sum is partial by construction and is labelled so.
Nothing here invents a figure: every number traces back to a reference or to a priced line.
"""
from collections.abc import Iterable
from statistics import median
from typing import Any, Literal

from pydantic import BaseModel

from backend.ai.references import Referinta

MIN_REFERENCES = 2
ROUND_TO_LEI = 100


class Cost(BaseModel):
    suficient: bool  # the reference interval exists
    min_lei: int | None = None  # integer lei, as in the contract (backend/app/schemas.py)
    mediana_lei: int | None = None
    max_lei: int | None = None
    moneda: Literal["RON"] = "RON"
    ipoteze: list[str] = []
    referinte_folosite: list[str] = []
    motiv: str | None = None
    # Itemised view (always present once a material list exists)
    suma_cotata_lei: int | None = None
    articole_cotate: int = 0
    articole_necotate: list[str] = []
    pe_surse: dict[str, int] = {}  # tip_sursa -> number of priced lines
    eticheta_suma: str = ""
    metoda: str = ("Două estimări independente: intervalul din proiecte de referință (cost/mp × suprafață) și suma "
                   "articolelor cu preț din lista de materiale (parțială: articolele „de cotat” lipsesc).")


def _round(value: float) -> int:
    return int(round(value / ROUND_TO_LEI) * ROUND_TO_LEI)


def _projects(n: int) -> str:
    return "un proiect" if n == 1 else f"{n} proiecte"


def _itemised(cost: Cost, lista: Any) -> Cost:
    if lista is None:
        return cost
    linii = getattr(lista, "linii", None) or (lista.get("linii") if isinstance(lista, dict) else []) or []
    get = lambda l, k: l.get(k) if isinstance(l, dict) else getattr(l, k, None)  # noqa: E731
    priced = [l for l in linii if get(l, "valoare_lei") is not None]
    todo = [get(l, "nume") for l in linii if get(l, "valoare_lei") is None]
    pe_surse: dict[str, int] = {}
    for l in priced:
        p = get(l, "pret_unitar")
        tip = (p.get("tip_sursa") if isinstance(p, dict) else getattr(p, "tip_sursa", None)) or "seap"
        pe_surse[tip] = pe_surse.get(tip, 0) + 1
    cost.suma_cotata_lei = int(sum(get(l, "valoare_lei") for l in priced))
    cost.articole_cotate = len(priced)
    cost.articole_necotate = todo
    cost.pe_surse = pe_surse
    cost.eticheta_suma = (f"Suma articolelor cotate ({len(priced)} din {len(linii)}); "
                          f"{len(todo)} articole rămân de cotat" if todo else
                          f"Suma articolelor cotate ({len(priced)} din {len(linii)})")
    return cost


def estimate_cost(referinte: Iterable[Any], suprafata_mp: float | None, lista: Any = None) -> Cost:
    refs = [r if isinstance(r, Referinta) else Referinta.model_validate(r) for r in referinte]
    usable = [r for r in refs if r.usable_for_cost]
    if not suprafata_mp or suprafata_mp <= 0:
        return _itemised(Cost(suficient=False, motiv="Suprafața propusă lipsește, deci costul nu poate fi raportat la ea."),
                         lista)
    if len(usable) < MIN_REFERENCES:
        return _itemised(Cost(
            suficient=False,
            referinte_folosite=[r.id for r in usable],
            motiv=(f"Doar {_projects(len(usable))} de referință {'are' if len(usable) == 1 else 'au'} "
                   f"atât costul, cât și suprafața publicate; sunt necesare cel puțin {MIN_REFERENCES}."
                   if usable else "Niciun proiect de referință nu are atât costul, cât și suprafața publicate."),
        ), lista)

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
    return _itemised(Cost(
        suficient=True,
        min_lei=_round(per_mp[0] * suprafata_mp),
        mediana_lei=_round(median(per_mp) * suprafata_mp),
        max_lei=_round(per_mp[-1] * suprafata_mp),
        ipoteze=ipoteze,
        referinte_folosite=[r.id for r in usable],
    ), lista)
