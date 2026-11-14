import pytest

from backend.ai.costs import MIN_REFERENCES, estimate_cost
from backend.ai.references import Referinta


def _r(rid, area, cost, an=2020, oras="Sibiu", sursa_tip="presa"):
    return Referinta(id=rid, tip_amenajare="skatepark", oras=oras, an=an, suprafata_mp=area, cost_total_lei=cost,
                     componente=[], sursa_url="https://exemplu.ro/x", sursa_tip=sursa_tip,
                     data_accesarii="2026-11-14")


def test_min_median_max_per_mp_times_area():
    # 1000, 2000 and 3000 lei/mp; 50 mp proposed
    refs = [_r("a", 100, 100_000), _r("b", 200, 400_000, an=2023, oras="Iași"), _r("c", 300, 900_000, an=2018)]
    c = estimate_cost(refs, 50)
    assert c.suficient is True and c.moneda == "RON" and c.motiv is None
    assert (c.min_lei, c.mediana_lei, c.max_lei) == (50_000, 100_000, 150_000)
    assert c.referinte_folosite == ["a", "b", "c"]
    assert c.ipoteze[0] == "Bazat pe 3 proiecte de referință din anii 2018–2023 (Sibiu, Iași)."
    assert any("inflație" in i for i in c.ipoteze)


def test_even_count_median_and_rounding():
    c = estimate_cost([_r("a", 1000, 1_000_000), _r("b", 1000, 2_000_000)], 333)
    assert c.min_lei == 333_000 and c.max_lei == 666_000 and c.mediana_lei == 499_500


def test_rounds_to_hundreds():
    c = estimate_cost([_r("a", 3, 1000), _r("b", 3, 1000)], 10)  # 333.33 lei/mp * 10 = 3333.33
    assert c.min_lei == c.max_lei == 3300


def test_only_references_with_cost_and_area_count():
    refs = [_r("a", 100, 100_000), _r("no-area", None, 500_000), _r("no-cost", 100, None), _r("b", 100, 300_000)]
    c = estimate_cost(refs, 100)
    assert c.referinte_folosite == ["a", "b"] and (c.min_lei, c.max_lei) == (100_000, 300_000)


@pytest.mark.parametrize("refs", [[], [_r("a", 100, 100_000)], [_r("a", 100, 100_000), _r("b", None, 5)]])
def test_insufficient_has_no_figures(refs):
    c = estimate_cost(refs, 100)
    assert c.suficient is False and (c.min_lei, c.mediana_lei, c.max_lei) == (None, None, None)
    assert c.ipoteze == [] and (f"cel puțin {MIN_REFERENCES}" in c.motiv or "Niciun proiect" in c.motiv)


def test_missing_area_is_insufficient():
    c = estimate_cost([_r("a", 100, 1), _r("b", 100, 2)], None)
    assert c.suficient is False and "Suprafața" in c.motiv


def test_accepts_dicts_and_flags_live_sources():
    refs = [_r("a", 100, 100_000).model_dump(), _r("b", 100, 200_000, sursa_tip="cautare_ai_verificata")]
    c = estimate_cost(refs, 10)
    assert c.suficient and any("căutare automată" in i for i in c.ipoteze)


def test_real_base_skatepark():
    from backend.ai.references import find_references

    c = estimate_cost(find_references("skatepark", 600), 600)
    assert c.suficient and 0 < c.min_lei <= c.mediana_lei <= c.max_lei
