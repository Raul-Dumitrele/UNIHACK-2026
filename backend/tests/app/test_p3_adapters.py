"""P3 integration seam: real modules may differ from the contract; P1 adapts them."""
from backend.app import p3
from backend.app.schemas import Structurat


def test_idea_dossier_is_converted_to_structurat():
    dossier = {
        "title": "Club de șah pentru copii", "summary": "x", "category": "educatie", "audience": "copii",
        "expected_participants": 12, "duration_hours": 2.0, "needs": ["mese", "scaune", "ceai"],
        "setting": "interior", "tags": [], "source": "fallback",
    }
    s = p3._to_structurat(dossier, "text")
    assert isinstance(s, Structurat)
    assert s.categorie == "educatie" and s.persoane == 12 and set(s.dotari) == {"mese", "scaune"}
    assert s.rezumat == "Club de șah pentru copii"


def test_unknown_category_falls_back_to_altele():
    s = p3._to_structurat({"title": "t", "category": "mediu", "expected_participants": 0, "needs": []}, "t")
    assert s.categorie == "altele" and s.persoane == 1


def test_contract_shaped_result_passes_through():
    st = Structurat(categorie="sport", persoane=5, zgomot="scazut", rezumat="r")
    assert p3._to_structurat(st, "t") is st
    assert p3._to_structurat(st.model_dump(), "t").categorie == "sport"


def test_compute_impact_falls_back_to_local(session):
    assert p3.compute_impact(session).proiecte_trimise == 0
