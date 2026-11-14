"""Any community proposal -> type -> references -> cost -> dossier. Offline: Gemini is faked or absent."""
import json

import pytest

from backend.ai import proposal
from backend.ai.proiect import DISCLAIMER, money_mentions
from backend.ai.proposal import classify_proposal, prepare_proiect

SPACE = {"id": "t1", "name": "Teren liber (exemplu)", "kind": "teren_liber", "neighborhood": "Fabric"}


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")


@pytest.mark.parametrize("text, tip, label", [
    ("Vrem un aquapark pentru copiii din cartier, cu tobogane de apă", "aquapark", "parc acvatic"),
    ("O fântână arteziană în Piața Mărăști", "fantana_arteziana", "fântână arteziană"),
    ("Bibliotecă stradală lângă stația de autobuz", "biblioteca_stradala", "bibliotecă stradală"),
    ("Propunem un observator astronomic pe dealul din parc", "observator_astronomic", "observator astronomic"),
    ("Ne trebuie un parc pentru câini", "parc_caini", "parc pentru câini"),
    ("Foișor din lemn în parcul Rozelor", "foisor", "foișor"),
    ("Vreau un teren de baschet", "teren_sport", "teren de sport"),
    ("", "amenajare", "amenajare"),
])
def test_fallback_classifies_any_proposal(no_key, text, tip, label):
    c = classify_proposal(text)
    assert (c.tip_amenajare, c.eticheta, c.source) == (tip, label, "fallback")


def _fake_gemini(monkeypatch, answer):
    from backend.tests.ai.conftest import fake_chain

    return fake_chain(monkeypatch, "backend.ai.proposal", answer, tries=1)


def test_gemini_label_is_kept_and_synonyms_are_canonical(monkeypatch):
    _fake_gemini(monkeypatch, {"eticheta": "Patinoar în aer liber", "cuvinte_cautare": ["patinoar", "gheață"]})
    c = classify_proposal("iarna vrem să patinăm în cartier")
    assert (c.tip_amenajare, c.eticheta, c.source) == ("patinoar_in_aer_liber", "patinoar în aer liber", "llm")
    assert c.cuvinte_cautare == ["patinoar", "gheață"]
    _fake_gemini(monkeypatch, {"eticheta": "Loc de joacă pentru copii", "cuvinte_cautare": []})
    assert classify_proposal("ceva pentru copii").tip_amenajare == "loc_de_joaca"


def test_gemini_failure_uses_fallback(monkeypatch):
    _fake_gemini(monkeypatch, RuntimeError("429 RESOURCE_EXHAUSTED"))
    assert classify_proposal("Vrem un aquapark").source == "fallback"


def test_unknown_proposal_still_gets_a_full_dossier(no_key):
    p = prepare_proiect({"title": "Aquapark", "text": "Vrem un aquapark pentru copii, cu tobogane de apă."},
                        SPACE, 5000)
    assert p["tip_amenajare"] == "aquapark" and p["referinte"] == []
    assert p["cost"]["suficient"] is False and p["cost"]["motiv"]
    d = p["dosar"]
    assert "parc acvatic" in d["titlu"] and d["justificare"].endswith(DISCLAIMER)
    assert d["componente"] and d["etape"] and d["riscuri"] and d["lista_verificare"]
    assert money_mentions(json.dumps(d, ensure_ascii=False)) == []


def test_known_proposal_uses_local_references_and_cost(no_key):
    p = prepare_proiect({"title": "Skate", "text": "Un skatepark mic pentru adolescenți"}, SPACE, 600)
    assert p["tip_amenajare"] == "skatepark" and p["cost"]["suficient"] is True
    assert p["dosar"]["referinte_citate"] and set(p["dosar"]["referinte_citate"]) <= {r["id"] for r in p["referinte"]}


def test_explicit_type_skips_classification(no_key, monkeypatch):
    monkeypatch.setattr(proposal, "classify_proposal", lambda text: pytest.fail("type was given"))
    p = prepare_proiect({"text": "orice"}, SPACE, 500, tip_amenajare="Parc pentru câini")
    assert p["tip_amenajare"] == "parc_caini" and len(p["referinte"]) == 3


@pytest.mark.parametrize("text, label", [
    ("Vreau să se facă o stație de încărcare pentru mașini electrice", "stație de încărcare"),
    ("Ar fi bine să avem stații de încărcare pentru mașini electrice în cartier", "stații de încărcare"),
    ("Am vrea să se construiască o fântână în parc", "fântână"),
    ("Ne trebuie un adăpost pentru bicicliști", "adăpost"),
])
def test_request_wording_is_stripped(no_key, text, label):
    assert classify_proposal(text).eticheta == label


def test_template_fits_any_kind_of_project(no_key):
    p = prepare_proiect({"title": "Încărcare", "text": "Vreau să se facă o stație de încărcare pentru mașini electrice"},
                        SPACE, 150)
    text = json.dumps(p["dosar"], ensure_ascii=False)
    assert "stație de încărcare" in p["dosar"]["titlu"]
    assert "timpului liber" not in text and "bănci" not in text


def test_accepts_contract_shaped_ideas(no_key):
    """P1's Idea rows: titlu, descriere, interesati, structurat.rezumat."""
    idea = {"titlu": "Stație de încărcare", "descriere": "Vrem o stație de încărcare pentru mașini electrice.",
            "interesati": 7, "structurat": {"rezumat": "Stație de încărcare pentru mașini electrice"}}
    p = prepare_proiect(idea, {"nume": "Parcare (exemplu)", "cartier": "Fabric"}, 100)
    assert p["eticheta"] == "stație de încărcare"
    d = p["dosar"]
    assert "Parcare (exemplu)" in d["descriere"] and "susținută de 7 persoane" in d["justificare"]
