import json

import pytest

from backend.ai.references import core, find_references, slugify
from backend.ai.references.validate import main as validate_main
from backend.ai.references.validate import validate

GOOD = {
    "id": "x-1", "tip_amenajare": "skatepark", "oras": "Sibiu", "an": 2020, "suprafata_mp": 1000,
    "cost_total_lei": 500000, "componente": ["rampe"], "sursa_url": "https://exemplu.ro/a",
    "sursa_tip": "presa", "data_accesarii": "2026-11-14",
}


def _ref(**over):
    return {**GOOD, **over}


def _write(folder, tip, entries):
    path = folder / f"{tip}.json"
    path.write_text(json.dumps({"tip_amenajare": tip, "referinte": entries}, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def base(tmp_path, monkeypatch):
    """Isolated reference folders; live search off unless a test turns it on."""
    data, cache = tmp_path / "data", tmp_path / "cache"
    data.mkdir()
    cache.mkdir()
    monkeypatch.setattr(core, "DATA_DIR", data)
    monkeypatch.setattr(core, "CACHE_DIR", cache)
    monkeypatch.setenv("REFERENCES_LIVE_SEARCH", "false")
    return data


# --- the committed base -------------------------------------------------------------------------

def test_committed_base_is_valid():
    report, rejected = validate()
    assert rejected == []
    for tip in ("skatepark", "loc_de_joaca", "pista_biciclete"):
        assert report[tip]["valide"] >= 4, tip
        assert report[tip]["cu_cost_si_suprafata"] >= 2, tip


def test_committed_entries_have_source_and_access_date():
    from datetime import date

    for path in core.data_files():
        valid, _ = core.read_file(path)
        for r in valid:
            assert r.sursa_url.startswith("http") and r.data_accesarii <= date.today(), r.id
            assert r.id.startswith(r.tip_amenajare + "-"), r.id


# --- validator ----------------------------------------------------------------------------------

@pytest.mark.parametrize("bad, reason", [
    (_ref(id="no-url", sursa_url=""), "sursa_url"),
    (_ref(id="neg-cost", cost_total_lei=-5), "cost_total_lei"),
    (_ref(id="zero-area", suprafata_mp=0), "suprafata_mp"),
    (_ref(id="no-date", data_accesarii=None), "data_accesarii"),
    (_ref(id="bad-source", sursa_tip="blog"), "sursa_tip"),
    (_ref(id="wrong-type", tip_amenajare="loc_de_joaca"), "diferă de fișier"),
])
def test_validator_rejects(tmp_path, bad, reason):
    valid, rejected = core.read_file(_write(tmp_path, "skatepark", [GOOD, bad]))
    assert [r.id for r in valid] == ["x-1"]
    assert len(rejected) == 1 and rejected[0][0] == bad["id"] and reason in rejected[0][1]


def test_validator_rejects_duplicate_ids(tmp_path):
    valid, rejected = core.read_file(_write(tmp_path, "skatepark", [GOOD, GOOD]))
    assert len(valid) == 1 and rejected == [("x-1", "id duplicat")]


def test_null_cost_and_area_are_valid_but_not_usable(tmp_path):
    valid, rejected = core.read_file(_write(tmp_path, "skatepark", [_ref(cost_total_lei=None, suprafata_mp=None)]))
    assert rejected == [] and valid[0].usable_for_cost is False


def test_validate_command_exit_code(tmp_path, monkeypatch, capsys):
    good = _write(tmp_path, "skatepark", [GOOD])
    monkeypatch.setattr("backend.ai.references.validate.data_files", lambda: [good])
    assert validate_main() == 0
    bad = _write(tmp_path, "loc_de_joaca", [_ref(id="b", tip_amenajare="loc_de_joaca", an=1800)])
    monkeypatch.setattr("backend.ai.references.validate.data_files", lambda: [good, bad])
    assert validate_main() == 1
    assert "loc_de_joaca.json / b" in capsys.readouterr().out


# --- find_references ----------------------------------------------------------------------------

def test_slugify():
    assert slugify("Loc de joacă") == "loc_de_joaca"
    assert slugify("  Foișor de lemn! ") == "foisor_de_lemn"
    assert slugify("") == ""


def test_closest_area_first_and_k(base):
    _write(base, "skatepark", [
        _ref(id="a", suprafata_mp=5000), _ref(id="b", suprafata_mp=900), _ref(id="c", suprafata_mp=2000),
        _ref(id="d", suprafata_mp=None),
    ])
    assert [r.id for r in find_references("skatepark", 1000)] == ["b", "c", "a", "d"]
    assert [r.id for r in find_references("skatepark", 1000, k=2)] == ["b", "c"]


def test_ties_newer_year_then_city_size(base):
    _write(base, "skatepark", [
        _ref(id="old", an=2015, oras="Sibiu"),
        _ref(id="new-small", an=2022, oras="Carei"),
        _ref(id="new-big", an=2022, oras="Cluj-Napoca"),  # closest in size to Timișoara
        _ref(id="new-unknown", an=2022, oras="Galda de Jos"),
    ])
    assert [r.id for r in find_references("skatepark", 1000)] == ["new-big", "new-small", "new-unknown", "old"]


def test_free_text_type_and_unknown_type(base):
    _write(base, "loc_de_joaca", [_ref(id="l", tip_amenajare="loc_de_joaca")])
    assert [r.id for r in find_references("Loc de joacă", 500)] == ["l"]
    assert find_references("foișor", 50) == []
    assert find_references("", 50) == []


def test_cache_entries_are_merged(base):
    _write(base, "foisor", [_ref(id="hand", tip_amenajare="foisor")])
    _write(core.CACHE_DIR, "foisor", [_ref(id="hand", tip_amenajare="foisor"),
                                      _ref(id="live", tip_amenajare="foisor", sursa_tip="cautare_ai")])
    assert sorted(r.id for r in find_references("foisor", 1000)) == ["hand", "live"]


def test_live_search_on_by_default_with_a_key(base, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("REFERENCES_LIVE_SEARCH", raising=False)
    called = []
    monkeypatch.setattr("backend.ai.references.search.search_references", lambda tip: called.append(tip) or [])
    assert find_references("Parc acvatic", 5000) == [] and called == ["Parc acvatic"]


def test_live_search_can_be_turned_off(base, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("REFERENCES_LIVE_SEARCH", "false")
    monkeypatch.setattr("backend.ai.references.search.search_references",
                        lambda tip: pytest.fail("live search is off"))
    assert find_references("foisor", 50) == []


@pytest.mark.parametrize("text, tip", [
    ("parc pentru câini", "parc_caini"), ("Loc de joacă pentru copii", "loc_de_joaca"),
    ("aqua park", "aquapark"), ("tobogane cu apă", "aquapark"), ("pistă pentru biciclete", "pista_biciclete"),
    ("teren de baschet", "teren_sport"), ("Fântână arteziană", "fantana_arteziana"), ("parc_caini", "parc_caini"),
])
def test_canonical_type(text, tip):
    from backend.ai.references import canonical_type

    assert canonical_type(text) == tip


def test_synonyms_reach_the_same_file(base):
    _write(base, "parc_caini", [_ref(id="c", tip_amenajare="parc_caini")])
    assert [r.id for r in find_references("Parc pentru câini", 500)] == ["c"]


def test_label_for():
    from backend.ai.references.core import label_for

    assert label_for("loc_de_joaca") == "loc de joacă"
    assert label_for("Fântână arteziană") == "fântână arteziană"
    assert label_for("bazin_de_inot") == "bazin de inot"
    assert label_for("") == "amenajare"


def test_live_search_needs_a_key(base, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("REFERENCES_LIVE_SEARCH", "true")
    monkeypatch.setattr("backend.ai.references.search.search_references",
                        lambda tip: pytest.fail("no key, no live search"))
    assert find_references("foisor", 50) == []


def test_live_search_tops_up_thin_base(base, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("REFERENCES_LIVE_SEARCH", "true")
    _write(base, "foisor", [_ref(id="hand", tip_amenajare="foisor")])
    live = core.Referinta.model_validate(_ref(id="live", tip_amenajare="foisor", sursa_tip="cautare_ai_verificata"))
    called = []
    monkeypatch.setattr("backend.ai.references.search.search_references", lambda tip: called.append(tip) or [live])
    assert sorted(r.id for r in find_references("foisor", 1000)) == ["hand", "live"]
    assert called == ["foisor"]


def test_live_search_skipped_when_base_is_enough(base, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("REFERENCES_LIVE_SEARCH", "true")
    _write(base, "skatepark", [_ref(id="a"), _ref(id="b")])
    monkeypatch.setattr("backend.ai.references.search.search_references",
                        lambda tip: pytest.fail("live search must not run"))
    assert len(find_references("skatepark", 1000)) == 2
