"""Single import point for P3 functions: real modules win, stubs are the fallback.

P3's real signatures can differ from docs/CONTRACT.md (e.g. structure_idea returned an English
IdeaDossier, compute_impact took bookings). The adapters below keep the API stable either way.
"""
import inspect

from pydantic import BaseModel

from backend.app.schemas import Impact, Structurat
from backend.app.services.impact import compute_local

try:
    from backend.ai import structure_idea as _real_structure
except ImportError:
    _real_structure = None
try:
    from backend.ai import owner_message
except ImportError:
    from backend.app.stubs.ai import owner_message
try:
    from backend.impact import compute_impact as _real_impact
except ImportError:
    _real_impact = None
try:
    from backend.ai.references import find_references
except ImportError:
    from backend.app.stubs.ai import find_references
try:
    from backend.ai.costs import estimate_cost
except ImportError:
    from backend.app.stubs.ai import estimate_cost
try:
    from backend.ai.proiect import generate_dosar
except ImportError:
    from backend.app.stubs.ai import generate_dosar

from backend.ai.proiect import find_plots  # noqa: E402
from backend.ai.proiect.documente import build_documente, materiale_json, plan_json  # noqa: E402

_CATEGORY_MAP = {"atelier": "creativ", "comunitate": "social", "mediu": "altele"}
_DOTARI = ("scaune", "mese", "proiector", "wifi", "scena", "oglinzi", "vestiare", "bucatarie", "curte", "priza", "tabla")


def _to_structurat(result, text: str) -> Structurat:
    if isinstance(result, Structurat):
        return result
    data = result.model_dump() if isinstance(result, BaseModel) else dict(result)
    if "categorie" in data:
        return Structurat(**{k: data[k] for k in Structurat.model_fields if k in data})
    # P3 IdeaDossier (English fields) -> contract Structurat
    needs = " ".join(data.get("needs", [])).lower()
    cat = getattr(data.get("category"), "value", data.get("category"))
    cat = _CATEGORY_MAP.get(cat, cat)
    return Structurat(
        categorie=cat if cat in Structurat.model_fields["categorie"].annotation.__args__ else "altele",
        persoane=int(data.get("expected_participants") or 1),
        dotari=[d for d in _DOTARI if d in needs],
        program=[],
        zgomot="mediu",
        rezumat=(data.get("title") or text.strip())[:80],
    )


def structure_idea(text: str) -> Structurat:
    if _real_structure is None:
        from backend.app.stubs.ai import structure_idea as stub
        return stub(text)
    return _to_structurat(_real_structure(text), text)


def compute_impact(session) -> Impact:
    """Use P3's function when it takes a Session and returns the contract Impact; else compute locally."""
    if _real_impact is not None and "session" in inspect.signature(_real_impact).parameters:
        result = _real_impact(session)
        if isinstance(result, Impact):
            return result
        if isinstance(result, BaseModel):
            return Impact(**{k: v for k, v in result.model_dump().items() if k in Impact.model_fields})
    return compute_local(session)


__all__ = ["structure_idea", "owner_message", "compute_impact", "find_references", "estimate_cost", "generate_dosar", "find_plots", "plan_json", "materiale_json", "build_documente"]
