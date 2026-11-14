"""Free plots from the city hall's Legea 15/2003 lists, as Spaces of type teren_liber.

Working hypothesis agreed by the team: plots on the list validated by the Local Council are treated as
land of the city hall. Every text says "din lista Primăriei, de confirmat" (they may have been allotted
since). Offline: reads backend/seed/data/terenuri_l15_<an>.json (extracted from the official annex, see
backend/seed/data/sursa/l15/manifest.json) and the Nominatim cache backend/seed/data/geocode_cache.json.

Rule: plots of at least MIN_AREA_MP with a resolved location, best MAX_PLOTS (largest first, then list
order); if fewer than MIN_PLOTS remain, none are added.
"""
import json
from pathlib import Path

from backend.ai.geo import nearest_neighborhood

DATA = Path(__file__).resolve().parent / "data"
LIST_FILES = ["terenuri_l15_2019.json"]  # newest edition first; HCL 25/2020 is scanned (no text)
GEOCODE_FILE = DATA / "geocode_cache.json"
MIN_AREA_MP = 250  # decided by the team (2026-11-14): the 2019 list has only 252 and 276 m² plots
MAX_PLOTS = 15
MIN_PLOTS = 5
CITY_HALL_OWNER = "demo-user-9"
SOURCE = "lista_primarie"
STREET_LABEL = {"str. Ovidiu Balea": "str. Lt. Ovidiu Balea"}


def _load(name: str) -> dict:
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def candidates() -> list[dict]:
    """Every listed plot, deduplicated on CF (the newest edition wins)."""
    seen: dict[str, dict] = {}
    for name in LIST_FILES:
        for row in _load(name).get("terenuri", []):
            seen.setdefault(row["cf"], row)
    return list(seen.values())


def select(rows: list[dict], streets: dict) -> list[dict]:
    kept = [r for r in rows if r["suprafata_mp"] >= MIN_AREA_MP and r["strada"] in streets]
    kept.sort(key=lambda r: (-r["suprafata_mp"], r["pozitie"]))
    kept = kept[:MAX_PLOTS]
    return kept if len(kept) >= MIN_PLOTS else []


def build_terenuri_lista() -> list[dict]:
    streets = _load(GEOCODE_FILE.name).get("streets", {})
    spaces = []
    for r in select(candidates(), streets):
        place = streets[r["strada"]]
        street = STREET_LABEL.get(r["strada"], r["strada"])
        details = r["sursa_detalii"] + ("" if place.get("precis") else "; locatie_aproximativa")
        spaces.append({
            "id": r["id"], "name": f"Teren din lista Primăriei (Legea 15/2003), {street}, CF {r['cf']}",
            "kind": "teren_liber", "kind_label": "teren liber", "lat": place["lat"], "lon": place["lon"],
            "address": f"{street}, Timișoara", "neighborhood": nearest_neighborhood((place["lat"], place["lon"])),
            "capacity": 0, "amenities": [], "setting": "exterior", "owner_id": CITY_HALL_OWNER,
            "suprafata_mp": r["suprafata_mp"], "source": SOURCE, "sursa_detalii": details, "is_demo": False,
        })
    return spaces
