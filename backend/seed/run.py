"""Offline, idempotent seeding: upsert by stable id. Never calls the network.
    python -m backend.seed.run

Binding to the database: each record list maps to a SQLModel class in backend.app.models by name.
Only fields that exist on the model are written; a missing model is skipped with a notice
(models are owned by P1 and still being defined).
"""
import sys
from datetime import date

from sqlmodel import Session, SQLModel

from backend.seed.build import SeedData, build_seed

# Insert order respects foreign keys: users -> spaces -> slots -> ideas -> interests/bookings -> proiecte
# -> proiect events -> notifications (which may point at a proiect).
TABLES = [
    ("users", "User"), ("spaces", "Space"), ("slots", "Slot"), ("ideas", "Idea"),
    ("interests", "Interest"), ("bookings", "Booking"), ("proiecte", "Proiect"),
    ("proiect_evenimente", "ProiectEveniment"), ("notifications", "Notification"),
]


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
    data = data or build_seed()
    written: dict[str, int] = {}
    for attr, name in TABLES:
        model = getattr(models, name, None)
        if model is None:
            print(f"seed: model {name} not defined yet, skipping {attr}", file=sys.stderr)
            continue
        written[name] = upsert(session, model, getattr(data, attr))
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
