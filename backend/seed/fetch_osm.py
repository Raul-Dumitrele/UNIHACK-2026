"""One-time fetch of candidate community spaces in Timișoara from OpenStreetMap (Overpass).

Run once, commit the JSON; seeding (run.py) is offline and never calls the network.
    python -m backend.seed.fetch_osm
Data © OpenStreetMap contributors, ODbL 1.0 (see docs/DATA.md).
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from backend.ai.fallback import normalize as normalize_text

OUT = Path(__file__).resolve().parent / "data" / "osm_spaces.json"
OVERPASS_URLS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")
USER_AGENT = "LocComun-seed/0.1 (hackathon demo)"
BBOX = (45.70, 21.14, 45.81, 21.32)  # south, west, north, east: Timișoara

AMENITIES = ("community_centre", "social_centre", "library", "arts_centre", "cultural_centre", "coworking_space")
LEISURE = ("sports_centre", "sports_hall")  # fitness_centre left out: mostly commercial gym chains

QUERY = f"""[out:json][timeout:90];
(
  nwr["amenity"~"^({'|'.join(AMENITIES)})$"]["name"]({','.join(map(str, BBOX))});
  nwr["leisure"~"^({'|'.join(LEISURE)})$"]["name"]({','.join(map(str, BBOX))});
);
out center tags;"""


def space_id(osm_type: str, osm_id: int) -> str:
    # node/way/relation ids are separate sequences in OSM, so the type is part of the id.
    return f"osm-{osm_type}-{osm_id}"


def normalize_element(el: dict) -> dict | None:
    tags = el.get("tags", {})
    lat = el.get("lat", el.get("center", {}).get("lat"))
    lon = el.get("lon", el.get("center", {}).get("lon"))
    name = (tags.get("name") or "").strip()
    if not name or lat is None or lon is None:
        return None
    street = " ".join(p for p in (tags.get("addr:street"), tags.get("addr:housenumber")) if p)
    return {
        "id": space_id(el["type"], el["id"]),
        "osm_type": el["type"],
        "osm_id": el["id"],
        "name": name,
        "kind": tags.get("amenity") or tags.get("leisure"),
        "lat": round(float(lat), 6),
        "lon": round(float(lon), 6),
        "address": street or None,
        "wheelchair": tags.get("wheelchair"),
        "opening_hours": tags.get("opening_hours"),
    }


def normalize(payload: dict) -> list[dict]:
    spaces = [s for s in map(normalize_element, payload.get("elements", [])) if s]
    ids = [s["id"] for s in spaces]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate space ids: {duplicates}")
    return sorted(spaces, key=lambda s: s["id"])


NEIGHBORHOODS_OUT = OUT.parent / "neighborhoods.json"
NEIGHBORHOODS_QUERY = f"""[out:json][timeout:90];
nwr["place"~"^(suburb|quarter|neighbourhood)$"]["name"]({','.join(map(str, BBOX))});
out center tags;"""


# Shopping/industrial places tagged as neighbourhoods; not where people live.
NOT_RESIDENTIAL = re.compile(r"^(cora|metro\b|zona industrial)", re.IGNORECASE)


def _name_key(name: str) -> str:
    """'Braytim - Timișoara Sud' / 'Braytim-Timișoara Sud' and 'Complex' / 'Complexul Studențesc'
    are the same district: ignore punctuation, spaces and the definite article '-ul'."""
    return re.sub(r"[^a-z0-9]", "", re.sub(r"ul\b", "", normalize_text(name)))


def normalize_neighborhoods(payload: dict) -> list[dict]:
    """One entry per district name; nodes first, then by id, so the choice is stable."""
    order = {"node": 0, "way": 1, "relation": 2}
    seen: dict[str, dict] = {}
    for el in sorted(payload.get("elements", []), key=lambda e: (order.get(e["type"], 3), e["id"])):
        name = (el.get("tags", {}).get("name") or "").strip()
        lat = el.get("lat", el.get("center", {}).get("lat"))
        lon = el.get("lon", el.get("center", {}).get("lon"))
        if not name or lat is None or lon is None or NOT_RESIDENTIAL.search(name):
            continue
        seen.setdefault(_name_key(name), {"name": name, "place": el["tags"]["place"],
                                          "lat": round(float(lat), 6), "lon": round(float(lon), 6)})
    return sorted(seen.values(), key=lambda n: _name_key(n["name"]))


def _fetch(query: str) -> dict:
    last: Exception | None = None
    for url in OVERPASS_URLS:  # public instances often return 502/504 under load
        try:
            resp = httpx.post(url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            print(f"{url}: {exc}", file=sys.stderr)
            last = exc
    raise RuntimeError("all Overpass instances failed") from last


def _write(path: Path, query: str, key: str, items: list[dict]) -> None:
    doc = {
        "source": "OpenStreetMap via Overpass API",
        "attribution": "© OpenStreetMap contributors (ODbL)",
        "license": "ODbL-1.0",
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "bbox": BBOX,
        "query": query,
        key: items,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(items)} {key} to {path}")


def main(argv: list[str]) -> int:
    """No argument: spaces. 'neighborhoods': district centres (each file is fetched once)."""
    if argv[:1] == ["neighborhoods"]:
        _write(NEIGHBORHOODS_OUT, NEIGHBORHOODS_QUERY, "neighborhoods",
               normalize_neighborhoods(_fetch(NEIGHBORHOODS_QUERY)))
    else:
        _write(OUT, QUERY, "spaces", normalize(_fetch(QUERY)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
