import os
import tempfile
from pathlib import Path

# Must be set before backend.app is imported (engine is created at import time).
_DB = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB.as_posix()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from backend.app.db import engine  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import Booking, Idea, Space, User  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    from backend.app import models  # noqa: F401

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session():
    with Session(engine) as s:
        yield s


@pytest.fixture
def world(session):
    """author (cetatean), owner (proprietar), other (cetatean), one space, one idea at prag_atins."""
    author = User(id="u-author", nume="Ana", rol="cetatean", cartier="Centru", lat=44.43, lng=26.10)
    owner = User(id="u-owner", nume="Ion", rol="proprietar", cartier="Centru", lat=44.43, lng=26.10)
    other = User(id="u-other", nume="Maria", rol="cetatean", cartier="Nord", lat=44.45, lng=26.08)
    space = Space(
        id="s1", nume="Sala 1", tip="scoala", lat=44.43, lng=26.10, capacitate=40,
        dotari=["mese"], sloturi=[{"zi": "sambata", "de_la": "10:00", "pana_la": "14:00"}],
        owner_id=owner.id, is_demo=True,
    )
    idea = Idea(
        id="i1", author_id=author.id, titlu="Atelier", descriere="Atelier de pictură",
        structurat={"categorie": "creativ", "persoane": 10, "dotari": [], "program": [], "zgomot": "scazut", "rezumat": "Atelier"},
        stare="prag_atins",
    )
    session.add_all([author, owner, other, space, idea])
    session.commit()
    return {"author": author.id, "owner": owner.id, "other": other.id, "space": space.id, "idea": idea.id}


def h(user_id: str) -> dict:
    return {"X-User-Id": user_id}
