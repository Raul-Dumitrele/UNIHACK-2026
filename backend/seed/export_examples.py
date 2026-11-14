"""Write example payloads from the demo seed, so web/mobile can build screens with real-looking data.

    python -m backend.seed.export_examples
Output: backend/seed/data/examples/*.json in the contract shapes (docs/CONTRACT.md): users, spaces_sample,
ideas, bookings, notifications, impact (computed by backend.impact.compute_impact on a throwaway database).
The city-hall proposal extension (not in the contract yet) is exported as P3 proposals: teren_liber,
proiecte, proiect_evenimente. The slot date is fixed so the files do not change on every run.
"""
import json
import sys
from datetime import date
from pathlib import Path

from backend.seed.build import build_seed
from backend.seed.contract import contract_rows

OUT = Path(__file__).resolve().parent / "data" / "examples"
EXAMPLE_START = date(2026, 11, 16)


def _impact(data) -> dict:
    from sqlmodel import Session, SQLModel, create_engine

    from backend.app import models  # noqa: F401  (registers the contract tables)
    from backend.impact import compute_impact
    from backend.seed.run import seed

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, data)
        return compute_impact(session).model_dump(mode="json")


def build_examples(start: date = EXAMPLE_START) -> dict[str, object]:
    data = build_seed(start)
    rows = contract_rows(data)
    return {
        "users": rows["User"],
        "spaces_sample": rows["Space"][:5],
        "ideas": rows["Idea"],
        "bookings": rows["Booking"],
        "notifications": rows["Notification"],
        "impact": _impact(data),
        # "Propunere către Primărie": P3 proposals, not in docs/CONTRACT.md yet.
        "teren_liber": [s for s in data.spaces if s["kind"] == "teren_liber"],
        "proiecte": data.proiecte,
        "proiect_evenimente": data.proiect_evenimente,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    payloads = build_examples()
    for stale in OUT.glob("*.json"):
        if stale.stem not in payloads:
            stale.unlink()  # shapes that are no longer part of the examples (e.g. pre-contract matches)
    for name, payload in payloads.items():
        (OUT / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote examples to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
