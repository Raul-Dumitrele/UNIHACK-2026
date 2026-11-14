"""Free plots search, project straight on a plot, plan / material list / documents (P3 functions, offline)."""
import pytest

from backend.app.models import Space, User
from backend.tests.app.conftest import h


@pytest.fixture
def plots(session, world):
    session.add_all([
        User(id="u-prim", nume="Primăria", rol="primarie", cartier="-", lat=44.43, lng=26.10),
        User(id="u-ver", nume="Verificator", rol="verificator", cartier="-", lat=44.43, lng=26.10),
        Space(id="t-mare", nume="Teren mare", tip="teren_liber", lat=45.75, lng=21.22, capacitate=0, dotari=[], sloturi=[],
              owner_id="u-prim", suprafata_mp=1200, cartier="Fabric", is_demo=True),
        Space(id="lista-2019-1", nume="Teren din lista Primăriei", tip="teren_liber", lat=45.76, lng=21.23, capacitate=0,
              dotari=[], sloturi=[], owner_id="u-prim", suprafata_mp=276, cartier="Fabric",
              sursa="lista_primarie", sursa_detalii="HCL 20/2019, anexa nr. 1"),
    ])
    session.commit()
    return world


def test_spaces_filter_by_tip_and_new_fields(client, plots):
    got = client.get("/spaces", params={"tip": "teren_liber"}).json()
    assert {s["id"] for s in got} == {"t-mare", "lista-2019-1"}
    listed = next(s for s in got if s["id"] == "lista-2019-1")
    assert listed["cartier"] == "Fabric" and listed["sursa_detalii"].startswith("HCL")


def test_terenuri_potrivite_ranked_with_reason(client, plots):
    r = client.get("/terenuri/potrivite", params={"tip_amenajare": "loc_de_joaca", "suprafata_minima": 200})
    assert r.status_code == 200
    got = r.json()
    assert {c["space_id"] for c in got} == {"t-mare", "lista-2019-1"}
    assert got == sorted(got, key=lambda c: c["scor"], reverse=True)
    for c in got:
        assert 0 <= c["scor"] <= 100 and c["motiv"]
    listed = next(c for c in got if c["space_id"] == "lista-2019-1")
    assert listed["din_lista_primarie"] is True and "Legea 15/2003" in listed["avertisment"]
    assert next(c for c in got if c["space_id"] == "t-mare")["avertisment"] is None


def test_terenuri_potrivite_excludes_small_plots(client, plots):
    got = client.get("/terenuri/potrivite", params={"tip_amenajare": "skatepark", "suprafata_minima": 400}).json()
    assert [c["space_id"] for c in got] == ["t-mare"]
    assert client.get("/terenuri/potrivite").status_code == 422  # tip_amenajare is required


def _direct(client, user, **kw):
    body = {"space_id": "t-mare", "tip_amenajare": "skatepark", "descriere": "Un skatepark pentru adolescenții din Fabric", **kw}
    return client.post("/proiecte", json=body, headers=h(user))


def test_post_proiecte_direct_on_plot(client, plots):
    r = _direct(client, plots["other"])
    assert r.status_code == 201
    p = r.json()
    assert p["stare"] == "draft" and p["autor_id"] == plots["other"] and p["suprafata_mp"] == 1200
    assert "acord de principiu simulat" in p["dosar"]["justificare"]
    assert [x["id"] for x in client.get("/proiecte", headers=h(plots["other"])).json()] == [p["id"]]
    assert _direct(client, plots["other"], suprafata_mp=900).json()["suprafata_mp"] == 900


def test_post_proiecte_errors(client, plots):
    assert client.post("/proiecte", json={"space_id": "t-mare", "tip_amenajare": "skatepark", "descriere": "x y z"}).status_code == 401
    assert _direct(client, plots["other"], space_id="nu-exista").status_code == 404
    assert _direct(client, plots["other"], descriere="").status_code == 422
    assert _direct(client, plots["other"], tip_amenajare="piscina").status_code == 422


def test_plan_materiale_and_documents(client, plots):
    pid = _direct(client, plots["other"]).json()["id"]
    plan = client.get(f"/proiecte/{pid}/plan", headers=h(plots["other"]))
    assert plan.status_code == 200
    body = plan.json()
    assert body["tip_amenajare"] == "skatepark" and body["suprafata_ocupata_mp"] > 0 and body["elemente"]
    mat = client.get(f"/proiecte/{pid}/materiale", headers=h(plots["other"])).json()
    assert mat["linii"] and "subtotal_cotat_lei" in mat and mat["disclaimer"]
    expected = {"plan.svg": ("image/svg+xml", b"<svg"), "plan.dxf": ("application/dxf", b"SECTION"),
                "dosar.pdf": ("application/pdf", b"%PDF"), "materiale.csv": ("text/csv", None)}
    for nume, (media, start) in expected.items():
        r = client.get(f"/proiecte/{pid}/documente/{nume}", headers=h(plots["other"]))
        assert r.status_code == 200, nume
        assert r.headers["content-type"].startswith(media)
        assert r.headers["content-disposition"] == f'attachment; filename="proiect-{pid}-{nume}"'
        if start:
            assert start in r.content[:400]
    assert client.get(f"/proiecte/{pid}/documente/altceva.zip", headers=h(plots["other"])).status_code == 404


def test_documents_follow_project_visibility(client, plots):
    pid = _direct(client, plots["other"]).json()["id"]
    for path in ("plan", "materiale", "documente/plan.svg"):
        assert client.get(f"/proiecte/{pid}/{path}", headers=h(plots["author"])).status_code == 403
        assert client.get(f"/proiecte/{pid}/{path}", headers=h("u-prim")).status_code == 403  # still a draft
        assert client.get(f"/proiecte/{pid}/{path}").status_code == 401
    client.post(f"/proiecte/{pid}/trimite", json={}, headers=h(plots["other"]))
    assert client.get(f"/proiecte/{pid}/plan", headers=h("u-prim")).status_code == 200
    assert client.get("/proiecte/nu-exista/plan", headers=h(plots["other"])).status_code == 404
