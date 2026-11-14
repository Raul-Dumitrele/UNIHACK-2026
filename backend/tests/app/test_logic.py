"""Business rules from docs/CONTRACT.md: matching, interest threshold, bookings, notifications, impact."""
import pytest

from backend.app.models import Booking, Idea, Interest, Space, User
from backend.app.services import slots as sl
from backend.app.services.matching import haversine_km, score_space
from backend.tests.app.conftest import h


def SAT(a, b):
    return {"zi": "sambata", "de_la": a, "pana_la": b}


# ---- slot arithmetic -------------------------------------------------------
def test_subtract_splits_slot():
    assert sl.subtract([SAT("10:00", "14:00")], SAT("11:00", "12:00")) == [SAT("10:00", "11:00"), SAT("12:00", "14:00")]
    assert sl.subtract([SAT("10:00", "14:00")], SAT("10:00", "12:00")) == [SAT("12:00", "14:00")]
    assert sl.subtract([SAT("10:00", "14:00")], SAT("10:00", "14:00")) == []
    other_day = {"zi": "duminica", "de_la": "10:00", "pana_la": "14:00"}
    assert sl.subtract([other_day], SAT("10:00", "14:00")) == [other_day]


def test_contains_and_overlap():
    assert sl.contains(SAT("10:00", "14:00"), SAT("10:00", "12:00"))
    assert not sl.contains(SAT("10:00", "14:00"), SAT("13:00", "15:00"))
    assert sl.overlap(SAT("10:00", "12:00"), SAT("11:00", "14:00")) == SAT("11:00", "12:00")
    assert sl.overlap(SAT("10:00", "11:00"), SAT("11:00", "12:00")) is None


# ---- matching, numeric cases -----------------------------------------------
def _space(**kw):
    base = dict(id="x", nume="S", tip="sala", lat=44.43, lng=26.10, capacitate=5, dotari=["mese"],
                sloturi=[SAT("11:00", "14:00")], owner_id="o")
    return Space(**{**base, **kw})


def test_haversine_one_hundredth_degree():
    assert haversine_km(44.43, 26.10, 44.44, 26.10) == pytest.approx(1.112, abs=0.01)


def test_score_numeric_partial_match():
    st = {"persoane": 10, "dotari": ["mese", "wifi"], "program": [SAT("10:00", "12:00")]}
    r = score_space(st, _space(), [(44.43, 26.10)], 0)
    # capacity .5, overlap 1h/2h = .5, amenities 1/2, distance 1 -> 100*(.15+.15+.10+.20)
    assert r["scor"] == 60
    assert r["suprapunere"] == [SAT("11:00", "12:00")]


def test_score_perfect_and_distance_floor():
    st = {"persoane": 4, "dotari": [], "program": [SAT("10:00", "12:00")]}
    sp = _space(capacitate=40, sloturi=[SAT("10:00", "14:00")])
    assert score_space(st, sp, [(44.43, 26.10)], 8)["scor"] == 100
    far = score_space(st, sp, [(44.43 + 0.1, 26.10)], 8)  # > 5 km away -> distance 0
    assert far["scor"] == 80


def test_score_reason_in_romanian():
    st = {"persoane": 10, "dotari": [], "program": [SAT("10:00", "14:00")]}
    sp = _space(capacitate=40, sloturi=[SAT("10:00", "14:00")], lat=44.4354)
    r = score_space(st, sp, [(44.43, 26.10)] * 8, 8)
    assert r["motiv"] == "40 locuri, liber sâmbătă 10-14, la 600 m de 8 interesați"


def test_matches_sorted_and_skip_spaces_without_slots(client, session, world):
    session.add(Space(id="s2", nume="Mic", tip="sala", lat=44.43, lng=26.10, capacitate=2,
                      dotari=[], sloturi=[SAT("10:00", "12:00")], owner_id=world["owner"]))
    session.add(Space(id="s3", nume="Plin", tip="sala", lat=44.43, lng=26.10, capacitate=99,
                      dotari=[], sloturi=[], owner_id=world["owner"]))
    session.commit()
    m = client.get("/ideas/i1/matches").json()
    assert [x["space"]["id"] for x in m] == ["s1", "s2"]
    assert m[0]["scor"] >= m[1]["scor"]


# ---- interest threshold ----------------------------------------------------
def test_threshold_reached_notifies_author(client, session, world):
    idea = session.get(Idea, "i1")
    idea.stare, idea.prag = "deschisa", 2
    session.add(idea)
    session.commit()
    assert client.post("/ideas/i1/interest", headers=h(world["other"])).json()["stare"] == "deschisa"
    r = client.post("/ideas/i1/interest", headers=h(world["owner"]))
    assert r.json()["stare"] == "prag_atins"
    notes = client.get("/notifications", headers=h(world["author"])).json()
    assert len(notes) == 1 and "pragul" in notes[0]["mesaj"]
    client.post("/ideas/i1/interest", headers=h(world["author"]))  # past the threshold: no second notification
    assert len(client.get("/notifications", headers=h(world["author"])).json()) == 1


