from datetime import date, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import JSON, Column
from sqlalchemy.orm import registry
from sqlmodel import Field, Session, SQLModel, create_engine, func, select

from backend.seed.build import SLOT_DAYS, build_seed, load_json
from backend.seed.fetch_osm import normalize, space_id
from backend.seed.run import seed

START = date(2026, 11, 16)  # a Monday


@pytest.fixture(scope="module")
def data():
    return build_seed(START)


# --- OSM normalization (fetch_osm) ---

def test_space_id_includes_osm_type():
    assert space_id("node", 42) == "osm-node-42"
    assert space_id("way", 42) != space_id("node", 42)


def test_normalize_uses_center_and_skips_unnamed():
    payload = {"elements": [
        {"type": "way", "id": 7, "center": {"lat": 45.75, "lon": 21.22},
         "tags": {"name": "Centrul X", "amenity": "community_centre", "addr:street": "Strada Y", "addr:housenumber": "3"}},
        {"type": "node", "id": 7, "lat": 45.7, "lon": 21.2, "tags": {"name": "Bibliotecă", "amenity": "library"}},
        {"type": "node", "id": 8, "lat": 45.7, "lon": 21.2, "tags": {"amenity": "library"}},
    ]}
    spaces = normalize(payload)
    assert [s["id"] for s in spaces] == ["osm-node-7", "osm-way-7"]
    assert spaces[1]["address"] == "Strada Y 3" and spaces[1]["lat"] == 45.75


def test_normalize_rejects_duplicates():
    el = {"type": "node", "id": 1, "lat": 1, "lon": 1, "tags": {"name": "A", "amenity": "library"}}
    with pytest.raises(ValueError, match="duplicate"):
        normalize({"elements": [el, el]})


def test_committed_osm_file_is_attributed_and_unique():
    osm = load_json("osm_spaces.json")
    assert osm["attribution"] == "© OpenStreetMap contributors (ODbL)"
    ids = [s["id"] for s in osm["spaces"]]
    assert len(ids) == len(set(ids)) > 20
    assert all(i.startswith(("osm-node-", "osm-way-", "osm-relation-")) for i in ids)


# --- build (pure, deterministic) ---

def test_build_is_deterministic(data):
    assert build_seed(START) == data


def test_ids_unique_and_everything_is_demo(data):
    for rows in (data.users, data.spaces, data.slots, data.ideas):
        ids = [r["id"] for r in rows]
        assert len(ids) == len(set(ids))
        assert all(r["is_demo"] is True for r in rows)


def test_references_are_consistent(data):
    users = {u["id"]: u for u in data.users}
    space_ids = {s["id"] for s in data.spaces}
    assert all(users[s["owner_id"]]["role"] == "proprietar" for s in data.spaces)
    assert all(sl["space_id"] in space_ids for sl in data.slots)
    assert all(i["author_id"] in users for i in data.ideas)


def test_commercial_venues_excluded(data):
    names = " ".join(s["name"].lower() for s in data.spaces)
    assert "kart" not in names and "paintball" not in names


def test_slots_are_in_window(data):
    past = {b["slot_id"] for b in data.bookings if b["id"] in {"demo-booking-5", "demo-booking-6", "demo-booking-7"}}
    for sl in (s for s in data.slots if s["id"] not in past):
        starts, ends = datetime.fromisoformat(sl["starts_at"]), datetime.fromisoformat(sl["ends_at"])
        assert 0 <= (starts.date() - START).days < SLOT_DAYS
        assert starts < ends


def test_slots_are_local_windows_stored_as_utc(data):
    from backend.seed.build import LOCAL_TZ, SLOT_WINDOWS

    local_starts = {t for t, _ in SLOT_WINDOWS}
    for sl in data.slots:
        starts = datetime.fromisoformat(sl["starts_at"])
        assert starts.utcoffset().total_seconds() == 0
        local = starts.astimezone(LOCAL_TZ)
        assert local.time() in local_starts
        assert sl["id"].endswith(f"-{local.date().isoformat()}-{local:%H%M}")


def test_scenario_covers_every_state(data):
    statuses = {i["status"] for i in data.ideas}
    assert statuses == {"deschisa", "prag_atins", "rezervata"}
    assert {b["status"] for b in data.bookings} == {"ceruta", "aprobata", "refuzata"}
    for idea in data.ideas:
        assert idea["interest_count"] == sum(1 for i in data.interests if i["idea_id"] == idea["id"])


