"""Offline, idempotent seeding: upsert by stable id. Never calls the network.
    python -m backend.seed.run

Writes the contract tables (docs/CONTRACT.md, backend/app/models.py) from backend.seed.contract.
Only fields that exist on the model are written; a model that does not exist yet (the city-hall proposal
extension: Proiect, ProiectEveniment) is skipped with a notice.
"""
import sys
from datetime import date

from sqlmodel import Session, SQLModel

from backend.seed.build import SeedData, build_seed
from backend.seed.contract import contract_rows

# Insert order respects foreign keys: users -> spaces -> ideas -> interests/bookings -> proiecte -> notifications.
TABLES = ["User", "Space", "Idea", "Interest", "Booking", "Proiect", "ProiectEveniment", "Notification"]


def upsert(session: Session, model: type[SQLModel], rows: list[dict]) -> int:
    fields = set(model.model_fields)
    for row in rows:
        # model_validate (not the constructor) so ISO strings become datetimes on table models.
        session.merge(model.model_validate({k: v for k, v in row.items() if k in fields}))
    return len(rows)


def seed(session: Session, data: SeedData | None = None, models: object | None = None) -> dict[str, int]:
    """Upsert all demo records; returns rows written per model. Safe to run repeatedly."""
    if models is None:
        from backend.app import models as app_models
        models = app_models
    rows = contract_rows(data or build_seed())
    written: dict[str, int] = {}
    for name in TABLES:
        model = getattr(models, name, None)
        if model is None:
            print(f"seed: model {name} not defined yet, skipping", file=sys.stderr)
            continue
        written[name] = upsert(session, model, rows[name])
        session.flush()  # parents before children (foreign keys)
    session.commit()
    return written


def main() -> int:
    from backend.app.db import engine, init_db

    init_db()
    with Session(engine) as session:
        written = seed(session, build_seed(date.today()))
    print("seed:", written or "nothing written (no models yet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
