"""Distances and Timișoara districts (centres from OSM, backend/seed/data/neighborhoods.json)."""
import json
import math
from functools import lru_cache
from pathlib import Path

from backend.ai.fallback import normalize

NEIGHBORHOODS_FILE = Path(__file__).resolve().parents[1] / "seed" / "data" / "neighborhoods.json"
CITY_CENTRE = "Cetate"
EARTH_RADIUS_KM = 6371.0

Point = tuple[float, float]  # (lat, lon)


def distance_km(a: Point, b: Point) -> float:
    """Great-circle (haversine) distance."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


@lru_cache(maxsize=1)
def neighborhoods() -> dict[str, Point]:
    doc = json.loads(NEIGHBORHOODS_FILE.read_text(encoding="utf-8"))
    return {n["name"]: (n["lat"], n["lon"]) for n in doc["neighborhoods"]}


def neighborhood_point(name: str | None) -> Point | None:
    """Centre of a district by name; tolerant to case and missing diacritics."""
    if not name:
        return None
    wanted = normalize(name).strip()
    for candidate, point in neighborhoods().items():
        if normalize(candidate) == wanted:
            return point
    return None


def nearest_neighborhood(point: Point) -> str:
    return min(neighborhoods().items(), key=lambda kv: (distance_km(point, kv[1]), kv[0]))[0]


def city_centre() -> Point:
    return neighborhoods()[CITY_CENTRE]
