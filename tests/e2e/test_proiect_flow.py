""""Propunere către Primărie", end to end: create -> trimite -> inainteaza -> decizie.

Endpoints belong to P1 and are not built yet, so every test is xfail(strict=True): once one passes
the run fails and the marker must be removed. Request bodies follow the contract extension agreed by
the team; fields still being finalized in docs/CONTRACT.md are best guesses.
"""
import pytest

from conftest import as_user

pytestmark = pytest.mark.anyio

NOT_BUILT = pytest.mark.xfail(strict=True, reason="proiect rule still TODO in P1's router (faza B)")
AUTHOR = "demo-user-5"  # author of demo-idea-8 (threshold reached in the seed)
VERIFIER = "demo-user-10"
CITY_HALL = "demo-user-9"
RESIDENT = "demo-user-1"
DISCLAIMER_START = "Estimare orientativă, bazată pe proiecte de referință."


async def _create(client):
    r = await client.post(
        "/ideas/demo-idea-8/proiect",
        json={"space_id": "demo-space-teren-1", "tip_amenajare": "skatepark", "suprafata_mp": 600},
        headers=as_user(AUTHOR),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


async def _step(client, proiect_id, action, user, body=None):
    r = await client.post(f"/proiecte/{proiect_id}/{action}", json=body or {}, headers=as_user(user))
    assert r.status_code == 200, r.text
    return r.json()


async def test_create_project_has_dossier_references_and_cost(client):
    p = await _create(client)
    assert p["stare"] == "draft" and p["autor_id"] == AUTHOR
    assert DISCLAIMER_START in p["dosar"]["justificare"]
    assert p["referinte"] and all(r["sursa_url"].startswith("http") for r in p["referinte"])
    assert p["cost"]["moneda"] == "RON" and p["cost"]["suficient"] is True
    assert set(p["dosar"]["referinte_citate"]) <= {r["id"] for r in p["referinte"]}


@NOT_BUILT
async def test_full_chain_to_agreement_in_principle(client):
    p = await _create(client)
    assert (await _step(client, p["id"], "trimite", AUTHOR))["stare"] == "trimis"
    forwarded = await _step(client, p["id"], "inainteaza", CITY_HALL, {"verificator_id": VERIFIER})
    assert forwarded["stare"] == "in_verificare" and forwarded["verificator_id"] == VERIFIER
    done = await _step(client, p["id"], "decizie", VERIFIER,
                       {"stare": "acord_de_principiu", "mesaj": "Acord de principiu (simulat)."})
    assert done["stare"] == "acord_de_principiu"

    r = await client.get(f"/proiecte/{p['id']}", headers=as_user(AUTHOR))
    assert r.status_code == 200 and r.json()["stare"] == "acord_de_principiu"
    listed = await client.get("/proiecte", headers=as_user(CITY_HALL))
    assert listed.status_code == 200 and any(x["id"] == p["id"] for x in listed.json())


@NOT_BUILT
async def test_only_the_right_roles_can_move_a_project(client):
    p = await _create(client)
    other = await client.post(f"/proiecte/{p['id']}/trimite", json={}, headers=as_user(RESIDENT))
    assert other.status_code == 403  # only the author sends it
    await _step(client, p["id"], "trimite", AUTHOR)
    resident = await client.post(f"/proiecte/{p['id']}/inainteaza", json={"verificator_id": VERIFIER},
                                 headers=as_user(RESIDENT))
    assert resident.status_code == 403
    early = await client.post(f"/proiecte/{p['id']}/decizie", json={"stare": "acord_de_principiu"},
                              headers=as_user(RESIDENT))
    assert early.status_code == 403


@NOT_BUILT
async def test_clarifications_and_rejection_are_recorded(client):
    p = await _create(client)
    await _step(client, p["id"], "trimite", AUTHOR)
    await _step(client, p["id"], "inainteaza", CITY_HALL, {"verificator_id": VERIFIER})
    asked = await _step(client, p["id"], "decizie", VERIFIER, {"stare": "clarificari", "mesaj": "Ce suprafață exactă?"})
    assert asked["stare"] == "clarificari"
    # Rule 8: after clarifications the author sends it again, then it goes back to verification.
    assert (await _step(client, p["id"], "trimite", AUTHOR, {"mesaj": "Suprafața e de 600 mp."}))["stare"] == "trimis"
    await _step(client, p["id"], "inainteaza", CITY_HALL, {"verificator_id": VERIFIER})
    rejected = await _step(client, p["id"], "decizie", VERIFIER, {"stare": "respins", "mesaj": "Teren indisponibil."})
    assert rejected["stare"] == "respins"
    detail = (await client.get(f"/proiecte/{p['id']}", headers=as_user(AUTHOR))).json()
    assert [e["stare_noua"] for e in detail["evenimente"]][-1] == "respins"
    bad = await client.post(f"/proiecte/{p['id']}/decizie", json={"stare": "respins"}, headers=as_user(VERIFIER))
    assert bad.status_code == 422  # a message is required when rejecting


@NOT_BUILT
async def test_author_is_notified_and_impact_counts_projects(client):
    p = await _create(client)
    await _step(client, p["id"], "trimite", AUTHOR)
    await _step(client, p["id"], "inainteaza", CITY_HALL, {"verificator_id": VERIFIER})
    await _step(client, p["id"], "decizie", VERIFIER, {"stare": "acord_de_principiu"})

    notes = await client.get("/notifications", headers=as_user(AUTHOR))
    assert notes.status_code == 200 and any(n.get("proiect_id") == p["id"] for n in notes.json())
    impact = await client.get("/impact")
    assert impact.status_code == 200
    body = impact.json()
    assert body["proiecte_trimise"] >= 1 and body["proiecte_cu_acord"] >= 1
