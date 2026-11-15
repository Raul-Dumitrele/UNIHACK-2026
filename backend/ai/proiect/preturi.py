"""Unit prices observed in SEAP direct purchases (open data, data.gov.ro, CC BY 4.0, Autoritatea pentru
Digitalizarea României). Deterministic, offline: reads backend/ai/proiect/data/preturi_seap.json, written once
by `python -m backend.seed.fetch_preturi` (network) with the extraction rules below.

The datasets give, per purchase, one free-text name, a CPV code and the awarded value: no quantity column.
A purchase becomes an observation ONLY when its name states one explicit quantity in the article's unit
("Achizitie 30 buc. Banci pentru parc", "MONTAJ PAVELE BETON 100 mp") and matches exactly one article.
Packs, sets, lots, repairs and anything mentioning a second article are dropped. An article gets a price only
with at least MIN_OBS observations; otherwise it stays "de cotat". These are prices paid by public buyers,
not a cost standard; VAT treatment is not stated in the dataset.
"""
import json
import re
import statistics
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

DATA_FILE = Path(__file__).resolve().parent / "data" / "preturi_seap.json"
MIN_OBS = 3  # fixed before looking at the results; not to be lowered to get more prices
MAX_SURSE = 5
SURSA = ("Achiziții directe din SEAP, date deschise publicate de Autoritatea pentru Digitalizarea României pe "
         "data.gov.ro (CC BY 4.0)")
TVA = "TVA: neprecizat în setul de date"


@dataclass(frozen=True)
class Articol:
    nume: str
    unitate: str  # buc | mp | ml
    include: str  # regex on normalized text (lowercase, no diacritics)
    exclude: str = ""
    cpv: tuple[str, ...] = ()  # allowed CPV prefixes (digits only); empty = any


ARTICOLE: dict[str, Articol] = {
    "banca": Articol("bancă de parc", "buc", r"\bbanc(a|i|ute)\b",
                     r"pergol|\bmas(a|i)\b|foisor|\bcos|scaun|bancar|de lucru|laborator|vestiar|gimnast|\bsala\b",
                     ("39113", "349284", "3911")),
    "cos_gunoi_stradal": Articol("coș de gunoi stradal", "buc",
                                 r"\bcos(uri)?\b.*\b(gunoi|deseuri)\b.*\b(stradal\w*|exterior|parc|stalp|urban)\b"
                                 r"|\bcos(uri)?\b.*\b(stradal\w*|exterior|urban)\b.*\b(gunoi|deseuri)\b",
                                 r"pubel|container|\d+\s*l\b|\bsac|birou|pedala|scrumier|interior",
                                 ("349284", "39224", "3983")),
    "leagan": Articol("leagăn", "buc", r"\bleagan(e)?\b",
                      r"tobogan|balansoar|complex|ansamblu|carusel|lant|sezut|scaun", ("37535",)),
    "balansoar": Articol("balansoar", "buc", r"\bbalansoar(e)?\b", r"leagan|tobogan|complex|ansamblu",
                         ("37535",)),
    "tobogan": Articol("tobogan", "buc", r"\btobogan(e)?\b",
                       r"leagan|balansoar|complex|ansamblu|structura|turn|\bapa\b|aqua", ("37535",)),
    "complex_joaca": Articol("structură de joacă (complex)", "buc",
                             r"(complex|ansamblu|structura)\w* (multifunctional\w* )?(de|pentru) joaca", "",
                             ("37535",)),
    "rastel_biciclete": Articol("rastel pentru biciclete", "buc",
                                r"\brastel\w*\b.*\bbici|\bsuport\w* (de |pentru )?bici"),
    "foisor": Articol("foișor", "buc", r"\bfoisor\w*\b", r"acoperis|proiect|pergol|paza|container"),
    "masa_picnic": Articol("masă de picnic cu bănci", "buc",
                           r"\bmas(a|i) (de )?picnic|\bmas(a|i) cu banc", r"pergol|foisor"),
    "compostor": Articol("compostor", "buc", r"\bcompostor\w*\b|\blad(a|e) (de |pentru )?compost"),
    "pardoseala_cauciuc": Articol("pardoseală sintetică (cauciuc / tartan)", "mp",
                                  r"(dale|covor|pardoseal\w*|suprafat\w*|tartan)\b.*\b(cauciuc|tartan|granule)"
                                  r"|\btartan\b",
                                  r"electroizol|\bauto\b|antiderap|intrare|birou|\busa\b|covoras|\bsala\b|scar|"
                                  r"insertie"),  # industrial rubber matting, not a play surface
    "pavaj": Articol("pavaj din pavele (furnizare și/sau montaj)", "mp", r"\bpavele\b|\bpavaj\w*\b",
                     r"decolmat|curatar|bordur"),
    "gazon_rulou": Articol("gazon în rulou", "mp", r"\bgazon\w*\b.*\brulou|\brulou\w*\b.*\bgazon",
                           r"\btuns|cosit|ingras|semint|saman|artificial"),
    "gard": Articol("împrejmuire (gard)", "ml", r"\bgard(ul|uri|urile|ului)?\b|\bimprejmuir\w*\b",
                    r"\bmobil\w*\b|santier|demol|dezafect|vopsi|\bband(a|e)\b|avertiz|sarma|soclu|tehnic|"
                    r"^(plas(a|e)|panou\w*|stalp\w*)\b",
                    ("45", "44", "34928")),  # works, construction products or fences (not "Gardlox ... 30ML")
}
# Several real names had to be read by hand before these rules were final; see test_preturi.py.

