"""Deterministic dossier builder used when Gemini is missing, slow or wrong (a common case)."""
import re
import unicodedata

from backend.ai.schemas import Category, DossierBase, Setting

# Keywords are regex fragments matched at a word start on normalized text (lowercase, no diacritics).
CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.atelier: ("atelier", "repar", "croitor", "tricot", "olarit", "lucru manual", "diy", "mester", "bricolaj", "gatit"),
    Category.sport: ("sport", "fotbal", "baschet", "volei", "alerga", "yoga", "fitness", "tenis", "sah", "dans", "biciclet", "ciclism", "miscare"),
    Category.cultura: ("concert", "teatru", "film", "cinema", "expozit", "lectur", "carte", "poezie", "muzic", "arta", "pictur", "fotograf"),
    Category.educatie: ("curs", "meditat", "invat", "lecti", "programare", "limba", "engleza", "matematic", "seminar", "prezentare", "workshop", "robotic", "stiint"),
    Category.mediu: ("mediu", "plant", "gradin", "reciclar", "compost", "curatenie", "ecolog", "copaci", "deseuri"),
    # Most generic category last: dict order breaks ties, so specific topics win over "comunitate".
    Category.comunitate: ("vecin", "cartier", "comunitat", "intalnire", "voluntar", "schimb", "targ", "petrecere", "seniori", "varstnic", "socializ"),
}

DEFAULT_PARTICIPANTS = {
    Category.atelier: 12, Category.sport: 16, Category.cultura: 30, Category.educatie: 15,
    Category.comunitate: 25, Category.mediu: 20, Category.altele: 15,
}

NEEDS: dict[str, str] = {
    "(?:video)?proiector": "proiector", r"ecran\b": "ecran",
    r"(?:mese|masa|masute)\b": "mese", "scaun": "scaune", "priz": "priză", r"curent\b": "priză",
    "wi-?fi": "wi-fi", "internet": "wi-fi",
    "bucatari": "bucătărie", "chiuvet": "apă curentă", r"apa curenta\b": "apă curentă",
    r"box(?:e|ele)\b": "sonorizare", "sonorizar": "sonorizare", "microfon": "sonorizare",
    r"tabl(?:a|ă)\b": "tablă", "flipchart": "tablă", "parcar": "parcare",
    "rampa": "acces persoane cu dizabilități", "dizabilit": "acces persoane cu dizabilități",
    "vestiar": "vestiar", "dusuri": "dușuri", "oglinz": "oglinzi", "saltel": "saltele",
}

AUDIENCES: list[tuple[str, str]] = [
    ("copii", "copii"), ("adolescent", "adolescenți"), ("tiner", "tineri"), ("student", "studenți"),
    ("parint", "părinți"), ("familii", "familii"), ("seniori", "seniori"), ("varstnic", "seniori"),
    ("pensionar", "seniori"), ("vecin", "vecinii din cartier"),
]

OUTDOOR = (r"parc(?:ul|uri)?\b", "aer liber", "afara", "exterior", "curte", "gradin", r"teren\b", "strad",
           r"mal(?:ul)?\b", "padur", "plaj")
INDOOR = (r"sal(?:a|i|ii)\b", "interior", "inauntru", "bibliotec", r"clas(?:a|e)\b", "bucatari")

PEOPLE = (r"(?:de\s+)?(?:oameni|persoane|participanti|copii|vecini|locuri|invitati|elevi|studenti|seniori|membri"
          r"|jucatori|voluntari|adulti|tineri|cursanti|spectatori|doritori|familii)")
_PARTICIPANTS_RE = re.compile(r"\b(\d{1,3})\s*(?:-\s*\d{1,3}\s*)?" + PEOPLE + r"\b")
_DURATION_RE = re.compile(r"\b(\d{1,2}(?:[.,]\d)?)\s*(?:de\s+)?(?:ore|ora|h)\b")
_FILLER_RE = re.compile(
    r"^(?:(?:eu\s+|noi\s+)?(?:vreau|vrem|as\s+vrea|am\s+vrea|propun|propunem|ne\s+gandim)\s+"
    r"(?:sa\s+)?(?:organizez|organizam|facem|fac|pornesc|pornim|deschid|deschidem|incep|incepem)?\s*)",
)


def normalize(text: str) -> str:
    text = text.replace("ş", "ș").replace("ţ", "ț").replace("Ş", "Ș").replace("Ţ", "Ț")
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _has(norm: str, pattern: str) -> bool:
    return re.search(r"\b" + pattern, norm) is not None


def _category(norm: str) -> tuple[Category, list[str]]:
    """Winning category plus every matched keyword (whole words), winner's first."""
    best, best_hits, all_hits = Category.altele, [], []
    for category, stems in CATEGORY_KEYWORDS.items():  # dict order breaks ties
        found = (re.search(r"\b" + s + r"[\w-]*", norm) for s in stems)
        hits = [m.group() for m in found if m]
        all_hits += hits
        if len(hits) > len(best_hits):
            best, best_hits = category, hits
    return best, list(dict.fromkeys(best_hits + all_hits))


def _first_sentence(text: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s+|\n", text.strip(), maxsplit=1)[0].rstrip(".!? ")
    if len(sentence) > 60:  # long sentence: keep the first clause
        comma = sentence.find(",", 15)
        if comma != -1:
            sentence = sentence[:comma]
    return sentence


def _title(text: str) -> str:
    sentence = _first_sentence(text)
    # Strip "Vreau să organizez ..." style openers; the filler regex runs on normalized text,
    # which has the same length as the original for Romanian letters, so offsets line up.
    norm = normalize(sentence)
    match = _FILLER_RE.match(norm) if len(norm) == len(sentence) else None
    if match and match.end() < len(sentence):
        sentence = sentence[match.end():]
    sentence = re.sub(r"^(?:un|o|niste|niște)\s+", "", sentence, flags=re.IGNORECASE).strip()
    return (sentence[:1].upper() + sentence[1:]) or "Idee nouă"


def build_fallback(text: str) -> DossierBase:
    text = (text or "").strip()
    norm = normalize(text)
    category, hits = _category(norm)

    m = _PARTICIPANTS_RE.search(norm)
    participants = int(m.group(1)) if m else DEFAULT_PARTICIPANTS[category]
    d = _DURATION_RE.search(norm)
    duration = float(d.group(1).replace(",", ".")) if d else 2.0

    needs = list(dict.fromkeys(label for stem, label in NEEDS.items() if _has(norm, stem)))
    audience = next((label for stem, label in AUDIENCES if _has(norm, stem)), "comunitatea locală")
    if any(_has(norm, s) for s in OUTDOOR):
        setting = Setting.exterior
    elif any(_has(norm, s) for s in INDOOR):
        setting = Setting.interior
    else:
        setting = Setting.oricare

    return DossierBase(
        title=_title(text) if text else "Idee nouă",
        summary=text or "Descriere în curs de completare.",
        category=category,
        audience=audience,
        expected_participants=participants,
        duration_hours=duration,
        needs=needs,
        setting=setting,
        tags=[category.value, *hits][:5],
    )
