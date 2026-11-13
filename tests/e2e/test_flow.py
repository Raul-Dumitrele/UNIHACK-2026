"""Main demo flow, end to end. Tests for endpoints P1 has not built yet are xfail(strict=True):
once an endpoint works the test XPASSes, the run fails, and the marker must be removed.
Request/response shapes follow docs/CONTRACT.md; fields marked TBD there are best guesses.
"""
import pytest

from conftest import as_user

pytestmark = pytest.mark.anyio

NOT_BUILT = pytest.mark.xfail(strict=True, reason="endpoint not implemented by P1 yet")
AUTHOR = "demo-user-1"
NEIGHBOURS = ["demo-user-2", "demo-user-3", "demo-user-4", "demo-user-5"]
IDEA_TEXT = "Atelier de reparat biciclete pentru vecini, 15 oameni, 3 ore, avem nevoie de mese și o priză."


async def _create_idea(client):
    r = await client.post("/ideas", json={"text": IDEA_TEXT}, headers=as_user(AUTHOR))
    assert r.status_code in (200, 201), r.text
    return r.json()


async def _reach_threshold(client, idea_id):
    idea = None
    for user in NEIGHBOURS:
        r = await client.post(f"/ideas/{idea_id}/interest", headers=as_user(user))
        assert r.status_code in (200, 201), r.text
        idea = r.json()
        if idea.get("status") == "prag_atins":
            break
    return idea


def _free_slot(seed_data, space_id):
    return next(sl for sl in seed_data.slots if sl["space_id"] == space_id)


def _owner(seed_data, space_id):
    return next(s["owner_id"] for s in seed_data.spaces if s["id"] == space_id)


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


@NOT_BUILT
async def test_create_idea_returns_fallback_dossier(client):
    idea = await _create_idea(client)
    dossier = idea["dossier"]
    assert dossier["source"] == "fallback"  # GEMINI_API_KEY is blanked in conftest
    assert dossier["category"] == "atelier"
    assert dossier["expected_participants"] == 15


@NOT_BUILT
async def test_matches_have_score_and_reason(client):
    idea = await _create_idea(client)
    r = await client.get(f"/ideas/{idea['id']}/matches")
    assert r.status_code == 200
    matches = r.json()
    assert matches, "seeded spaces should produce matches"
    first = matches[0]
    assert {"space_id", "score", "reason"} <= first.keys()
    assert isinstance(first["reason"], str) and first["reason"]
    scores = [m["score"] for m in matches]
    assert scores == sorted(scores, reverse=True)


@NOT_BUILT
async def test_one_interest_per_user_then_threshold(client):
    idea = await _create_idea(client)
    first = await client.post(f"/ideas/{idea['id']}/interest", headers=as_user("demo-user-2"))
    again = await client.post(f"/ideas/{idea['id']}/interest", headers=as_user("demo-user-2"))
    assert first.status_code in (200, 201)
    assert again.status_code in (200, 409)
    count = lambda body: body.get("interest_count")  # noqa: E731
    if again.status_code == 200:
        assert count(again.json()) == count(first.json())
    idea = await _reach_threshold(client, idea["id"])
    assert idea["status"] == "prag_atins"


@NOT_BUILT
async def test_booking_needs_owner_approval_and_slot_disappears(client, seed_data):
    idea = await _create_idea(client)
    await _reach_threshold(client, idea["id"])
    space_id = (await client.get(f"/ideas/{idea['id']}/matches")).json()[0]["space_id"]
    slot, owner = _free_slot(seed_data, space_id), _owner(seed_data, space_id)

    r = await client.post("/bookings", json={"idea_id": idea["id"], "slot_id": slot["id"]}, headers=as_user(AUTHOR))
    assert r.status_code in (200, 201), r.text
    booking = r.json()

    not_owner = await client.patch(f"/bookings/{booking['id']}", json={"status": "aprobata"}, headers=as_user(AUTHOR))
    assert not_owner.status_code == 403

    approved = await client.patch(f"/bookings/{booking['id']}", json={"status": "aprobata"}, headers=as_user(owner))
    assert approved.status_code == 200 and approved.json()["status"] == "aprobata"

    taken = await client.post("/bookings", json={"idea_id": idea["id"], "slot_id": slot["id"]}, headers=as_user(AUTHOR))
    assert taken.status_code == 409


@pytest.mark.xfail(strict=True, reason="notifications endpoint not in docs/CONTRACT.md yet")
async def test_author_is_notified_on_status_change(client):
    idea = await _create_idea(client)
    await _reach_threshold(client, idea["id"])
    r = await client.get("/notifications", headers=as_user(AUTHOR))
    assert r.status_code == 200
    assert any(n.get("idea_id") == idea["id"] for n in r.json())


@pytest.mark.xfail(strict=True, reason="backend.app.models not published by P1 yet")
async def test_seed_populates_database_idempotently(seed_data):
    from sqlmodel import Session, func, select

    from backend.app import models
    from backend.app.db import engine
    from backend.seed.run import seed

    def counts():
        with Session(engine) as s:
            return {name: s.exec(select(func.count()).select_from(getattr(models, name))).one()
                    for name in ("User", "Space", "Slot", "Idea", "Interest", "Booking", "Notification")}

    before = counts()
    assert before["Space"] == len(seed_data.spaces) and before["User"] == len(seed_data.users)
    with Session(engine) as s:
        seed(s, seed_data)
    assert counts() == before


@NOT_BUILT
async def test_api_matches_agree_with_p3_ranking(client, seed_data):
    from backend.ai import match_spaces

    idea = next(i for i in seed_data.ideas if i["id"] == "demo-idea-3")
    author = next(u for u in seed_data.users if u["id"] == idea["author_id"])
    expected = [m.space_id for m in match_spaces(idea["dossier"], seed_data.spaces, author["neighborhood"], limit=3)]
    r = await client.get(f"/ideas/{idea['id']}/matches", headers=as_user(author["id"]))
    assert r.status_code == 200
    assert [m["space_id"] for m in r.json()[:3]] == expected


@pytest.mark.xfail(strict=True, reason="notifications endpoint not in docs/CONTRACT.md yet")
async def test_seeded_notifications_are_listed(client, seed_data):
    mine = [n for n in seed_data.notifications if n["user_id"] == "demo-user-1"]
    r = await client.get("/notifications", headers=as_user("demo-user-1"))
    assert r.status_code == 200
    assert {n["id"] for n in mine} <= {n["id"] for n in r.json()}


@NOT_BUILT
async def test_impact_reports_estimate(client):
    r = await client.get("/impact")
    assert r.status_code == 200
    body = r.json()
    assert {"idei_realizate", "spatii_activate", "ore_folosite", "participanti", "km_economisiti"} <= body.keys()
    assert body["km_economisiti_estimare"] is True
