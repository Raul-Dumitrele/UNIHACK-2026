from collections.abc import Iterator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from backend.app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def init_db() -> None:
    from backend.app import models  # noqa: F401  (registers tables)

    SQLModel.metadata.create_all(engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """Additive migration: create_all does not alter existing tables, so add new columns (nullable, or NOT NULL with a plain default)."""
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                ddl = col.type.compile(dialect=engine.dialect)
                default = getattr(col.default, "arg", None)
                if col.nullable:
                    clause = ""
                elif isinstance(default, (bool, int, float, str)):
                    # NOT NULL column with a plain default (e.g. is_demo=False): old rows get the default.
                    clause = f" NOT NULL DEFAULT {int(default) if isinstance(default, bool) else repr(default)}"
                else:
                    continue  # cannot add safely; needs a manual reset of the local database
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl}{clause}'))


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
