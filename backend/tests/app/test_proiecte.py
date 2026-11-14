"""Skeleton-level checks for the 'Propunere catre Primarie' extension (shapes, models, migration)."""
from sqlalchemy import create_engine, inspect, text
from sqlmodel import SQLModel

from backend.app.models import Proiect, ProiectEveniment, Space
from backend.tests.app.conftest import h

PROIECT_KEYS = {
    "id", "idea_id", "space_id", "autor_id", "verificator_id", "tip_amenajare", "suprafata_mp",
    "stare", "dosar", "referinte", "cost", "created_at", "updated_at",
}


def _create(client, world, **body):
    payload = {"space_id": "s1", "tip_amenajare": "skatepark", "suprafata_mp": 1200, **body}
    return client.post("/ideas/i1/proiect", json=payload, headers=h(world["author"]))


def test_create_proiect_shape_and_chain(client, world):
    r = _create(client, world)
    assert r.status_code == 201
    p = r.json()
    assert set(p) == PROIECT_KEYS
    assert p["stare"] == "draft" and p["suprafata_mp"] == 1200
    assert set(p["dosar"]) == {"titlu", "descriere", "justificare", "componente", "etape", "riscuri", "lista_verificare", "referinte_citate"}
    assert "acord de principiu simulat" in p["dosar"]["justificare"]
    assert p["cost"]["moneda"] == "RON" and p["cost"]["suficient"] is True
    assert p["created_at"].endswith("Z")


def test_create_proiect_requires_surface(client, world):
    r = _create(client, world, suprafata_mp=None)  # Space s1 has no suprafata_mp
    assert r.status_code == 422 and r.json()["detail"].startswith("Date invalide")


def test_create_proiect_surface_from_space(client, session, world):
    session.get(Space, "s1").suprafata_mp = 900
    session.commit()
    r = _create(client, world, suprafata_mp=None)
    assert r.status_code == 201 and r.json()["suprafata_mp"] == 900


def test_get_proiect_detail_has_events(client, session, world):
    pid = _create(client, world).json()["id"]
    session.add(ProiectEveniment(proiect_id=pid, user_id=world["author"], stare_noua="draft"))
    session.commit()
    d = client.get(f"/proiecte/{pid}", headers=h(world["author"])).json()
    assert set(d) == PROIECT_KEYS | {"evenimente"} and d["evenimente"][0]["stare_noua"] == "draft"
    assert client.get("/proiecte/nu-exista", headers=h(world["author"])).status_code == 404


def test_new_endpoints_need_user(client, world):
    assert client.get("/proiecte").status_code == 401
    assert client.post("/proiecte/x/trimite", json={}).status_code == 401


def test_decizie_message_required_for_respins(client, world):
    pid = _create(client, world).json()["id"]
    r = client.post(f"/proiecte/{pid}/decizie", json={"stare": "respins"}, headers=h(world["owner"]))
    assert r.status_code == 422
    r = client.post(f"/proiecte/{pid}/decizie", json={"stare": "acord_de_principiu"}, headers=h(world["owner"]))
    assert r.status_code == 200


def test_new_optional_fields_in_responses(client, world):
    assert client.get("/spaces").json()[0]["suprafata_mp"] is None
    b = client.post("/bookings", json={"idea_id": "i1", "space_id": "s1", "slot": {"zi": "sambata", "de_la": "10:00", "pana_la": "12:00"}},
                    headers=h(world["author"])).json()
    assert "mesaj" in b


def test_init_db_adds_missing_columns(tmp_path, monkeypatch):
    """An old database without the new columns is upgraded in place, keeping its rows."""
    import backend.app.db as db

    eng = create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE space (id TEXT PRIMARY KEY, nume TEXT, tip TEXT, lat FLOAT, lng FLOAT, "
                       "capacitate INT, dotari JSON, sloturi JSON, owner_id TEXT, is_demo BOOLEAN)"))
        c.execute(text("INSERT INTO space (id, nume) VALUES ('x', 'Vechi')"))
    monkeypatch.setattr(db, "engine", eng)
    db.init_db()
    cols = {c["name"] for c in inspect(eng).get_columns("space")}
    assert "suprafata_mp" in cols
    assert {"proiect", "proiectEveniment".lower()} <= set(inspect(eng).get_table_names())
    with eng.connect() as c:
        assert c.execute(text("SELECT nume FROM space")).scalar() == "Vechi"
    assert Proiect.__tablename__ == "proiect"
