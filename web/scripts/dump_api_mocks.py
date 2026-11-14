"""Snapshot the REAL backend (P1's API over the seed) into web/src/mocks/data, so the mocks are exactly what the API answers.

Run from the repo root, on a throwaway database:

    export DATABASE_URL=sqlite:////tmp/loccomun-mocks.db GEMINI_API_KEY= REFERENCES_LIVE_SEARCH=false
    backend/.venv/bin/python -m backend.seed.run
    backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8010 &
    PYTHONPATH=. backend/.venv/bin/python web/scripts/dump_api_mocks.py http://localhost:8010 web/src/mocks/data --create-projects

What it does, all through the API:
  * adds the candidate plots from web/src/mocks/data/terenuri_osm.json to the throwaway database (see terenuri_osm.py;
    P1 can put the same rows in the seed), so /terenuri/potrivite scores them like any other plot;
  * with --create-projects, creates one project in every state with POST /proiecte and the real transitions;
  * saves users, spaces, impact, notifications, projects (with events), and for every project its plan, materials and the
    four documents; plus /terenuri/potrivite for every kind of project and a few minimum areas.
Nothing is computed here: every field is what the API sent.
"""
import json
import shutil
import sys
from pathlib import Path

import httpx
from sqlmodel import Session

from backend.app import models
from backend.app.db import engine

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
API = ARGS[0] if ARGS else "http://localhost:8010"
OUT = Path(ARGS[1]) if len(ARGS) > 1 else Path("mocks-out")
TIPURI = ["skatepark", "loc_de_joaca", "parc_caini", "pista_biciclete", "gradina_comunitara", "teren_sport", "foisor"]  # foisor = the generic plan for any other kind
MINIME = [100, 250, 400, 600]
FISIERE = ["plan.svg", "plan.dxf", "dosar.pdf", "materiale.csv"]
CITIZEN, PRIMARIE, VERIFICATOR = "demo-user-1", "demo-user-9", "demo-user-10"

client = httpx.Client(base_url=API, timeout=120)


def call(method: str, path: str, user: str | None = None, **kw):
    r = client.request(method, path, headers={"X-User-Id": user} if user else {}, **kw)
    r.raise_for_status()
    return r


def get(path: str, user: str | None = None):
    return call("GET", path, user).json()


def add_osm_plots() -> None:
    src = OUT / "terenuri_osm.json"
    rows = json.loads(src.read_text(encoding="utf-8")) if src.exists() else []
    fields = set(models.Space.model_fields)
    with Session(engine) as s:
        for row in rows:
            if not s.get(models.Space, row["id"]):
                s.add(models.Space(**{k: v for k, v in row.items() if k in fields}))
        s.commit()


def plot_id(cartier: str) -> str:
    return next(s["id"] for s in get("/spaces?tip=teren_liber") if s.get("cartier") == cartier)


def create_projects() -> None:
    """One project per state, through the real endpoints. Descriptions are plain citizen text."""
    plan = [  # (author, tip, cartier of the plot, description, final state)
        ("demo-user-1", "loc_de_joaca", "Torontalului", "Un loc de joacă pentru copiii din cartier, cu leagăne, tobogan și bănci pentru părinți.", "draft"),
        ("demo-user-4", "teren_sport", "Dorobanților", "Un teren de sport în aer liber pentru tinerii din zonă, deschis seara.", "trimis"),
        ("demo-user-3", "gradina_comunitara", "Mehala", "O grădină comunitară cu rame de plantare pentru locatarii blocurilor din jur.", "in_verificare"),
        ("demo-user-2", "parc_caini", "Steaua", "Un parc pentru câini, împrejmuit, cu zonă de joacă și apă.", "clarificari"),
        ("demo-user-1", "skatepark", "Tipografilor", "Un skatepark mic pentru adolescenții din cartier, cu rampe și bănci.", "acord_de_principiu"),
        ("demo-user-5", "pista_biciclete", "Cartierul Vienez", "O pistă pentru biciclete, pentru copii și începători, pe terenul liber de lângă linia ferată.", "respins"),
    ]
    mesaje = {"clarificari": "Precizați cine întreține parcul după deschidere.", "respins": "Terenul este rezervat altei investiții.",
              "acord_de_principiu": "Propunerea este în regulă pentru etapa următoare."}
    for author, tip, cartier, text, final in plan:
        p = call("POST", "/proiecte", author, json={"space_id": plot_id(cartier), "tip_amenajare": tip, "descriere": text}).json()
        pid = p["id"]
        if final == "draft":
            continue
        call("POST", f"/proiecte/{pid}/trimite", author, json={"mesaj": None})
        if final == "trimis":
            continue
        call("POST", f"/proiecte/{pid}/inainteaza", PRIMARIE, json={"verificator_id": VERIFICATOR})
        if final == "in_verificare":
            continue
        call("POST", f"/proiecte/{pid}/decizie", VERIFICATOR, json={"stare": final, "mesaj": mesaje[final]})


def main() -> None:
    add_osm_plots()
    if "--create-projects" in sys.argv:
        create_projects()

    users = get("/users")
    notifications: dict[str, dict] = {}
    proiecte: dict[str, dict] = {}
    visible_to: dict[str, str] = {}
    for u in users:
        for n in get("/notifications", u["id"]):
            notifications[n["id"]] = n
        for p in get("/proiecte", u["id"]):
            proiecte[p["id"]] = get(f"/proiecte/{p['id']}", u["id"])
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

    potrivite = {
        tip: {str(m): get(f"/terenuri/potrivite?tip_amenajare={tip}&suprafata_minima={m}&limit=50", CITIZEN) for m in MINIME}
        for tip in TIPURI
    }

    payloads = {
        "users": users,
        "spaces": get("/spaces"),
        "impact": get("/impact"),
        "notifications": sorted(notifications.values(), key=lambda n: n["created_at"], reverse=True),
        "proiecte": list(proiecte.values()),
        "documente_json": docs_json,
        "terenuri_potrivite": potrivite,
    }
    for name, payload in payloads.items():
        (OUT / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print({k: len(v) for k, v in payloads.items()})


if __name__ == "__main__":
    main()
