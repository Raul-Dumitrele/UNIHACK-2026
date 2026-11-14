"""Bridge to the team contract (docs/CONTRACT.md, types in backend/app/schemas.py, owned by P1).

P3 keeps a richer internal dossier (IdeaDossier); this module maps it to the contract's Structurat
(categorie, persoane, dotari, program, zgomot, rezumat) and writes owner_message. Deterministic.
"""
import re
from typing import Any

from backend.ai.fallback import normalize
from backend.ai.schemas import Category, IdeaDossier, Setting, _clip
from backend.app.schemas import Slot, Structurat

CATEGORY = {
    Category.atelier: "creativ", Category.sport: "sport", Category.cultura: "cultura",
    Category.educatie: "educatie", Category.comunitate: "social", Category.mediu: "social",
    Category.altele: "altele",
}
TECH = re.compile(r"\b(?:programar|robotic|tehnolog|calculator|coding|arduino|\bit\b|digital|scratch)")

# Internal amenity labels (backend.ai.fallback.NEEDS / seed) -> contract `dotari` vocabulary.
DOTARI = {
    "mese": "mese", "scaune": "scaune", "priză": "priza", "proiector": "proiector", "ecran": "proiector",
    "wi-fi": "wifi", "tablă": "tabla", "bucătărie": "bucatarie", "acces persoane cu dizabilități": "acces_rampa",
    "vestiar": "vestiare", "dușuri": "vestiare", "oglinzi": "oglinzi",
}
EXTRA_DOTARI = {r"\bscen": "scena", r"\bcurte\b|\bcurtea\b": "curte", r"\boglinz": "oglinzi", r"\bvestiar": "vestiare"}

LOUD = re.compile(r"\b(?:concert|petrecer|muzic|trupa|dans|fotbal|baschet|volei|karaoke|festival|dj|tobe|zumba)")
QUIET = re.compile(r"\b(?:lectur|carte|carti|curs|meditat|yoga|sah|seniori|linist|pictur|desen|studiu|invat|tricot)")

DAYS = [("luni", r"\bluni\b|\blunea\b"), ("marti", r"\bmarti\b|\bmartea\b"), ("miercuri", r"\bmiercur"),
        ("joi", r"\bjoi\b|\bjoia\b"), ("vineri", r"\bviner"), ("sambata", r"\bsamb"), ("duminica", r"\bdumin")]
DAY_LABEL = {"luni": "luni", "marti": "marți", "miercuri": "miercuri", "joi": "joi", "vineri": "vineri",
             "sambata": "sâmbătă", "duminica": "duminică"}
PART_OF_DAY = [(r"\bdiminea", 10), (r"\bdupa[- ]?amiaz|\bdupa[- ]?masa", 15), (r"\bseara\b|\bserile\b", 18)]
_RANGE = re.compile(r"\b(?:intre|de la|de la ora|orele|ora)?\s*(\d{1,2})(?:[:.](\d{2}))?\s*(?:-|–|si|pana la|la)\s*"
                    r"(\d{1,2})(?:[:.](\d{2}))?\b")
_AT = re.compile(r"\b(?:ora|orele|la)\s+(\d{1,2})(?:[:.](\d{2}))?\b")


def _hhmm(h: int, m: int = 0) -> str:
    return f"{min(max(h, 0), 23):02d}:{min(max(m, 0), 59):02d}"