# ---- bookings --------------------------------------------------------------
def test_booking_slot_must_fit_free_slot(client, world):
    body = {"idea_id": "i1", "space_id": "s1", "slot": SAT("13:00", "15:00")}
    assert client.post("/bookings", json=body, headers=h(world["author"])).status_code == 409


def test_booking_requires_threshold(client, session, world):
    idea = session.get(Idea, "i1")
    idea.stare = "deschisa"
    session.add(idea)
    session.commit()
    body = {"idea_id": "i1", "space_id": "s1", "slot": SAT("10:00", "12:00")}
    assert client.post("/bookings", json=body, headers=h(world["author"])).status_code == 409


def test_booking_saves_message_and_notifies_owner(client, session, world):
    body = {"idea_id": "i1", "space_id": "s1", "slot": SAT("10:00", "12:00"), "mesaj": "Bună ziua!"}
    r = client.post("/bookings", json=body, headers=h(world["author"]))
    assert r.status_code == 201 and r.json()["mesaj"] == "Bună ziua!"
    notes = client.get("/notifications", headers=h(world["owner"])).json()
    assert len(notes) == 1 and notes[0]["booking_id"] == r.json()["id"]


def test_approval_effects(client, session, world):
    # a second idea requests an overlapping slot; approving the first must refuse it
    session.add(User(id="u2", nume="Dan", rol="cetatean", cartier="x", lat=44.43, lng=26.10))
    session.add(Idea(id="i2", author_id="u2", titlu="Alta", descriere="alta idee", structurat={}, stare="prag_atins"))
    session.commit()
    b1 = client.post("/bookings", json={"idea_id": "i1", "space_id": "s1", "slot": SAT("10:00", "12:00")}, headers=h(world["author"])).json()
    b2 = client.post("/bookings", json={"idea_id": "i2", "space_id": "s1", "slot": SAT("11:00", "13:00")}, headers=h("u2")).json()
    ok = client.patch(f"/bookings/{b1['id']}", json={"stare": "aprobat"}, headers=h(world["owner"]))
    assert ok.status_code == 200 and ok.json()["stare"] == "aprobat"
    session.expire_all()
    assert session.get(Idea, "i1").stare == "rezervata"
    assert session.get(Space, "s1").sloturi == [SAT("12:00", "14:00")]
    assert session.get(Booking, b2["id"]).stare == "refuzat"
    assert any("aprobată" in n["mesaj"] for n in client.get("/notifications", headers=h(world["author"])).json())
    assert any("refuzată" in n["mesaj"] for n in client.get("/notifications", headers=h("u2")).json())


def test_refusal_notifies_author_and_keeps_slots(client, session, world):
    b = client.post("/bookings", json={"idea_id": "i1", "space_id": "s1", "slot": SAT("10:00", "12:00")}, headers=h(world["author"])).json()
    client.patch(f"/bookings/{b['id']}", json={"stare": "refuzat"}, headers=h(world["owner"]))
    session.expire_all()
    assert session.get(Space, "s1").sloturi == [SAT("10:00", "14:00")]
    assert session.get(Idea, "i1").stare == "prag_atins"
    assert any("refuzată" in n["mesaj"] for n in client.get("/notifications", headers=h(world["author"])).json())


# ---- impact ----------------------------------------------------------------
def test_impact_counts_approved_booking(client, session, world):
    idea = session.get(Idea, "i1")
    idea.interesati = 3
    session.add(idea)
    for uid in (world["other"], world["owner"]):
        session.add(Interest(user_id=uid, idea_id="i1"))
    session.commit()
    b = client.post("/bookings", json={"idea_id": "i1", "space_id": "s1", "slot": SAT("10:00", "12:00")}, headers=h(world["author"])).json()
    client.patch(f"/bookings/{b['id']}", json={"stare": "aprobat"}, headers=h(world["owner"]))
    imp = client.get("/impact").json()
    assert imp["ore_recuperate"] == 2.0 and imp["oameni_conectati"] == 2
    assert imp["km_economisiti"] == 12.0 and imp["proiecte_active"] == 1


# ---- GET /bookings ---------------------------------------------------------
def test_list_bookings_for_author_and_owner_only(client, session, world):
    session.add(User(id="u3", nume="Dan", rol="cetatean", cartier="x", lat=44.43, lng=26.10))
    session.commit()
    b = client.post("/bookings", json={"idea_id": "i1", "space_id": "s1", "slot": SAT("10:00", "12:00")}, headers=h(world["author"])).json()
    for uid in (world["author"], world["owner"]):
        got = client.get("/bookings", headers=h(uid)).json()
        assert [x["id"] for x in got] == [b["id"]]
        assert set(got[0]) == {"id", "idea_id", "space_id", "slot", "stare", "created_at", "mesaj"}
    assert client.get("/bookings", headers=h(world["other"])).json() == []
    assert client.get("/bookings", headers=h("u3")).json() == []
    assert client.get("/bookings").status_code == 401