def test_scenario_rules(data):
    users = {u["id"] for u in data.users}
    ideas = {i["id"]: i for i in data.ideas}
    slots = {s["id"]: s for s in data.slots}
    pairs = [(i["idea_id"], i["user_id"]) for i in data.interests]
    assert len(pairs) == len(set(pairs)), "one interest per user per idea"
    assert all(u in users and ideas[i]["author_id"] != u for i, u in pairs), "no self-interest"
    for b in data.bookings:
        assert slots[b["slot_id"]]["space_id"] == b["space_id"]
        assert ideas[b["idea_id"]]["interest_count"] >= 3, "booking only after threshold"
        assert slots[b["slot_id"]]["is_free"] is (b["status"] != "aprobata")
    approved_slots = [b["slot_id"] for b in data.bookings if b["status"] == "aprobata"]
    assert len(approved_slots) == len(set(approved_slots)), "a slot is approved at most once"


def test_past_events_have_past_slots(data):
    past = [b for b in data.bookings if b["id"] in {"demo-booking-5", "demo-booking-6", "demo-booking-7"}]
    slots = {s["id"]: s for s in data.slots}
    assert all(datetime.fromisoformat(slots[b["slot_id"]]["starts_at"]).date() < START for b in past)


def test_notifications(data):
    users = {u["id"] for u in data.users}
    kinds = {n["kind"] for n in data.notifications}
    assert kinds == {"prag_atins", "cerere_rezervare", "rezervare_aprobata", "rezervare_refuzata"}
    assert all(n["user_id"] in users and n["text"] and n["read"] is False for n in data.notifications)
    owners = {s["id"]: s["owner_id"] for s in data.spaces}
    for n in data.notifications:
        if n["kind"] == "cerere_rezervare":
            booking = next(b for b in data.bookings if b["id"] == n["booking_id"])
            assert n["user_id"] == owners[booking["space_id"]]
    ids = [n["id"] for n in data.notifications]
    assert len(ids) == len(set(ids))


def test_format_local():
    from backend.seed.build import LOCAL_TZ
    from backend.seed.scenario import format_local

    assert format_local("2026-11-21T08:00:00+00:00", LOCAL_TZ) == "sâmbătă 21 noiembrie, 10:00"


def test_demo_impact_is_not_empty(data):
    from backend.impact import compute_impact
    from backend.seed.scenario import approved_for_impact

    r = compute_impact(approved_for_impact(data.bookings, data.spaces, data.slots, data.interests, data.users))
    assert r.rezervari_aprobate == 5 and r.idei_realizate == 5
    assert len(r.pe_saptamani) >= 3 and r.km_economisiti > 0


def test_committed_examples_are_up_to_date():
    """If this fails, run: python -m backend.seed.export_examples (and commit the JSON)."""
    import json

    from backend.seed.export_examples import OUT, build_examples

    for name, payload in build_examples().items():
        committed = json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))
        assert committed == json.loads(json.dumps(payload, ensure_ascii=False)), name


def test_ideas_have_fallback_dossier(data):
    bikes = next(i for i in data.ideas if i["id"] == "demo-idea-1")
    assert bikes["dossier"]["source"] == "fallback"
    assert bikes["dossier"]["category"] == "atelier"
    assert bikes["title"] == bikes["dossier"]["title"]


# --- run (DB upsert) against throwaway models; real ones come from backend.app.models ---

_reg = registry()


class _Base(SQLModel, registry=_reg):
    pass


class User(_Base, table=True):
    __tablename__ = "seedtest_user"
    id: str = Field(primary_key=True)
    name: str
    is_demo: bool = False


class Space(_Base, table=True):
    __tablename__ = "seedtest_space"
    id: str = Field(primary_key=True)
    name: str
    capacity: int
    amenities: list[str] = Field(sa_column=Column(JSON))
    owner_id: str
    is_demo: bool = False


class Slot(_Base, table=True):
    __tablename__ = "seedtest_slot"
    id: str = Field(primary_key=True)
    space_id: str
    starts_at: datetime
    ends_at: datetime


FAKE_MODELS = SimpleNamespace(User=User, Space=Space, Slot=Slot)  # no Idea: must be skipped


def _count(session, model):
    return session.exec(select(func.count()).select_from(model)).one()


def test_seed_is_idempotent(data, capsys):
    engine = create_engine("sqlite://")
    _Base.metadata.create_all(engine)
    with Session(engine) as session:
        first = seed(session, data, FAKE_MODELS)
        counts = [_count(session, m) for m in (User, Space, Slot)]
        second = seed(session, data, FAKE_MODELS)
        assert [_count(session, m) for m in (User, Space, Slot)] == counts
    assert first == second == {"User": len(data.users), "Space": len(data.spaces), "Slot": len(data.slots)}
    assert "model Idea not defined yet" in capsys.readouterr().err


def test_seed_upsert_updates_existing_rows(data):
    engine = create_engine("sqlite://")
    _Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, data, FAKE_MODELS)
        session.get(Space, data.spaces[0]["id"]).name = "modificat"
        session.commit()
        seed(session, data, FAKE_MODELS)
        session.expire_all()
        assert session.get(Space, data.spaces[0]["id"]).name == data.spaces[0]["name"]
        assert isinstance(session.get(Slot, data.slots[0]["id"]).starts_at, datetime)