# Anything that hides the real quantity or is not a purchase of the article itself: packs, sets, lots,
# repairs, services, or a second item/work in the same purchase ("+ remodelare teren").
GLOBAL_EXCLUDE = re.compile(r"\b(pachet\w*|set|seturi|lot|loturi|kit|reparat\w*|rep|intretinere|piese|piesa|"
                            r"schimb|inlocuire|reconditionare|reabilitare|refacere|proiectare|documentati\w*|"
                            r"servicii|inchiriere|plus)\b|\s\+\s?|\+\s"
                            r"|\b(rola|rulou) (de )?\d"  # size of one roll, not the quantity bought
                            r"|\b\w+ de lemn \d+ buc")  # "rigla de lemn 8 bucati": count of parts, not of benches
MAX_NUMBERS = 6  # more numbers than this = an invoice pasted into the name (several items and prices)
UNIT = {"buc": "buc", "bucata": "buc", "bucati": "buc", "bc": "buc",
        "mp": "mp", "m2": "mp", "m²": "mp", "ml": "ml"}
_NUM = r"\d{1,3}(?:\.\d{3})+|\d+(?:,\d{1,2})?"
QTY_AFTER = re.compile(rf"(?<![\d.,x*])({_NUM})\s*(buc(?:ata|ati)?|bc|mp|m2|m²|ml)(?![a-z0-9])(?!\s*/)")  # not "9,6 mp/pal"
QTY_BEFORE = re.compile(rf"\b(buc(?:ata|ati)?)\.?\s*[:=]?\s*({_NUM})(?![\d.,])")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def _number(raw: str) -> float:
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):  # 1.250 = one thousand two hundred fifty
        return float(raw.replace(".", ""))
    return float(raw.replace(",", "."))


def quantities(text: str) -> list[tuple[float, str]]:
    found = [(_number(n), UNIT[u]) for n, u in QTY_AFTER.findall(text)]
    found += [(_number(n), UNIT[u]) for u, n in QTY_BEFORE.findall(text)]
    return found


def _cpv_digits(cpv: str) -> str:
    return re.sub(r"\D", "", cpv or "")


def classify(denumire: str, cpv: str = "") -> str | None:
    """The single article a purchase name is about, or None (no article, several, or excluded)."""
    text = normalize(denumire)
    if GLOBAL_EXCLUDE.search(text) or len(re.findall(r"\d+(?:[.,]\d+)?", text)) > MAX_NUMBERS:
        return None
    hits = [k for k, a in ARTICOLE.items() if re.search(a.include, text)]
    if len(hits) != 1:
        return None
    art = ARTICOLE[hits[0]]
    if art.exclude and re.search(art.exclude, text):
        return None
    if art.cpv and not _cpv_digits(cpv).startswith(art.cpv):
        return None
    return hits[0]


def extract(denumire: str, cpv: str, valoare_ron: float | None) -> dict | None:
    """{articol, cantitate, unitate, pret_unitar_ron} when the name states exactly one quantity in the
    article's unit; None otherwise."""
    if not valoare_ron or valoare_ron <= 0:
        return None
    key = classify(denumire, cpv)
    if key is None:
        return None
    text = normalize(denumire)
    qty = quantities(text)
    # One quantity only, and no other "buc"/"/unit" left over: a list of items or a per-pallet size.
    if len(qty) != 1 or len(re.findall(r"\bbuc", text)) > 1 or re.search(r"\b(mp|ml|buc)\s*/", text):
        return None
    n, unit = qty[0]
    if unit != ARTICOLE[key].unitate or n <= 0:
        return None
    return {"articol": key, "cantitate": n, "unitate": unit, "pret_unitar_ron": round(valoare_ron / n, 2)}


class PretUnitar(BaseModel):
    articol: str
    nume: str
    unitate: str
    mediana_lei: float
    min_lei: float
    max_lei: float
    observatii: int
    surse: list[str]  # DA numbers closest to the median (SEAP) or page URLs (catalog)
    perioada: str  # "2023-10-02 – 2026-09-30"
    tip_sursa: str = "seap"  # seap | plafon | catalog
    sursa_url: str | None = None
    data_accesarii: str | None = None
    nota: str | None = None


@lru_cache(maxsize=1)
def _load() -> dict:
    if not DATA_FILE.exists():
        return {"observatii": []}
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def observatii(articol: str | None = None) -> list[dict]:
    rows = _load().get("observatii", [])
    return [r for r in rows if articol is None or r["articol"] == articol]


def pret_unitar(articol: str) -> PretUnitar | None:
    """Median of the observed unit prices; None (de cotat) below MIN_OBS observations."""
    rows = observatii(articol)
    if len(rows) < MIN_OBS or articol not in ARTICOLE:
        return None
    prices = sorted(r["pret_unitar_ron"] for r in rows)
    med = statistics.median(prices)
    closest = sorted(rows, key=lambda r: (abs(r["pret_unitar_ron"] - med), r["numar_da"]))[:MAX_SURSE]
    dates = sorted(r["data"] for r in rows if r.get("data"))
    art = ARTICOLE[articol]
    return PretUnitar(articol=articol, nume=art.nume, unitate=art.unitate, mediana_lei=round(med, 2),
                      min_lei=prices[0], max_lei=prices[-1], observatii=len(rows),
                      surse=[r["numar_da"] for r in closest],
                      perioada=f"{dates[0]} – {dates[-1]}" if dates else "")
