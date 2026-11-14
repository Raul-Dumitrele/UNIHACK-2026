"""Reference projects (already built elsewhere in Romania) used to compare and cost a proposal.

Local base: backend/ai/references/data/<tip_amenajare>.json, collected by hand from pages that were
actually opened; fields missing from the source stay null. The live layer (search.py) adds entries
to cache/<tip>.json only when the local base is too thin and live search is enabled.
"""
import json
import logging
import math
import re
from collections.abc import Iterable
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from backend.ai.fallback import normalize

log = logging.getLogger(__name__)

PACKAGE = Path(__file__).resolve().parent
DATA_DIR = PACKAGE / "data"
CACHE_DIR = PACKAGE / "cache"
POPULATION_FILE = DATA_DIR / "_populatie.json"
REFERENCE_CITY = "Timișoara"  # tie-break: cities closest in size to the app's city come first

# Contract vocabulary; any other slug is accepted too (proposals can be about anything).
KNOWN_TYPES = ("skatepark", "loc_de_joaca", "parc_caini", "pista_biciclete", "gradina_comunitara", "teren_sport")
TYPE_LABELS = {
    "skatepark": "skatepark",
    "loc_de_joaca": "loc de joacă",
    "parc_caini": "parc pentru câini",
    "pista_biciclete": "pistă de biciclete",
    "gradina_comunitara": "grădină comunitară",
    "teren_sport": "teren de sport",
    "foisor": "foișor",
    "aquapark": "parc acvatic",
}
SOURCE_TYPES = {
    "achizitie_publica", "hotarare_consiliu", "comunicat_primarie", "date_deschise", "presa",
    "cautare_ai_verificata", "cautare_ai",
}
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def slugify(text: str) -> str:
    """'Foișor de lemn' -> 'foisor_de_lemn'."""
    return re.sub(r"[^a-z0-9]+", "_", normalize(text or "")).strip("_")


def type_label(tip: str) -> str:
    return TYPE_LABELS.get(tip, tip.replace("_", " "))


# Common wordings -> contract types (or a stable slug), matched on normalized text, so "parc pentru câini",
# "Loc de joacă pentru copii" or "aqua park" all reach the same reference file.
ALIASES: list[tuple[str, str]] = [  # first match wins: specific objects before generic words
    (r"aqua ?park|parc[ _]acvatic|parc cu apa|tobogan\w* (?:cu|de) apa", "aquapark"),
    (r"skate|pump ?track|\brole\b", "skatepark"),
    (r"loc(?:uri|ul)? de joaca|spatiu de joaca|tobogan|leagan", "loc_de_joaca"),
    (r"(?:parc|loc|spatiu|tarc)\w* (?:de joaca )?(?:pentru|de) (?:caini|catei)|dog ?park|parc_caini", "parc_caini"),
    (r"pist\w*[ _](?:de |pentru )?bici|bike ?lane", "pista_biciclete"),
    (r"gradin\w*[ _](?:comunitar|urban)", "gradina_comunitara"),
    (r"teren\w*[ _](?:de[ _])?(?:sport|fotbal|baschet|volei|tenis|multisport)|minifotbal", "teren_sport"),
    (r"foisor|pavilion", "foisor"),
]


def canonical_type(text: str) -> str:
    """Free text or slug -> type slug: known synonyms map to contract types, anything else is slugified."""
    norm = normalize(text or "")
    for pattern, tip in ALIASES:
        if re.search(pattern, norm):
            return tip
    return slugify(text)


def label_for(tip_amenajare: str) -> str:
    """Human label: free text ("parc acvatic", "Foișor de lemn") is kept as written, diacritics included;
    a slug ("loc_de_joaca") gets its Romanian label."""
    text = " ".join((tip_amenajare or "").split())
    if not text:
        return "amenajare"
    if slugify(text) != text:
        return text[:1].lower() + text[1:]
    return type_label(text)


