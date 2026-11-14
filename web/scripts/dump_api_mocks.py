"""Snapshot the REAL backend (P1's API over P3's seed) into web/src/mocks/data, so mocks match the API exactly.

Run from a checkout that has both backend/app (P1) and backend/seed (P3), e.g. the integration branch:

    git worktree add --detach /tmp/integ origin/integrare-2026-11-14
    cd /tmp/integ
    export DATABASE_URL=sqlite:////tmp/seed.db GEMINI_API_KEY=
    PYTHONPATH=. <repo>/backend/.venv/bin/python -m backend.seed.run
    PYTHONPATH=. <repo>/backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8010 &
    PYTHONPATH=. <repo>/backend/.venv/bin/python <repo>/web/scripts/dump_api_mocks.py http://localhost:8010 <repo>/web/src/mocks/data

Everything comes from API responses, except two lists the API does not expose (read from the same DB through
P1's own response schemas): bookings (GET /bookings is not in the contract) and interests (for the mock's
"one interest per user" rule). Nothing is computed here.
"""
import json
import sys
from pathlib import Path

import httpx
from sqlmodel import Session, select

from backend.app import models, schemas
from backend.app.db import engine

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8010"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("mocks-out")


def get(path: str, user: str | None = None):
    r = httpx.get(API + path, headers={"X-User-Id": user} if user else {}, timeout=30)
    r.raise_for_status()
    return r.json()


def main() -> None:
    users = get("/users")
    spaces = get("/spaces")
    ideas = get("/ideas")
    matches = {i["id"]: get(f"/ideas/{i['id']}/matches") for i in ideas}
    impact = get("/impact")

    notifications: dict[str, dict] = {}
    proiecte: dict[str, dict] = {}
    for u in users:
        for n in get("/notifications", u["id"]):
            notifications[n["id"]] = n
        for p in get("/proiecte", u["id"]):
            # Detail (Proiect + evenimente) as a user allowed to see it.
            proiecte.setdefault(p["id"], get(f"/proiecte/{p['id']}", u["id"]))
    # Drafts are visible only to their author; make sure every author's projects are included.
    for u in users:
        for p in get("/proiecte", u["id"]):
            proiecte[p["id"]] = get(f"/proiecte/{p['id']}", u["id"])

    with Session(engine) as s:
        bookings = [schemas.BookingOut.model_validate(b).model_dump(mode="json") for b in s.exec(select(models.Booking))]
        interests = [{"user_id": i.user_id, "idea_id": i.idea_id} for i in s.exec(select(models.Interest))]

    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.json"):
        f.unlink()
    payloads = {
        "users": users, "spaces": spaces, "ideas": ideas, "matches": matches, "impact": impact,
        "notifications": sorted(notifications.values(), key=lambda n: n["created_at"], reverse=True),
        "proiecte": list(proiecte.values()), "bookings": bookings, "interests": interests,
    }
    for name, payload in payloads.items():
        (OUT / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print({k: len(v) for k, v in payloads.items()})


if __name__ == "__main__":
    main()
