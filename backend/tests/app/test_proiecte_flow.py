"""State machine, roles and listing of 'Propunere catre Primarie'."""
from datetime import date

import pytest
from sqlmodel import select

from backend.app import p3
from backend.app.models import Idea, ProiectEveniment, Space, User
from backend.app.schemas import Referinta
from backend.tests.app.conftest import h


@pytest.fixture
def people(session, world):
    session.add_all([
        User(id="u-prim", nume="Primăria", rol="primarie", cartier="-", lat=44.43, lng=26.10),
        User(id="u-prim2", nume="Primăria 2", rol="primarie", cartier="-", lat=44.43, lng=26.10),
        User(id="u-ver", nume="Verificator", rol="verificator", cartier="-", lat=44.43, lng=26.10),
        User(id="u-ver2", nume="Verificator 2", rol="verificator", cartier="-", lat=44.43, lng=26.10),
    ])
    session.get(Space, "s1").suprafata_mp = 1000
    session.commit()
    return {**world, "prim": "u-prim", "prim2": "u-prim2", "ver": "u-ver", "ver2": "u-ver2"}


def make(client, w, **kw):
    r = client.post("/ideas/i1/proiect", json={"space_id": "s1", "tip_amenajare": "skatepark", **kw}, headers=h(w["author"]))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def go(client, pid, action, user, body=None):
    return client.post(f"/proiecte/{pid}/{action}", json=body or {}, headers=h(user))


def to_verification(client, w):
    pid = make(client, w)
    assert go(client, pid, "trimite", w["author"], {"mesaj": "Vă rog analizați"}).status_code == 200
    assert go(client, pid, "inainteaza", w["prim"], {"verificator_id": w["ver"]}).status_code == 200
    return pid


# ---- creation --------------------------------------------------------------
def test_create_rules(client, session, people):
    body = {"space_id": "s1", "tip_amenajare": "skatepark"}
    assert client.post("/ideas/i1/proiect", json=body, headers=h(people["other"])).status_code == 403
    idea = session.get(Idea, "i1")
    idea.stare = "deschisa"
    session.add(idea)
    session.commit()
    assert client.post("/ideas/i1/proiect", json=body, headers=h(people["author"])).status_code == 409
    idea.stare = "rezervata"
    session.add(idea)
    session.commit()
    assert client.post("/ideas/i1/proiect", json=body, headers=h(people["author"])).status_code == 201


def test_create_writes_draft_event(client, session, people):
    pid = make(client, people)
    ev = session.exec(select(ProiectEveniment).where(ProiectEveniment.proiect_id == pid)).all()
    assert [e.stare_noua for e in ev] == ["draft"]


def test_cost_insufficient_when_few_references(client, monkeypatch, people):
    one = [Referinta(id="r1", tip_amenajare="skatepark", oras="X", an=2022, suprafata_mp=900, cost_total_lei=500000,
                     sursa_url="https://e.x", sursa_tip="primarie", data_accesarii=date.today())]
    monkeypatch.setattr(p3, "find_references", lambda *a, **k: one)
    pid = make(client, people)
    cost = client.get(f"/proiecte/{pid}", headers=h(people["author"])).json()["cost"]
    assert cost["suficient"] is False and cost["motiv"] and cost["mediana_lei"] is None


def test_surface_from_request_overrides_space(client, people):
    pid = make(client, people, suprafata_mp=2500)
    assert client.get(f"/proiecte/{pid}", headers=h(people["author"])).json()["suprafata_mp"] == 2500


# ---- full happy path with events and notifications -------------------------
def test_full_flow_acord(client, people):
    pid = to_verification(client, people)
    r = go(client, pid, "decizie", people["ver"], {"stare": "acord_de_principiu"})
    assert r.status_code == 200 and r.json()["stare"] == "acord_de_principiu"
    detail = client.get(f"/proiecte/{pid}", headers=h(people["author"])).json()
    assert [e["stare_noua"] for e in detail["evenimente"]] == ["draft", "trimis", "in_verificare", "acord_de_principiu"]
    assert detail["verificator_id"] == people["ver"]
    for uid in (people["author"], people["prim"], people["prim2"]):
        notes = client.get("/notifications", headers=h(uid)).json()
        assert any(n["proiect_id"] == pid and "acord de principiu" in n["mesaj"] for n in notes)
    assert any(n["proiect_id"] == pid for n in client.get("/notifications", headers=h(people["ver"])).json())
    imp = client.get("/impact").json()
    assert imp["proiecte_trimise"] == 1 and imp["proiecte_cu_acord"] == 1


