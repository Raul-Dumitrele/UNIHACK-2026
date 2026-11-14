"""Main demo flow, end to end, against P1's API on a temporary database seeded by P3.

Shapes and rules follow docs/CONTRACT.md; every rule is implemented by P1 and checked here.
"""
import pytest

from conftest import as_user

pytestmark = pytest.mark.anyio

AUTHOR = "demo-user-1"
NEIGHBOURS = ["demo-user-2", "demo-user-3", "demo-user-4"]
IDEA_TEXT = ("Atelier de reparat biciclete pentru vecini, sâmbătă 10-13, 15 oameni, 3 ore. "
             "Avem nevoie de mese și o priză.")
STRUCTURAT_KEYS = {"categorie", "persoane", "dotari", "program", "zgomot", "rezumat"}


def _rows(seed_data):
    from backend.seed.contract import contract_rows

    return contract_rows(seed_data)


def _bookable_space(seed_data, skip=()):
    return next(s for s in _rows(seed_data)["Space"] if s["sloturi"] and s["id"] not in skip)


async def _create_idea(client, prag=None, author=AUTHOR):
    body = {"descriere": IDEA_TEXT} | ({"prag": prag} if prag else {})
    r = await client.post("/ideas", json=body, headers=as_user(author))
    assert r.status_code == 201, r.text
    return r.json()


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


async def test_create_idea_is_structured_by_p3(client):
    idea = await _create_idea(client)
    s = idea["structurat"]
    assert set(s) == STRUCTURAT_KEYS and idea["stare"] == "deschisa" and idea["prag"] == 5
    assert s["categorie"] == "creativ" and s["persoane"] == 15  # GEMINI_API_KEY is blanked in conftest
    assert {"mese", "priza"} <= set(s["dotari"])
    assert s["program"] == [{"zi": "sambata", "de_la": "10:00", "pana_la": "13:00"}]
    assert idea["titlu"] == s["rezumat"] and len(idea["titlu"]) <= 80


async def test_interest_once_per_user(client):
    idea = await _create_idea(client)
    first = await client.post(f"/ideas/{idea['id']}/interest", headers=as_user("demo-user-2"))
    again = await client.post(f"/ideas/{idea['id']}/interest", headers=as_user("demo-user-2"))
    assert first.status_code == 201 and first.json()["interesati"] == 1
    assert again.status_code == 409


async def test_threshold_moves_idea_to_prag_atins(client):
    idea = await _create_idea(client, prag=2)
    for user in NEIGHBOURS[:2]:
        r = await client.post(f"/ideas/{idea['id']}/interest", headers=as_user(user))
        assert r.status_code == 201
    assert r.json()["stare"] == "prag_atins"


async def test_matches_have_score_and_reason(client):
    r = await client.get("/ideas/demo-idea-3/matches")
    assert r.status_code == 200
    matches = r.json()
    assert matches and {"space", "scor", "motiv", "suprapunere"} <= matches[0].keys()
    assert [m["scor"] for m in matches] == sorted((m["scor"] for m in matches), reverse=True)


async def test_owner_message_is_written_by_p3(client, seed_data):
    space = _bookable_space(seed_data)
    r = await client.post("/ideas/demo-idea-2/owner-message",
                          json={"space_id": space["id"], "slot": space["sloturi"][0]}, headers=as_user("demo-user-2"))
    assert r.status_code == 200
    text = r.json()["mesaj"]
    assert space["nume"] in text and space["sloturi"][0]["de_la"] in text and text.startswith("Bună ziua")


async def test_booking_request_and_owner_decision(client, seed_data):
    space = _bookable_space(seed_data)
    body = {"idea_id": "demo-idea-8", "space_id": space["id"], "slot": space["sloturi"][0]}
    not_author = await client.post("/bookings", json=body, headers=as_user("demo-user-1"))
    assert not_author.status_code == 403
    r = await client.post("/bookings", json=body, headers=as_user("demo-user-5"))
    assert r.status_code == 201 and r.json()["stare"] == "cerut"
    booking = r.json()

    stranger = await client.patch(f"/bookings/{booking['id']}", json={"stare": "aprobat"}, headers=as_user("demo-user-5"))
    assert stranger.status_code == 403
    owner = space["owner_id"]
    approved = await client.patch(f"/bookings/{booking['id']}", json={"stare": "aprobat"}, headers=as_user(owner))
    assert approved.status_code == 200 and approved.json()["stare"] == "aprobat"
    again = await client.patch(f"/bookings/{booking['id']}", json={"stare": "refuzat"}, headers=as_user(owner))
    assert again.status_code == 409


async def test_approval_reserves_idea_takes_slot_and_notifies(client, seed_data):
    space = _bookable_space(seed_data, skip={_bookable_space(seed_data)["id"]})
    slot = space["sloturi"][0]
    r = await client.post("/bookings", json={"idea_id": "demo-idea-2", "space_id": space["id"], "slot": slot},
                          headers=as_user("demo-user-2"))
    booking = r.json()
    await client.patch(f"/bookings/{booking['id']}", json={"stare": "aprobat"}, headers=as_user(space["owner_id"]))
    assert (await client.get("/ideas/demo-idea-2")).json()["stare"] == "rezervata"
    spaces = {s["id"]: s for s in (await client.get("/spaces")).json()}
    assert slot not in spaces[space["id"]]["sloturi"]
    notes = (await client.get("/notifications", headers=as_user("demo-user-2"))).json()
    assert any(n["booking_id"] == booking["id"] for n in notes)


async def test_seeded_notifications_are_listed(client, seed_data):
    mine = {n["id"] for n in _rows(seed_data)["Notification"] if n["user_id"] == AUTHOR}
    r = await client.get("/notifications", headers=as_user(AUTHOR))
    assert r.status_code == 200 and mine and mine <= {n["id"] for n in r.json()}


async def test_seed_populates_database_idempotently(seed_data, e2e_engine):
    from sqlmodel import Session, func, select

    from backend.app import models
    from backend.seed.run import seed

    engine = e2e_engine

    names = ("User", "Space", "Idea", "Interest", "Booking", "Notification")

    def counts():
        with Session(engine) as s:
            return {n: s.exec(select(func.count()).select_from(getattr(models, n))).one() for n in names}

    rows = _rows(seed_data)
    before = counts()
    assert before["User"] == len(rows["User"]) and before["Space"] == len(rows["Space"])
    with Session(engine) as s:
        seed(s, seed_data)
    assert counts() == before
    with Session(engine) as s:
        assert {i["id"] for i in rows["Idea"]} <= {i.id for i in s.exec(select(models.Idea)).all()}


async def test_impact_from_seed(client):
    r = await client.get("/impact")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"ore_recuperate", "oameni_conectati", "km_economisiti", "proiecte_active",
                         "proiecte_trimise", "proiecte_cu_acord"}
    assert body["proiecte_trimise"] >= 1  # the seeded city-hall proposal is in verification
    assert body["proiecte_active"] >= 5 and body["ore_recuperate"] > 0 and body["km_economisiti"] > 0
