from types import SimpleNamespace

import pytest

from backend.ai import geo
from backend.ai.matching import WEIGHTS, canonical_needs, match_spaces, score_space, SpaceCandidate
from backend.ai.schemas import DossierBase
from backend.seed.build import build_seed, load_json

CETATE = (45.756038, 21.228846)


def dossier(**over):
    base = dict(title="Atelier", summary="", category="atelier", audience="vecini", expected_participants=15,
                duration_hours=2, needs=["mese", "priză"], setting="oricare", tags=[])
    return DossierBase(**{**base, **over})


def space(**over):
    base = dict(id="s1", name="Centrul X", kind="community_centre", capacity=30,
                amenities=["mese", "scaune", "priză"], setting="interior", lat=CETATE[0], lon=CETATE[1])
    return {**base, **over}


# --- geo ---

def test_distance_km_is_symmetric_and_plausible():
    fabric = geo.neighborhood_point("Fabric")
    d = geo.distance_km(CETATE, fabric)
    assert d == pytest.approx(geo.distance_km(fabric, CETATE))
    assert 1.0 < d < 2.5  # Cetate-Fabric is about 1.6 km
    assert geo.distance_km(CETATE, CETATE) == 0


def test_neighborhood_lookup_ignores_diacritics_and_case():
    assert geo.neighborhood_point("sagului") == geo.neighborhood_point("Șagului") is not None
    assert geo.neighborhood_point("Atlantida") is None
    assert geo.nearest_neighborhood(CETATE) == "Cetate"


def test_demo_users_live_in_known_neighborhoods():
    for user in load_json("demo.json")["users"]:
        assert geo.neighborhood_point(user["neighborhood"]) is not None, user


# --- needs ---

def test_canonical_needs_maps_synonyms_and_keeps_unknown():
    known, unknown = canonical_needs(["masă mare", "Videoproiector", "wifi", "ceai"])
    assert known == ["mese", "proiector", "wi-fi"]
    assert unknown == ["ceai"]


# --- scoring ---

def test_perfect_match_scores_100_and_explains():
    m = score_space(dossier(), SpaceCandidate(**space()), CETATE)
    assert m.score == 100
    assert m.reason.startswith("Încape 15 persoane (30 locuri)")
    assert "are mese, priză" in m.reason and "la 0,0 km, în Cetate" in m.reason
    assert m.missing_needs == []


def test_too_small_space_is_excluded():
    assert score_space(dossier(expected_participants=50), SpaceCandidate(**space(capacity=39))) is None


def test_slightly_small_space_gets_half_capacity_points():
    full = score_space(dossier(), SpaceCandidate(**space()))
    tight = score_space(dossier(expected_participants=35), SpaceCandidate(**space()))
    assert full.score - tight.score == WEIGHTS["capacity"] / 2
    assert "puțin sub" in tight.reason


def test_missing_needs_lower_score_and_are_listed():
    m = score_space(dossier(needs=["mese", "proiector"]), SpaceCandidate(**space()), CETATE)
    assert m.missing_needs == ["proiector"]
    assert "lipsește: proiector" in m.reason
    assert m.score == round(100 - WEIGHTS["needs"] / 2)


def test_unknown_needs_do_not_penalize_but_are_mentioned():
    m = score_space(dossier(needs=["ceai"]), SpaceCandidate(**space()), CETATE)
    assert m.score == 100
    assert "de verificat cu proprietarul: ceai" in m.reason


def test_setting_mismatch():
    m = score_space(dossier(setting="exterior"), SpaceCandidate(**space()), CETATE)
    assert m.score == 100 - WEIGHTS["setting"]
    assert "spațiu interior, ideea cere exterior" in m.reason


def test_unknown_distance_is_neutral():
    m = score_space(dossier(), SpaceCandidate(**space()), origin=None)
    assert m.distance_km is None and m.score == 100 - WEIGHTS["distance"] / 2


# --- ranking ---

def test_ranking_orders_by_score_then_distance_and_limits():
    near, far = space(id="near"), space(id="far", lat=45.70, lon=21.30)
    sport = space(id="sport", kind="sports_centre", amenities=["vestiar"])
    small = space(id="small", capacity=5)
    result = match_spaces(dossier(), [far, sport, small, near], origin="Cetate", limit=2)
    assert [m.space_id for m in result] == ["near", "far"]


def test_accepts_orm_like_objects_and_dict_dossier():
    obj = SimpleNamespace(**space())
    result = match_spaces(dossier().model_dump(mode="json") | {"source": "fallback"}, [obj])
    assert result[0].space_id == "s1"


def test_demo_ideas_get_relevant_matches():
    data = build_seed()
    users = {u["id"]: u for u in data.users}
    for idea in data.ideas:
        matches = match_spaces(idea["dossier"], data.spaces, users[idea["author_id"]]["neighborhood"])
        assert matches, idea["id"]
        assert matches[0].score >= 80
    sport = next(i for i in data.ideas if i["dossier"]["category"] == "sport")
    top = match_spaces(sport["dossier"], data.spaces)[0]
    assert next(s for s in data.spaces if s["id"] == top.space_id)["kind"] in {"sports_centre", "sports_hall"}
