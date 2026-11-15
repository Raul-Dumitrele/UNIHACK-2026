"""Community flow: analysis before generating, publish, one vote per user, automatic send at the threshold,
public visibility, documents (A3 sheets, XLSX) and the itemised cost that is always present."""
import io
import zipfile

import pytest

from backend.app.models import Space, User
from backend.tests.app.conftest import h


@pytest.fixture
def town(session, world):
    session.add_all([
        User(id="u-prim", nume="Primăria", rol="primarie", cartier="-", lat=44.43, lng=26.10),
        User(id="u-ver", nume="Verificator", rol="verificator", cartier="-", lat=44.43, lng=26.10),
        User(id="u-v1", nume="Vecin 1", rol="cetatean", cartier="Fabric", lat=44.43, lng=26.10),
        User(id="u-v2", nume="Vecin 2", rol="cetatean", cartier="Fabric", lat=44.43, lng=26.10),
        Space(id="t-ev", nume="Teren viran", tip="teren_liber", lat=45.75, lng=21.22, capacitate=0, dotari=[], sloturi=[],
              owner_id="u-prim", suprafata_mp=90, cartier="Mehala", sursa="osm", status_verificare="neconfirmat"),
        Space(id="t-mic", nume="Colț de stradă", tip="teren_liber", lat=45.75, lng=21.22, capacitate=0, dotari=[], sloturi=[],
              owner_id="u-prim", suprafata_mp=200, cartier="Mehala", sursa="osm"),
    ])
    session.commit()
    return {**world, "prim": "u-prim", "ver": "u-ver", "v1": "u-v1", "v2": "u-v2"}


def _ev(client, town, **kw):
    body = {"space_id": "t-ev", "tip_amenajare": "stație de încărcare", "descriere": "Stație de încărcare pentru mașini electrice", **kw}
    r = client.post("/proiecte", json=body, headers=h(town["author"]))
    assert r.status_code == 201, r.text
    return r.json()


# ---- analysis and specification ---------------------------------------------------------------------------------
def test_analiza_flags_unrealistic_proposal(client, town):
    r = client.post("/proiecte/analiza", json={"tip_amenajare": "parc acvatic", "space_id": "t-mic"}, headers=h(town["author"]))
    assert r.status_code == 200
    a = r.json()
    assert a["tip_amenajare"] == "aquapark" and a["fezabilitate"]["nivel"] == "nerealist"
    assert any("3000" in m for m in a["fezabilitate"]["motive"]) and a["fezabilitate"]["recomandari"]
    ok = client.post("/proiecte/analiza", json={"tip_amenajare": "stație de încărcare", "space_id": "t-ev"}, headers=h(town["author"])).json()
    assert ok["fezabilitate"]["nivel"] in ("ok", "atentie") and ok["specificatie"]["componente"]
    assert any(u["nume"] == "energie electrică" for u in ok["fezabilitate"]["utilitati"])
    assert client.post("/proiecte/analiza", json={"tip_amenajare": "x"}).status_code == 401


def test_ev_station_project_is_specific(client, town):
    p = _ev(client, town)
    names = " ".join(c["nume"].lower() for c in p["specificatie"]["componente"])
    for word in ("încărcare", "tablou", "branșament", "parcare", "plată", "marcaj"):
        assert word in names, word
    assert "gazon" not in names and "cauciuc" not in names
    assert p["specificatie"]["sursa_specificatie"] == "model_verificat"
    assert p["fezabilitate"]["nivel"] in ("ok", "atentie")
    d = p["dosar"]
    assert set(d["memoriu"]) >= {"date_generale", "solutia_propusa", "specificatii_tehnice", "documente_necesare"}
    assert any("racordare" in a["nume"].lower() for a in d["acte"]) and d["acte_disclaimer"]
    assert len(d["cereri_tip"]) == 2 and "certificatului de urbanism" in d["cereri_tip"][0]["titlu"]
    assert "acord de principiu simulat" in d["justificare"]


def test_cost_is_always_present_with_itemised_sum(client, town):
    p = _ev(client, town)
    c = p["cost"]
    assert "suma_cotata_lei" in c and isinstance(c["articole_necotate"], list) and c["eticheta_suma"]
    assert c["suma_cotata_lei"] == 0 or c["articole_cotate"] > 0
    mat = client.get(f"/proiecte/{p['id']}/materiale", headers=h(town["author"])).json()
    assert mat["capitole"] and all(l["capitol"] for l in mat["linii"])
    assert len(mat["articole_necotate"]) == mat["linii_de_cotat"]
    for l in mat["linii"]:
        assert (l["valoare_lei"] is None) == (l["stare"] == "de_cotat")
        if l["pret_unitar"]:
            assert l["pret_unitar"]["tip_sursa"] in ("seap", "plafon", "catalog")