def parse_program(text: str, duration_hours: float) -> list[Slot]:
    """Weekly slots stated in the text ("sâmbăta 10-14", "joi seara", "în weekend dimineața").
    No day in the text -> [] (nothing is invented)."""
    norm = normalize(text or "")
    days = [d for d, pattern in DAYS if re.search(pattern, norm)]
    if re.search(r"\bweekend", norm):
        days += [d for d in ("sambata", "duminica") if d not in days]
    if not days:
        return []
    start = end = None
    if m := _RANGE.search(norm):
        h1, m1, h2, m2 = int(m[1]), int(m[2] or 0), int(m[3]), int(m[4] or 0)
        if 0 <= h1 < h2 <= 23:
            start, end = (h1, m1), (h2, m2)
    if start is None and (m := _AT.search(norm)) and 6 <= int(m[1]) <= 22:
        start = (int(m[1]), int(m[2] or 0))
    if start is None:
        start = next(((h, 0) for pattern, h in PART_OF_DAY if re.search(pattern, norm)), (10, 0))
    if end is None:
        minutes = start[0] * 60 + start[1] + max(int(round(duration_hours * 60)), 30)
        end = divmod(min(minutes, 23 * 60 + 59), 60)
    return [Slot(zi=d, de_la=_hhmm(*start), pana_la=_hhmm(*end)) for d in days]


def _dotari(dossier: IdeaDossier, norm: str) -> list[str]:
    out: list[str] = []
    for need in dossier.needs:
        label = DOTARI.get(need)
        if label and label not in out:
            out.append(label)
    for pattern, label in EXTRA_DOTARI.items():
        if re.search(pattern, norm) and label not in out:
            out.append(label)
    if dossier.setting == Setting.exterior and "curte" not in out and re.search(r"\bcurt", norm):
        out.append("curte")
    return out


def _zgomot(dossier: IdeaDossier, norm: str) -> str:
    if LOUD.search(norm):
        return "ridicat"
    if QUIET.search(norm):
        return "scazut"
    return "mediu"


def to_structurat(dossier: IdeaDossier, text: str) -> Structurat:
    norm = normalize(text or "")
    categorie = "tehnologie" if TECH.search(norm) else CATEGORY[dossier.category]
    # The contract uses `rezumat` as the default title (max 80 characters): short and clean. Gemini's
    # summary when it fits, otherwise the dossier title (always <= 80).
    summary = " ".join(dossier.summary.split())
    rezumat = summary if dossier.source == "gemini" and len(summary) <= 80 else dossier.title
    return Structurat(
        categorie=categorie,
        persoane=dossier.expected_participants,
        dotari=_dotari(dossier, norm),
        program=parse_program(text, dossier.duration_hours),
        zgomot=_zgomot(dossier, norm),
        rezumat=rezumat or "Idee nouă",
    )


def _field(obj: Any, name: str, default: Any = None) -> Any:
    value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    return default if value in (None, "", [], {}) else value


def owner_message(idea: Any, space: Any, slot: Any) -> str:
    """Polite booking request to the space owner, in Romanian, from the idea, space and requested slot."""
    structurat = _field(idea, "structurat", {}) or {}
    if not isinstance(structurat, dict):
        structurat = structurat.model_dump()
    slot = slot if isinstance(slot, dict) else slot.model_dump()
    titlu = _field(idea, "titlu", "o activitate pentru vecini")
    interesati = _field(idea, "interesati", 0)
    persoane = structurat.get("persoane") or interesati
    rezumat = structurat.get("rezumat") or ""
    lines = ["Bună ziua!"]
    support = f", susținută de {interesati} vecini în aplicația Loc Comun" if interesati else " din aplicația Loc Comun"
    lines.append(f"Vă scriu în legătură cu ideea „{titlu}”{support}."
                 + (f" Pe scurt: {rezumat.rstrip('.')}." if rezumat and rezumat != titlu else ""))
    when = f"{DAY_LABEL.get(slot.get('zi'), slot.get('zi'))}, între {slot.get('de_la')} și {slot.get('pana_la')}"
    lines.append(f"Am dori să folosim {_field(space, 'nume', 'spațiul dumneavoastră')} {when}"
                 + (f", pentru aproximativ {persoane} persoane." if persoane else "."))
    dotari = [d.replace("_", " ") for d in structurat.get("dotari") or []]
    if dotari:
        lines.append("Ne-ar fi de folos: " + ", ".join(dotari) + ".")
    lines.append("Dacă intervalul nu vă convine, suntem deschiși la altă variantă. Vă mulțumim!")
    return "\n".join(lines)
