"""backend.ai.references.find_references(tip_amenajare, suprafata_mp, k=5) -> list[Referinta]."""
from backend.ai.config import get_settings
from backend.ai.references.core import (
    KNOWN_TYPES,
    Referinta,
    canonical_type,
    local_references,
    rank,
    slugify,
    type_label,
)

MIN_USABLE = 2  # below this many entries with cost and area, live search may top up the base


def live_search_enabled() -> bool:
    s = get_settings()
    return bool(s.references_live_search and s.gemini_api_key)


def find_references(tip_amenajare: str, suprafata_mp: float | None, k: int = 5) -> list[Referinta]:
    """Reference projects of the same type, closest in area first; [] when none are known.

    Any type works ("aquapark", "Foișor de lemn"...). With a Gemini key and live search on (the default;
    REFERENCES_LIVE_SEARCH=false turns it off) it searches the web when fewer than MIN_USABLE local
    entries have both cost and area, and caches the result.
    """
    tip = canonical_type(tip_amenajare)
    if not tip:
        return []
    refs = local_references(tip)
    if sum(r.usable_for_cost for r in refs) < MIN_USABLE and live_search_enabled():
        from backend.ai.references.search import search_references  # network layer, loaded on demand

        known = {r.id for r in refs}
        refs += [r for r in search_references(tip_amenajare) if r.id not in known]
    return rank(refs, suprafata_mp, k)


__all__ = ["KNOWN_TYPES", "MIN_USABLE", "Referinta", "canonical_type", "find_references", "local_references",
           "slugify", "type_label"]