def test_plan_has_balance_and_indicators(client, town):
    p = _ev(client, town)
    plan = client.get(f"/proiecte/{p['id']}/plan", headers=h(town["author"])).json()
    assert plan["bilant"] and plan["bilant"][-1]["zona"] == "Total teren"
    assert abs(sum(b["procent"] for b in plan["bilant"][:-1]) - 100) < 1.5
    assert 0 <= plan["pot_procent"] <= 100 and all("inaltime_m" in e for e in plan["elemente"])


def test_new_documents(client, town):
    p = _ev(client, town)
    for name, media, head in (("plansa.pdf", "application/pdf", b"%PDF"),
                              ("materiale.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"PK")):
        r = client.get(f"/proiecte/{p['id']}/documente/{name}", headers=h(town["author"]))
        assert r.status_code == 200 and r.headers["content-type"].startswith(media) and r.content.startswith(head)
    x = client.get(f"/proiecte/{p['id']}/documente/materiale.xlsx", headers=h(town["author"])).content
    z = zipfile.ZipFile(io.BytesIO(x))
    assert z.testzip() is None and {"xl/workbook.xml", "xl/styles.xml", "xl/worksheets/sheet2.xml"} <= set(z.namelist())
    sheet = z.read("xl/worksheets/sheet2.xml").decode("utf-8")
    assert "<f>" in sheet and "de cotat" in sheet or "SUM(" in sheet
    pdf = client.get(f"/proiecte/{p['id']}/documente/plansa.pdf", headers=h(town["author"])).content
    assert b"/MediaBox [0 0 1190.55 841.89]" in pdf  # A3 landscape


# ---- publish, vote, threshold ------------------------------------------------------------------------------------
def test_publish_vote_threshold_sends_to_city_hall(client, town):
    pid = _ev(client, town)["id"]
    assert client.post(f"/proiecte/{pid}/vot", headers=h(town["v1"])).status_code == 409  # not published yet
    assert client.get(f"/proiecte/{pid}").status_code == 403  # draft is private
    assert client.post(f"/proiecte/{pid}/publica", headers=h(town["v1"])).status_code == 403
    r = client.post(f"/proiecte/{pid}/publica", headers=h(town["author"]))
    assert r.status_code == 200 and r.json()["stare"] == "publicat"
    assert pid in {x["id"] for x in client.get("/proiecte/publice").json()}
    assert client.get(f"/proiecte/{pid}").status_code == 200  # anyone can read it now
    v = client.post(f"/proiecte/{pid}/vot", headers=h(town["v1"]))
    assert v.status_code == 201 and v.json()["voturi"] == 1 and v.json()["stare"] == "publicat"
    assert client.post(f"/proiecte/{pid}/vot", headers=h(town["v1"])).status_code == 409  # one vote per user
    assert client.get(f"/proiecte/{pid}", headers=h(town["v1"])).json()["votat_de_mine"] is True
    assert client.get(f"/proiecte/{pid}", headers=h(town["v2"])).json()["votat_de_mine"] is False
    client.post(f"/proiecte/{pid}/vot", headers=h(town["v2"]))
    third = client.post(f"/proiecte/{pid}/vot", headers=h(town["other"]))
    assert third.json()["voturi"] == 3 and third.json()["stare"] == "trimis"  # threshold reached -> city hall
    detail = client.get(f"/proiecte/{pid}", headers=h(town["prim"])).json()
    assert [e["stare_noua"] for e in detail["evenimente"]] == ["draft", "publicat", "trimis"]
    assert pid in {x["id"] for x in client.get("/proiecte", headers=h(town["prim"])).json()}
    assert any(n["proiect_id"] == pid for n in client.get("/notifications", headers=h(town["prim"])).json())
    assert any("susținători" in n["mesaj"] for n in client.get("/notifications", headers=h(town["author"])).json())
    # the rest of the chain, persisted
    assert client.post(f"/proiecte/{pid}/inainteaza", json={"verificator_id": town["ver"]}, headers=h(town["prim"])).status_code == 200
    assert client.post(f"/proiecte/{pid}/vot", headers=h(town["prim"])).status_code == 201  # voting stays open in verification
    dec = client.post(f"/proiecte/{pid}/decizie", json={"stare": "acord_de_principiu"}, headers=h(town["ver"]))
    assert dec.status_code == 200
    assert client.post(f"/proiecte/{pid}/vot", headers=h(town["ver"])).status_code == 409  # decided: votes closed
    assert any(n["proiect_id"] == pid and "acord" in n["mesaj"] for n in client.get("/notifications", headers=h(town["v1"])).json())


def test_impact_counts_community(client, town):
    pid = _ev(client, town)["id"]
    client.post(f"/proiecte/{pid}/publica", headers=h(town["author"]))
    client.post(f"/proiecte/{pid}/vot", headers=h(town["v1"]))
    imp = client.get("/impact").json()
    assert imp["proiecte_propuse"] >= 1 and imp["proiecte_publicate"] == 1 and imp["voturi_total"] == 1
    assert imp["oameni_implicati"] >= 2 and imp["terenuri_libere"] == 2
