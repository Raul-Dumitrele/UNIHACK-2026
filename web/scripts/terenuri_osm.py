"""Candidate free plots in Timișoara from OpenStreetMap (landuse=brownfield|greenfield|vacant), one per neighbourhood.

    python3 web/scripts/terenuri_osm.py                       # list candidates (400-5000 mp, no name), needs network
    python3 web/scripts/terenuri_osm.py --write 159603642,1076560842,...   # write src/mocks/data/terenuri_osm.json

How the 8 plots in the file were chosen (2026-11-15): the list above, one candidate per neighbourhood, then each one looked at
on satellite imagery (Esri World Imagery, polygon drawn on top). Kept: lots that look empty (grass, bare ground, gravel);
dropped: courtyards, parking lots, lots with houses on them, tiny or odd shapes. NOT checked: who owns them, whether they
are free to use, zoning. They are CANDIDATES: the UI shows "exemplu" and the dossier asks the Primărie to confirm.
Area comes from the polygon (shoelace, local metres). Data © OpenStreetMap contributors, ODbL 1.0.
Neighbourhood = nearest point of P3's neighbourhoods.json (docs/DATA.md), passed with --hoods.
"""
import argparse
import json
import math
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "src" / "mocks" / "data" / "terenuri_osm.json"
BBOX = "45.69,21.14,45.82,21.33"
QUERY = f'[out:json][timeout:60];way["landuse"~"^(brownfield|greenfield|vacant)$"]({BBOX});out tags geom;'
URLS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


def fetch() -> list[dict]:
    for url in URLS:
        raw = subprocess.run(["curl", "-s", "-m", "90", "-A", "LocComun-hackathon/0.1", "--data-urlencode", f"data={QUERY}", url],
                             capture_output=True, text=True).stdout
        if raw.startswith("{"):
            return json.loads(raw)["elements"]
    raise SystemExit("Overpass is busy; try again in a minute")


def measure(geom: list[dict]) -> tuple[float, float, float]:
    lat0 = sum(p["lat"] for p in geom) / len(geom)
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110540
    pts = [(p["lon"] * kx, p["lat"] * ky) for p in geom]
    area = abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))) / 2
    return area, lat0, sum(p["lon"] for p in geom) / len(geom)


def candidates(hoods: list[dict]) -> list[dict]:
    rows = []
    for e in fetch():
        g = e.get("geometry")
        if not g or len(g) < 4 or e["tags"].get("name"):
            continue
        area, lat, lon = measure(g)
        if 400 <= area <= 5000:
            h = min(hoods, key=lambda h: (h["lat"] - lat) ** 2 + ((h["lon"] - lon) * 0.7) ** 2)
            rows.append({"osm_id": e["id"], "landuse": e["tags"]["landuse"], "suprafata_mp": round(area), "lat": round(lat, 6), "lng": round(lon, 6), "cartier": h["name"]})
    return sorted(rows, key=lambda r: (r["cartier"], r["suprafata_mp"]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hoods", default="backend/seed/data/neighborhoods.json")
    ap.add_argument("--write", help="comma-separated OSM way ids to keep (after checking them on satellite imagery)")
    args = ap.parse_args()
    hoods = json.loads(Path(args.hoods).read_text(encoding="utf-8"))["neighborhoods"]
    rows = candidates(hoods)
    if not args.write:
        for r in rows:
            print(r["osm_id"], r["cartier"], r["suprafata_mp"], r["lat"], r["lng"], r["landuse"])
        return
    keep = {int(x) for x in args.write.split(",")}
    out = []
    for r in rows:
        if r["osm_id"] in keep:
            out.append({
                "id": f"teren-osm-{r['osm_id']}", "nume": f"Teren viran, {r['cartier']} (candidat OSM)", "tip": "teren_liber",
                "lat": r["lat"], "lng": r["lng"], "capacitate": 0, "dotari": [], "sloturi": [], "owner_id": "demo-user-9",
                "is_demo": True, "suprafata_mp": r["suprafata_mp"],
                "sursa": "osm", "cartier": r["cartier"], "status_verificare": "neconfirmat",
                "sursa_detalii": f"OpenStreetMap way {r['osm_id']}, landuse={r['landuse']}; aspect liber verificat pe imagini satelit; proprietar și statut neconfirmate",
            })
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} plots to {OUT}")


if __name__ == "__main__":
    main()
