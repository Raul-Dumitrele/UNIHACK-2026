"""Detect amounts of money in Romanian text, so AI-written prose never carries invented costs."""
import re

from backend.ai.fallback import normalize

# Amounts in normalized text (lowercase, no diacritics): "250.000 lei", "1,2 milioane euro", "RON 5000",
# "€300", "3 mii de lei". Areas ("400 mp"), durations ("3 luni") and counts are allowed.
_AMOUNT = r"\d[\d.,\s]*"
_SCALE = r"(?:(?:mii|mil(?:ioane|ion)?\.?|mld\.?|miliarde?)\s*(?:de\s+)?)?"
MONEY_RE = re.compile(
    rf"{_AMOUNT}\s*{_SCALE}(?:lei|ron|euro|eur|€|usd|dolari|\$)(?![a-z])|(?:\blei|\bron|\beur|\beuro|€|\$)\s*\d"
)


def money_mentions(text: str) -> list[str]:
    return [m.group().strip() for m in MONEY_RE.finditer(normalize(text or ""))]


def without_money(text: str) -> str:
    """Drop sentences that mention an amount of money."""
    sentences = re.split(r"(?<=[.!?])\s+", text or "")
    return " ".join(s for s in sentences if not money_mentions(s)).strip()
