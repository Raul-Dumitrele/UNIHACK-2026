"""Snapshot the REAL backend into web/src/mocks/data, so the demo mode shows exactly what the API answers.

Run from the repo root, on a throwaway database (never on the demo database):

    export DATABASE_URL=sqlite:////tmp/loccomun-mocks.db GEMINI_API_KEY= REFERENCES_LIVE_SEARCH=false
    backend/.venv/bin/python -m backend.seed.run
    backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8010 &
    backend/.venv/bin/python web/scripts/dump_api_mocks.py http://localhost:8010 web/src/mocks/data

What it does, all through the API:
  * creates the demo scenarios (scripts/demo_cases.py: one project in every state, with votes);
  * saves users, spaces, impact, notifications, projects (with events), who voted what, and for every project its
    plan, materials and the six documents;
  * saves the plot choice (/terenuri/potrivite) and the analysis (/proiecte/analiza: specification per kind,
    feasibility per kind and plot) for the kinds below, plus the generic answer for an unknown kind.
Nothing is computed here: every field is what the API sent.
"""
import json
import shutil
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import demo_cases  # noqa: E402

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
API = ARGS[0] if ARGS else "http://localhost:8010"
OUT = Path(ARGS[1]) if len(ARGS) > 1 else Path("mocks-out")
# What the user may type -> asked as such; the answer's own `tip_amenajare` is the key in the mock tables.
TIPURI = ["skatepark", "loc_de_joaca", "parc_caini", "pista_biciclete", "gradina_comunitara", "teren_sport", "foisor", "parc acvatic"]
GENERIC = "altceva"  # an unknown kind: the generic specification (the mock puts the user's own words in its place)
MINIME = [100, 250, 400, 600]
FISIERE = ["plan.svg", "plan.dxf", "plansa.pdf", "dosar.pdf", "materiale.xlsx", "materiale.csv"]
CITIZEN = "demo-user-1"

client = httpx.Client(base_url=API, timeout=180)


def call(method: str, path: str, user: str | None = None, **kw):
    r = client.request(method, path, headers={"X-User-Id": user} if user else {}, **kw)
    r.raise_for_status()
    return r


def get(path: str, user: str | None = None):
    return call("GET", path, user).json()


def analiza(tip: str, space_id: str | None = None) -> dict:
    body = {"tip_amenajare": tip, "descriere": None, "suprafata_mp": None, "space_id": space_id}
    return call("POST", "/proiecte/analiza", CITIZEN, json=body).json()


def main() -> None:
    demo_cases.create(API)

    users = get("/users")
    notifications: dict[str, dict] = {}
    proiecte: dict[str, dict] = {}
    visible_to: dict[str, str] = {}
    voturi: list[dict] = []
    for u in users:
        for n in get("/notifications", u["id"]):
            notifications[n["id"]] = n
        for p in get("/proiecte", u["id"]) + get("/proiecte/publice", u["id"]):
            detail = get(f"/proiecte/{p['id']}", u["id"])
            if detail.pop("votat_de_mine", False):
                voturi.append({"proiect_id": p["id"], "user_id": u["id"]})
            proiecte[p["id"]] = detail
            visible_to.setdefault(p["id"], u["id"])

    OUT.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(OUT / "documente", ignore_errors=True)  # documents of projects that no longer exist
    docs_json: dict[str, dict] = {}
    for pid, user in visible_to.items():
        folder = OUT / "documente" / pid
        folder.mkdir(parents=True, exist_ok=True)
        docs_json[pid] = {"plan": get(f"/proiecte/{pid}/plan", user), "materiale": get(f"/proiecte/{pid}/materiale", user)}
        for name in FISIERE:
            (folder / name).write_bytes(call("GET", f"/proiecte/{pid}/documente/{name}", user).content)

    plots = get("/spaces?tip=teren_liber")
    spec: dict[str, dict] = {}
    fez: dict[str, dict] = {}
    potrivite: dict[str, dict] = {}
    for tip in [*TIPURI, GENERIC]:
        a = analiza(tip)
        key = "_generic" if tip == GENERIC else a["tip_amenajare"]
        spec[key] = a["specificatie"]
        minim = a["specificatie"]["suprafata_minima_mp"]
        fez[key] = {"_": a["fezabilitate"]}
        for s in plots:
            if (s.get("suprafata_mp") or 0) >= minim:  # smaller plots are never offered for this kind
                fez[key][s["id"]] = analiza(tip, s["id"])["fezabilitate"]
        potrivite[key] = {
            str(m): get(f"/terenuri/potrivite?tip_amenajare={tip}&suprafata_minima={m}&limit=50", CITIZEN)
            for m in sorted({*MINIME, int(minim)})
        }

    payloads = {
        "users": users,
        "spaces": get("/spaces"),
        "impact": get("/impact"),
        "notifications": sorted(notifications.values(), key=lambda n: n["created_at"], reverse=True),
        "proiecte": sorted(proiecte.values(), key=lambda p: p["updated_at"], reverse=True),
        "voturi": voturi,
        "documente_json": docs_json,
        "terenuri_potrivite": potrivite,
        "analiza": {"specificatie": spec, "fezabilitate": fez},
    }
    for name, payload in payloads.items():
        (OUT / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print({k: len(v) for k, v in payloads.items()})


if __name__ == "__main__":
    main()
