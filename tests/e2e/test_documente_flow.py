""""Propune pe un teren", end to end on the real seed: pick a plot -> project directly on it -> plan,
material list and documents. Endpoints belong to P1 (rules 11-13 in docs/CONTRACT.md); find_plots, the plan,
the prices and the documents come from P3.
"""
import xml.etree.ElementTree as ET

import pytest

from conftest import as_user

pytestmark = pytest.mark.anyio

AUTHOR = "demo-user-3"
OTHER = "demo-user-1"
CITY_HALL = "demo-user-9"


async def _plots(client, **params):
    r = await client.get("/terenuri/potrivite", params=params)
    assert r.status_code == 200, r.text
    return r.json()


async def _project_on(client, space_id, tip="loc_de_joaca"):
    r = await client.post("/proiecte", json={"space_id": space_id, "tip_amenajare": tip,
                                             "descriere": "Un loc de joacă pentru copiii din cartier, cu bănci."},
                          headers=as_user(AUTHOR))
    assert r.status_code == 201, r.text
    return r.json()


async def test_listed_plots_are_ranked_and_marked_to_confirm(client):
    plots = await _plots(client, tip_amenajare="loc_de_joaca", suprafata_minima=250, cartier="Ronaț")
    assert plots and plots == sorted(plots, key=lambda p: -p["scor"])
    listed = [p for p in plots if p["din_lista_primarie"]]
    assert listed, "the seed has the city hall's Legea 15/2003 lots"
    for p in listed:
        assert p["space_id"].startswith("lista-2019-") and "de confirmat" in p["motiv"] and p["avertisment"]
    assert all(p["suprafata_mp"] >= 250 for p in plots)


async def test_big_project_goes_to_the_osm_candidates_or_the_demo_plot(client):
    plots = await _plots(client, tip_amenajare="skatepark", suprafata_minima=500, cartier="Steaua")
    ids = [p["space_id"] for p in plots]
    assert ids[0] == "teren-osm-445294489"  # the OSM candidate in Steaua
    assert "demo-space-teren-1" in ids and all(p["is_demo"] for p in plots)
    assert not any(p["din_lista_primarie"] for p in plots)


async def test_project_on_a_listed_lot_has_plan_materials_and_documents(client):
    # listed lots lose points (they need a Local Council decision), so the best plot may be another one: pick a listed lot
    plots = await _plots(client, tip_amenajare="loc_de_joaca", suprafata_minima=250, cartier="Ronaț", limit=50)
    best = next(p for p in plots if p["din_lista_primarie"])
    p = await _project_on(client, best["space_id"])
    assert p["stare"] == "draft" and p["space_id"] == best["space_id"]
    assert p["dosar"]["lista_verificare"][0].startswith("Confirmarea faptului că terenul nu a fost atribuit")

    plan = (await client.get(f"/proiecte/{p['id']}/plan", headers=as_user(AUTHOR))).json()
    assert plan["latime_m"] == 12.0 and plan["complet"] and plan["elemente"]
    assert "Nu este un proiect tehnic" in plan["disclaimer"]

    mat = (await client.get(f"/proiecte/{p['id']}/materiale", headers=as_user(AUTHOR))).json()
    assert mat["eticheta_subtotal"].startswith("Subtotal articole cotate (incomplet:")
    assert mat["linii"] and all(l["stare"] in ("cotat", "de_cotat") and l["ipoteza"] for l in mat["linii"])
    assert all((l["valoare_lei"] is None) == (l["stare"] == "de_cotat") for l in mat["linii"])
    assert "CC BY 4.0" in mat["sursa_preturi"] and mat["tva"]

    docs = {}
    for name in ("plan.svg", "plan.dxf", "plansa.pdf", "dosar.pdf", "materiale.xlsx", "materiale.csv"):
        r = await client.get(f"/proiecte/{p['id']}/documente/{name}", headers=as_user(AUTHOR))
        assert r.status_code == 200, (name, r.text)
        assert f'filename="proiect-{p["id"]}-{name}"' in r.headers["content-disposition"]
        docs[name] = r
    assert docs["dosar.pdf"].headers["content-type"] == "application/pdf"
    assert docs["dosar.pdf"].content.startswith(b"%PDF-1.4") and docs["dosar.pdf"].content.rstrip().endswith(b"%%EOF")
    assert ET.fromstring(docs["plan.svg"].content).tag == "{http://www.w3.org/2000/svg}svg"
    assert docs["plan.dxf"].content.decode("ascii").rstrip().endswith("EOF")
    assert docs["materiale.csv"].content.decode("utf-8-sig").startswith("capitol;articol;denumire;cantitate")
    assert docs["materiale.xlsx"].content.startswith(b"PK") and docs["plansa.pdf"].content.startswith(b"%PDF")


async def test_documents_are_private_until_sent(client):
    p = await _project_on(client, "demo-space-teren-1")
    for path in ("plan", "materiale", "documente/dosar.pdf"):
        assert (await client.get(f"/proiecte/{p['id']}/{path}", headers=as_user(OTHER))).status_code == 403
        assert (await client.get(f"/proiecte/{p['id']}/{path}", headers=as_user(CITY_HALL))).status_code == 403
    sent = await client.post(f"/proiecte/{p['id']}/trimite", json={}, headers=as_user(AUTHOR))
    assert sent.status_code == 200
    r = await client.get(f"/proiecte/{p['id']}/documente/dosar.pdf", headers=as_user(CITY_HALL))
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