def test_send_notifies_all_primarie(client, people):
    pid = make(client, people)
    go(client, pid, "trimite", people["author"])
    for uid in (people["prim"], people["prim2"]):
        assert len(client.get("/notifications", headers=h(uid)).json()) == 1


def test_clarificari_then_resend(client, people):
    pid = to_verification(client, people)
    assert go(client, pid, "decizie", people["ver"], {"stare": "clarificari", "mesaj": "Lipsește planul"}).status_code == 200
    assert go(client, pid, "trimite", people["author"], {"mesaj": "Completat"}).json()["stare"] == "trimis"


def test_respins_is_final(client, people):
    pid = to_verification(client, people)
    assert go(client, pid, "decizie", people["ver"], {"stare": "respins", "mesaj": "Nu"}).status_code == 200
    assert go(client, pid, "trimite", people["author"]).status_code == 409
    assert go(client, pid, "decizie", people["ver"], {"stare": "acord_de_principiu"}).status_code == 409


# ---- roles (403) -----------------------------------------------------------
def test_trimite_only_author(client, people):
    pid = make(client, people)
    assert go(client, pid, "trimite", people["other"]).status_code == 403
    assert go(client, pid, "trimite", people["prim"]).status_code == 403


def test_inainteaza_only_primarie(client, people):
    pid = make(client, people)
    go(client, pid, "trimite", people["author"])
    for uid in (people["author"], people["ver"], people["other"]):
        assert go(client, pid, "inainteaza", uid, {"verificator_id": people["ver"]}).status_code == 403


def test_decizie_only_designated_verifier(client, people):
    pid = to_verification(client, people)
    for uid in (people["ver2"], people["prim"], people["author"]):
        assert go(client, pid, "decizie", uid, {"stare": "acord_de_principiu"}).status_code == 403


# ---- wrong state (409) and validation (422) --------------------------------
def test_wrong_states(client, people):
    pid = make(client, people)
    assert go(client, pid, "inainteaza", people["prim"], {"verificator_id": people["ver"]}).status_code == 409  # draft
    go(client, pid, "trimite", people["author"])
    assert go(client, pid, "trimite", people["author"]).status_code == 409  # already sent
    go(client, pid, "inainteaza", people["prim"], {"verificator_id": people["ver"]})
    assert go(client, pid, "inainteaza", people["prim"], {"verificator_id": people["ver"]}).status_code == 409


def test_inainteaza_requires_real_verifier(client, people):
    pid = make(client, people)
    go(client, pid, "trimite", people["author"])
    assert go(client, pid, "inainteaza", people["prim"], {"verificator_id": people["other"]}).status_code == 422
    assert go(client, pid, "inainteaza", people["prim"], {"verificator_id": "nimeni"}).status_code == 422


def test_decizie_needs_message_for_respins_and_clarificari(client, people):
    pid = to_verification(client, people)
    for stare in ("respins", "clarificari"):
        assert go(client, pid, "decizie", people["ver"], {"stare": stare}).status_code == 422
        assert go(client, pid, "decizie", people["ver"], {"stare": stare, "mesaj": "  "}).status_code == 422


# ---- listing by role -------------------------------------------------------
def test_list_by_role(client, people):
    draft = make(client, people)
    sent = make(client, people)
    go(client, sent, "trimite", people["author"])

    def ids(uid):
        return {p["id"] for p in client.get("/proiecte", headers=h(uid)).json()}

    assert ids(people["author"]) == {draft, sent}
    assert ids(people["other"]) == set()
    assert ids(people["prim"]) == {sent}  # no drafts
    assert ids(people["ver"]) == set()
    go(client, sent, "inainteaza", people["prim"], {"verificator_id": people["ver"]})
    assert ids(people["ver"]) == {sent} and ids(people["ver2"]) == set()


def test_detail_visibility(client, people):
    pid = make(client, people)
    assert client.get(f"/proiecte/{pid}", headers=h(people["other"])).status_code == 403
    assert client.get(f"/proiecte/{pid}", headers=h(people["prim"])).status_code == 403  # draft is private
    go(client, pid, "trimite", people["author"])
    assert client.get(f"/proiecte/{pid}", headers=h(people["prim"])).status_code == 200
