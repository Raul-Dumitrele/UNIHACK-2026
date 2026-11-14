"""Free-text proposals and plots marked by users, end to end on the real seed (rules 12 and 14 in
docs/CONTRACT.md; endpoints by P1, plan/plot ranking/dossier by P3).
"""
import pytest

from conftest import as_user

pytestmark = pytest.mark.anyio

AUTHOR = "demo-user-3"
OTHER = "demo-user-1"
INSIDE = {"lat": 45.7472, "lng": 21.2087}  # Timișoara


async def _mark(client, user=AUTHOR, **extra):
    body = {"nume": "Teren viran lângă parc (test)", **INSIDE, "suprafata_mp": 900, **extra}
    return await client.post("/spaces", json=body, headers=as_user(user))


async def _project(client, space_id, tip, user=AUTHOR):
    r = await client.post("/proiecte", json={"space_id": space_id, "tip_amenajare": tip,
                                             "descriere": f"Propunem {tip} pentru vecini."}, headers=as_user(user))
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.parametrize("tip", ["foișor", "Fântână arteziană", "parc acvatic"])
async def test_free_text_proposal_gets_a_dossier_and_a_plan(client, tip):
    p = await _project(client, "demo-space-teren-1", tip)
    assert p["stare"] == "draft" and p["dosar"]["titlu"]
    assert "Nu reprezintă o autorizație" in p["dosar"]["justificare"]
    plan = (await client.get(f"/proiecte/{p['id']}/plan", headers=as_user(AUTHOR))).json()
    assert plan["elemente"] and plan["complet"]
    pdf = await client.get(f"/proiecte/{p['id']}/documente/dosar.pdf", headers=as_user(AUTHOR))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


async def test_free_text_plot_search(client):
    r = await client.get("/terenuri/potrivite", params={"tip_amenajare": "fântână arteziană", "suprafata_minima": 100})
    assert r.status_code == 200 and r.json()


async def test_marked_plot_is_unverified_with_district_and_can_be_ranked(client):
    r = await _mark(client)
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["tip"] == "teren_liber" and s["is_demo"] is False and s["owner_id"] == AUTHOR
    assert s["sursa"] == "marcat_de_utilizator" and s["status_verificare"] == "neverificat" and s["cartier"]
    found = (await client.get("/terenuri/potrivite", params={"tip_amenajare": "loc_de_joaca",
                                                              "suprafata_minima": 800})).json()
    assert s["id"] in [p["space_id"] for p in found]


async def test_plot_outside_timisoara_or_unauthenticated_is_refused(client):
    assert (await _mark(client, lat=44.43, lng=26.10)).status_code == 422  # Bucharest
    r = await client.post("/spaces", json={"nume": "x", **INSIDE, "suprafata_mp": 300})
    assert r.status_code == 401


async def test_projects_on_a_plot_public_after_sending_drafts_only_for_the_author(client):
    s = (await _mark(client)).json()
    p = await _project(client, s["id"], "loc_de_joaca")
    public = (await client.get(f"/spaces/{s['id']}/proiecte")).json()
    assert p["id"] not in [x["id"] for x in public]  # a draft is private
    own = (await client.get(f"/spaces/{s['id']}/proiecte", headers=as_user(AUTHOR))).json()
    assert p["id"] in [x["id"] for x in own]
    other = (await client.get(f"/spaces/{s['id']}/proiecte", headers=as_user(OTHER))).json()
    assert p["id"] not in [x["id"] for x in other]
    assert (await client.post(f"/proiecte/{p['id']}/trimite", json={}, headers=as_user(AUTHOR))).status_code == 200
    public = (await client.get(f"/spaces/{s['id']}/proiecte")).json()
    assert p["id"] in [x["id"] for x in public]
    assert (await client.get("/spaces/nu-exista/proiecte")).status_code == 404


async def test_seed_plots_have_district_and_verification_status(client):
    plots = (await client.get("/spaces", params={"tip": "teren_liber"})).json()
    assert plots and all(p["cartier"] for p in plots)
    listed = [p for p in plots if p["sursa"] == "lista_primarie"]
    assert listed and all(p["status_verificare"] == "neconfirmat" for p in listed)
    assert all(p["is_demo"] and p["status_verificare"] == "neconfirmat" for p in plots if p["sursa"] == "osm")
