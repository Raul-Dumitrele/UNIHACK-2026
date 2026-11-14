"""Write example payloads from the demo seed, so web/mobile can build screens before the API exists.

    python -m backend.seed.export_examples
Output: backend/seed/data/examples/*.json (shapes are P3 proposals; docs/CONTRACT.md stays the authority).
The slot date is fixed so the files do not change on every run.
"""
import json
import sys
from datetime import date
from pathlib import Path

from backend.ai.matching import match_spaces
from backend.impact import compute_impact
from backend.seed.build import build_seed
from backend.seed.scenario import approved_for_impact

OUT = Path(__file__).resolve().parent / "data" / "examples"
EXAMPLE_START = date(2026, 11, 16)


def build_examples(start: date = EXAMPLE_START) -> dict[str, object]:
    data = build_seed(start)
    hood = {u["id"]: u["neighborhood"] for u in data.users}
    matches = {
        idea["id"]: [m.model_dump(mode="json") for m in
                     match_spaces(idea["dossier"], data.spaces, hood[idea["author_id"]], limit=5)]
        for idea in data.ideas
    }
    impact = compute_impact(approved_for_impact(data.bookings, data.spaces, data.slots, data.interests, data.users),
                            data.proiecte)
    return {
        "users": data.users,
        "ideas": data.ideas,
        "matches": matches,
        "spaces_sample": data.spaces[:5],
        "slots_sample": [s for s in data.slots if s["space_id"] == data.spaces[0]["id"]],
        "bookings": data.bookings,
        "notifications": data.notifications,
        "impact": impact.model_dump(mode="json"),
        # "Propunere către Primărie": the free plot, one project (dossier, references, cost) and its history.
        "teren_liber": [s for s in data.spaces if s["kind"] == "teren_liber"],
        "proiecte": data.proiecte,
        "proiect_evenimente": data.proiect_evenimente,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, payload in build_examples().items():
        (OUT / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote examples to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
