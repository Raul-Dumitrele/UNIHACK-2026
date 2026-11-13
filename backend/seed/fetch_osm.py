"""One-time fetch of candidate community spaces in Timișoara from OpenStreetMap (Overpass).

Run once, commit the JSON; seeding (run.py) is offline and never calls the network.
    python -m backend.seed.fetch_osm
Data © OpenStreetMap contributors, ODbL 1.0 (see docs/DATA.md).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent / "data" / "osm_spaces.json"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
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


def main() -> int:
    resp = httpx.post(OVERPASS_URL, data={"data": QUERY}, headers={"User-Agent": USER_AGENT}, timeout=120)
    resp.raise_for_status()
    spaces = normalize(resp.json())
    doc = {
        "source": "OpenStreetMap via Overpass API",
        "attribution": "© OpenStreetMap contributors (ODbL)",
        "license": "ODbL-1.0",
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "bbox": BBOX,
        "query": QUERY,
        "spaces": spaces,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(spaces)} spaces to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
