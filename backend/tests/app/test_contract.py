import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from backend.app.models import Booking, Interest
from backend.tests.app.conftest import h

SLOT = {"zi": "sambata", "de_la": "10:00", "pana_la": "12:00"}
IDEA_KEYS = {"id", "author_id", "titlu", "descriere", "structurat", "prag", "interesati", "stare", "is_demo", "created_at"}


def test_interest_unique_in_db(session, world):
    session.add(Interest(user_id=world["other"], idea_id=world["idea"]))
    session.commit()
    session.add(Interest(user_id=world["other"], idea_id=world["idea"]))
    with pytest.raises(IntegrityError):
        session.commit()


def test_json_fields_roundtrip(session, world):
    from backend.app.models import Space
    s = session.get(Space, world["space"])
    assert s.sloturi == [{"zi": "sambata", "de_la": "10:00", "pana_la": "14:00"}]
    assert s.dotari == ["mese"]


def test_list_endpoints_shapes(client, world):
    users = client.get("/users").json()
    assert {u["id"] for u in users} == {"u-author", "u-owner", "u-other"}
    assert set(users[0]) == {"id", "nume", "rol", "cartier", "lat", "lng"}
    spaces = client.get("/spaces", params={"capacitate_min": 50}).json()
    assert spaces == []
    spaces = client.get("/spaces", params={"dotari": "mese"}).json()
    assert set(spaces[0]) == {"id", "nume", "tip", "lat", "lng", "capacitate", "dotari", "sloturi", "owner_id", "is_demo", "suprafata_mp"}
    idea = client.get("/ideas/i1").json()
    assert set(idea) == IDEA_KEYS and idea["created_at"].endswith("Z")
    assert client.get("/ideas").json()[0]["id"] == "i1"
    m = client.get("/ideas/i1/matches").json()
    assert set(m[0]) == {"space", "scor", "motiv", "suprapunere"} and 0 <= m[0]["scor"] <= 100
    assert set(client.get("/impact").json()) == {"ore_recuperate", "oameni_conectati", "km_economisiti", "proiecte_active", "proiecte_trimise", "proiecte_cu_acord"}


def test_create_idea_defaults(client, world):
    r = client.post("/ideas", json={"descriere": "Club de șah în cartier"}, headers=h(world["author"]))
    assert r.status_code == 201
    body = r.json()
    assert body["stare"] == "deschisa" and body["prag"] == 5 and body["interesati"] == 0
    assert body["titlu"] == body["structurat"]["rezumat"] and len(body["titlu"]) <= 80
    assert set(body["structurat"]) == {"categorie", "persoane", "dotari", "program", "zgomot", "rezumat"}


def test_missing_or_unknown_user_is_401(client, world):
    r = client.post("/ideas", json={"descriere": "ceva"})
    assert r.status_code == 401 and isinstance(r.json()["detail"], str)
    assert client.post("/ideas", json={"descriere": "ceva"}, headers=h("nimeni")).status_code == 401


def test_validation_error_is_romanian_detail(client, world):
    r = client.post("/ideas", json={}, headers=h(world["author"]))
    assert r.status_code == 422 and r.json()["detail"].startswith("Date invalide")


def test_duplicate_interest_is_409(client, world):
    first = client.post("/ideas/i1/interest", headers=h(world["other"]))
    assert first.status_code == 201 and first.json()["interesati"] == 1
    second = client.post("/ideas/i1/interest", headers=h(world["other"]))
    assert second.status_code == 409
    assert client.get("/ideas/i1").json()["interesati"] == 1


def test_booking_create_rules(client, world):
    body = {"idea_id": "i1", "space_id": "s1", "slot": SLOT}
    assert client.post("/bookings", json=body, headers=h(world["other"])).status_code == 403
    r = client.post("/bookings", json=body, headers=h(world["author"]))
    assert r.status_code == 201 and r.json()["stare"] == "cerut"


def test_patch_booking_by_non_owner_is_403(client, session, world):
    session.add(Booking(id="b1", idea_id="i1", space_id="s1", slot=SLOT))
    session.commit()
    for uid in (world["author"], world["other"]):
        r = client.patch("/bookings/b1", json={"stare": "aprobat"}, headers=h(uid))
        assert r.status_code == 403
    assert session.get(Booking, "b1").stare == "cerut"
    ok = client.patch("/bookings/b1", json={"stare": "refuzat"}, headers=h(world["owner"]))
    assert ok.status_code == 200 and ok.json()["stare"] == "refuzat"
    again = client.patch("/bookings/b1", json={"stare": "aprobat"}, headers=h(world["owner"]))
    assert again.status_code == 409


def test_notifications_only_own(client, session, world):
    from backend.app.models import Notification
    session.add(Notification(id="n1", user_id=world["author"], idea_id="i1", mesaj="Salut"))
    session.commit()
    assert [n["id"] for n in client.get("/notifications", headers=h(world["author"])).json()] == ["n1"]
    assert client.get("/notifications", headers=h(world["other"])).json() == []
    assert client.patch("/notifications/n1/read", headers=h(world["other"])).status_code == 403
    r = client.patch("/notifications/n1/read", headers=h(world["author"]))
    assert r.json()["citita"] is True


def test_owner_message_uses_stub(client, world):
    r = client.post("/ideas/i1/owner-message", json={"space_id": "s1", "slot": SLOT}, headers=h(world["author"]))
    assert r.status_code == 200 and isinstance(r.json()["mesaj"], str)


def test_openapi_has_all_contract_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    expected = {
        ("/health", "get"), ("/users", "get"), ("/spaces", "get"), ("/ideas", "post"), ("/ideas", "get"),
        ("/ideas/{idea_id}", "get"), ("/ideas/{idea_id}/matches", "get"), ("/ideas/{idea_id}/interest", "post"),
        ("/ideas/{idea_id}/owner-message", "post"), ("/bookings", "post"), ("/bookings/{booking_id}", "patch"),
        ("/notifications", "get"), ("/notifications/{notification_id}/read", "patch"), ("/impact", "get"),
        ("/ideas/{idea_id}/proiect", "post"), ("/proiecte", "get"), ("/proiecte/{proiect_id}", "get"),
        ("/proiecte/{proiect_id}/trimite", "post"), ("/proiecte/{proiect_id}/inainteaza", "post"),
        ("/proiecte/{proiect_id}/decizie", "post"),
    }
    assert {(p, m) for p, ops in paths.items() for m in ops} == expected