class Referinta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tip_amenajare: str
    oras: str
    an: int
    suprafata_mp: float | None = None
    cost_total_lei: float | None = None
    componente: list[str] = []
    sursa_url: str
    sursa_tip: str
    data_accesarii: date

    @field_validator("tip_amenajare")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError(f"tip_amenajare invalid: {v!r} (doar litere mici, cifre și _)")
        return v

    @field_validator("an")
    @classmethod
    def _year(cls, v: int) -> int:
        if not 1990 <= v <= date.today().year + 1:
            raise ValueError(f"an în afara intervalului: {v}")
        return v

    @field_validator("suprafata_mp", "cost_total_lei")
    @classmethod
    def _positive(cls, v: float | None) -> float | None:
        if v is not None and not v > 0:
            raise ValueError("trebuie să fie pozitiv sau null")
        return v

    @field_validator("sursa_url")
    @classmethod
    def _url(cls, v: str) -> str:
        if not re.match(r"^https?://[^\s/]+\.[^\s/]+", v or ""):
            raise ValueError("sursa_url lipsește sau nu e un link http(s)")
        return v

    @field_validator("sursa_tip")
    @classmethod
    def _source(cls, v: str) -> str:
        if v not in SOURCE_TYPES:
            raise ValueError(f"sursa_tip necunoscut: {v!r}")
        return v

    @field_serializer("suprafata_mp", "cost_total_lei")
    def _as_int(self, v: float | None) -> int | None:
        """The contract (backend/app/schemas.py) has integer lei and m²; the base keeps source decimals."""
        return None if v is None else int(round(v))

    @property
    def usable_for_cost(self) -> bool:
        return bool(self.suprafata_mp and self.cost_total_lei)


def read_file(path: Path) -> tuple[list[Referinta], list[tuple[str, str]]]:
    """Valid entries and (id, reason) for every rejected one. File type must match each entry."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    expected = doc.get("tip_amenajare", path.stem)
    valid: list[Referinta] = []
    rejected: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in doc.get("referinte", []):
        rid = str(raw.get("id", "?"))
        try:
            ref = Referinta.model_validate(raw)
        except ValueError as exc:
            errors = getattr(exc, "errors", lambda: [])()
            reason = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in errors) or str(exc)
            rejected.append((rid, reason))
            continue
        if ref.tip_amenajare != expected:
            rejected.append((rid, f"tip_amenajare {ref.tip_amenajare!r} diferă de fișier ({expected!r})"))
        elif ref.id in seen:
            rejected.append((rid, "id duplicat"))
        else:
            seen.add(ref.id)
            valid.append(ref)
    return valid, rejected


def data_files() -> list[Path]:
    return sorted(p for p in DATA_DIR.glob("*.json") if not p.name.startswith("_"))


def local_references(tip: str, include_cache: bool = True) -> list[Referinta]:
    """Valid entries for one type: hand-collected base first, then cached live results (no network)."""
    paths = [DATA_DIR / f"{tip}.json"] + ([CACHE_DIR / f"{tip}.json"] if include_cache else [])
    refs: list[Referinta] = []
    for path in paths:
        if path.exists():
            valid, rejected = read_file(path)
            for rid, reason in rejected:
                log.warning("reference %s rejected: %s", rid, reason)
            refs += [r for r in valid if r.id not in {x.id for x in refs}]
    return refs


@lru_cache(maxsize=1)
def populations() -> dict[str, int]:
    return json.loads(POPULATION_FILE.read_text(encoding="utf-8"))["populatie"]


def rank(refs: Iterable[Any], suprafata_mp: float | None, k: int = 5) -> list[Referinta]:
    """Closest k by area (relative difference); ties: newer year, then city size closest to Timișoara."""
    pop = populations()
    home = pop[REFERENCE_CITY]

    def key(r: Referinta):
        if suprafata_mp and r.suprafata_mp:
            diff = round(abs(r.suprafata_mp - suprafata_mp) / max(r.suprafata_mp, suprafata_mp), 2)
        else:
            diff = 2.0  # unknown area: after every entry with an area
        city = pop.get(r.oras)
        return diff, -r.an, abs(city - home) if city else math.inf, r.id

    models = [r if isinstance(r, Referinta) else Referinta.model_validate(r) for r in refs]
    return sorted(models, key=key)[: max(k, 0)]
