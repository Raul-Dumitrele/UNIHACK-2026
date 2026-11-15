"""rezolva_pret(articol) -> PretUnitar | None: one unit price with its source, in this order of preference:

1. SEAP direct purchases (backend.ai.proiect.preturi: observed prices, median of >= MIN_OBS purchases);
2. official programme ceilings (data/plafoane.json): shown as a CEILING of a financing programme, never as a price,
   and only when the file ties a ceiling to an article;
3. catalogue prices from public shop pages (data/preturi_catalog.json): each row carries the page URL, the access
   date and whether the figure was re-read on the page by the offline fetch script; rows that are not verified
   are ignored.

No figure is ever invented here: an article without a row in any source stays "de cotat".
"""
import json
from functools import lru_cache
from pathlib import Path

from backend.ai.proiect.preturi import ARTICOLE, PretUnitar, pret_unitar

DATA = Path(__file__).resolve().parent / "data"
PLAFOANE_FILE = DATA / "plafoane.json"
CATALOG_FILE = DATA / "preturi_catalog.json"

# Articles the specifications use that SEAP does not cover (yet): name and unit, so lines stay consistent.
ARTICOLE_EXTRA: dict[str, tuple[str, str]] = {
    "statie_incarcare_ac": ("punct de încărcare AC 22 kW (dublu)", "buc"),
    "tablou_electric": ("tablou electric de distribuție cu protecții", "buc"),
    "bransament_electric": ("branșament electric (racord, prin operatorul de distribuție)", "set"),
    "cablu_electric": ("cablu de alimentare îngropat, cu tub de protecție", "ml"),
    "borna_protectie": ("bornă de protecție", "buc"),
    "stalp_iluminat": ("stâlp de iluminat LED", "buc"),
    "cismea": ("cișmea publică (fântână de băut apă)", "buc"),
    "bransament_apa": ("branșament la rețeaua de apă", "set"),
    "bransament_canal": ("racord la canalizare", "set"),
    "conducta_apa": ("conductă de apă îngropată", "ml"),
    "suprafata_skate": ("platformă din beton cu module de skate", "mp"),
    "suprafata_sport": ("suprafață sintetică pentru teren de sport", "mp"),
    "amenajare_caini": ("amenajare zonă pentru câini (gard, obstacole)", "mp"),
    "imbracaminte_pista": ("îmbrăcăminte asfaltică pentru pistă", "mp"),
    "strat_inaltat": ("strat înălțat din lemn, cu pământ", "buc"),
    "bazin": ("bazin din beton cu hidroizolație și finisaj", "mp"),
}


def nume_articol(articol: str | None) -> tuple[str, str] | None:
    if not articol:
        return None
    if articol in ARTICOLE:
        return ARTICOLE[articol].nume, ARTICOLE[articol].unitate
    return ARTICOLE_EXTRA.get(articol)


@lru_cache(maxsize=1)
def plafoane() -> list[dict]:
    if not PLAFOANE_FILE.exists():
        return []
    return json.loads(PLAFOANE_FILE.read_text(encoding="utf-8")).get("plafoane", [])


@lru_cache(maxsize=1)
def catalog() -> list[dict]:
    if not CATALOG_FILE.exists():
        return []
    rows = json.loads(CATALOG_FILE.read_text(encoding="utf-8")).get("preturi", [])
    return [r for r in rows if r.get("verificat") and r.get("sursa_url") and r.get("pret_lei")]


def plafoane_program(tip_amenajare: str | None = None) -> list[dict]:
    """Programme-level ceilings (per beneficiary, not per article), for display next to the cost."""
    out = []
    for p in plafoane():
        if p.get("nivel") == "program" and (tip_amenajare is None or tip_amenajare in p.get("tipuri", [])):
            out.append(p)
    return out


def rezolva_pret(articol: str | None) -> PretUnitar | None:
    if not articol:
        return None
    seap = pret_unitar(articol) if articol in ARTICOLE else None
    if seap:
        return seap
    info = nume_articol(articol)
    for p in plafoane():
        if p.get("nivel") == "articol" and p.get("articol") == articol and p.get("valoare_lei"):
            return PretUnitar(articol=articol, nume=info[0] if info else articol, unitate=p.get("unitate", "buc"),
                              mediana_lei=float(p["valoare_lei"]), min_lei=float(p["valoare_lei"]),
                              max_lei=float(p["valoare_lei"]), observatii=1, surse=[p.get("program", "")],
                              perioada=p.get("data_accesarii", ""), tip_sursa="plafon", sursa_url=p.get("sursa_url"),
                              data_accesarii=p.get("data_accesarii"),
                              nota=f"Plafon de finanțare al programului {p.get('program', '')}, nu preț de piață.")
    rows = [r for r in catalog() if r.get("articol") == articol]
    if rows:
        prices = sorted(float(r["pret_lei"]) for r in rows)
        mid = prices[len(prices) // 2]
        best = min(rows, key=lambda r: abs(float(r["pret_lei"]) - mid))
        return PretUnitar(articol=articol, nume=info[0] if info else best.get("nume", articol),
                          unitate=best.get("unitate", info[1] if info else "buc"), mediana_lei=mid, min_lei=prices[0],
                          max_lei=prices[-1], observatii=len(rows), surse=[r["sursa_url"] for r in rows[:5]],
                          perioada=best.get("data_accesarii", ""), tip_sursa="catalog", sursa_url=best["sursa_url"],
                          data_accesarii=best.get("data_accesarii"),
                          nota="Preț de catalog de pe o pagină comercială publică, nu standard; poate varia.")
    return None


def motiv_necotat(articol: str | None) -> str:
    if not articol:
        return "aplicația nu are o sursă de preț pentru acest articol"
    if articol in ARTICOLE:
        from backend.ai.proiect.preturi import MIN_OBS, observatii
        n = len(observatii(articol))
        return f"doar {n} observații în SEAP pentru acest articol (minimum {MIN_OBS}); fără plafon sau preț de catalog verificat"
    return "fără achiziții SEAP potrivite, fără plafon de program și fără preț de catalog verificat"
