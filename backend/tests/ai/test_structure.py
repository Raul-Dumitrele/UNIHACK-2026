import json

import pytest

from backend.ai import Category, IdeaDossier, Setting, structure_idea
from backend.ai import gemini
from backend.ai.fallback import build_fallback, normalize

BIKES = (
    "Vreau să organizez un atelier de reparat biciclete pentru vecini, sâmbăta dimineața, "
    "cam 15 oameni, 3 ore. Avem nevoie de mese și o priză."
)

GOOD = {
    "title": "Atelier de reparat biciclete",
    "summary": "Vecinii își repară bicicletele împreună.",
    "category": "atelier",
    "audience": "vecinii din cartier",
    "expected_participants": 15,
    "duration_hours": 3,
    "needs": ["mese", "priză"],
    "setting": "interior",
    "tags": ["biciclete", "reparații"],
}


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")


@pytest.fixture
def fake_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")


def _gemini_returns(monkeypatch, result):
    calls = []

    def fake(settings, prompt):
        calls.append((settings.gemini_model, prompt))
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(gemini, "_generate", fake)
    return calls


# --- fallback (the common path) ---

def test_without_key_uses_fallback(no_key, monkeypatch):
    calls = _gemini_returns(monkeypatch, AssertionError("must not call Gemini"))
    d = structure_idea(BIKES)
    assert isinstance(d, IdeaDossier)
    assert d.source == "fallback"
    assert calls == []


def test_fallback_extracts_fields(no_key):
    d = structure_idea(BIKES)
    assert d.category is Category.atelier
    assert d.expected_participants == 15
    assert d.duration_hours == 3.0
    assert d.needs == ["mese", "priză"]
    assert d.audience == "vecinii din cartier"
    assert d.title == "Atelier de reparat biciclete pentru vecini"
    assert d.tags[0] == "atelier" and "biciclete" in d.tags


def test_fallback_is_deterministic(no_key):
    assert structure_idea(BIKES) == structure_idea(BIKES)


@pytest.mark.parametrize(
    ("text", "category", "setting"),
    [
        ("Turneu de șah pentru seniori în sala bibliotecii", Category.sport, Setting.interior),
        ("Proiecție de film în aer liber, în parcul din cartier", Category.cultura, Setting.exterior),
        ("Curs de programare pentru copii, avem nevoie de proiector și wifi", Category.educatie, Setting.oricare),
        ("Plantăm flori și facem compost în grădina blocului", Category.mediu, Setting.exterior),
        ("Ceva frumos împreună", Category.altele, Setting.oricare),
    ],
)
def test_fallback_categories(text, category, setting):
    d = build_fallback(text)
    assert (d.category, d.setting) == (category, setting)


def test_fallback_without_diacritics_matches_with_diacritics():
    plain = build_fallback("Atelier de reparat biciclete, avem nevoie de priza si mese")
    accented = build_fallback("Atelier de reparat biciclete, avem nevoie de priză și mese")
    assert plain.needs == accented.needs == ["mese", "priză"]


def test_no_false_positive_keywords():
    d = build_fallback("Întâlnire cu un meșter în apartamentul de lângă parcare")
    assert d.needs == ["parcare"]
    assert d.setting is Setting.oricare


def test_empty_text_never_raises(fake_key, monkeypatch):
    calls = _gemini_returns(monkeypatch, AssertionError("must not call Gemini"))
    d = structure_idea("   ")
    assert d.source == "fallback" and d.title == "Idee nouă"
    assert calls == []


def test_long_title_is_clipped():
    d = build_fallback("Vreau să organizez " + "o întâlnire foarte lungă " * 20)
    assert len(d.title) <= 81


def test_normalize_handles_cedilla_variants():
    assert normalize("Şcoală ţară ȘȚ") == "scoala tara st"


# --- Gemini path (mocked, no network) ---

def test_gemini_success(fake_key, monkeypatch):
    calls = _gemini_returns(monkeypatch, json.dumps(GOOD))
    d = structure_idea(BIKES)
    assert d.source == "gemini"
    assert d.title == "Atelier de reparat biciclete"
    assert calls[0][0] == "test-model"
    assert BIKES in calls[0][1]


@pytest.mark.parametrize(
    "result",
    [
        TimeoutError("deadline"),
        RuntimeError("429 RESOURCE_EXHAUSTED"),
        "not json",
        json.dumps({**GOOD, "category": "necunoscut"}),
        json.dumps({**GOOD, "title": "   "}),
        "",
    ],
)
def test_gemini_failures_fall_back(fake_key, monkeypatch, result):
    _gemini_returns(monkeypatch, result)
    d = structure_idea(BIKES)
    assert d.source == "fallback"
    assert d == IdeaDossier(**build_fallback(BIKES).model_dump(), source="fallback")


def test_gemini_values_are_clamped(fake_key, monkeypatch):
    _gemini_returns(monkeypatch, json.dumps({**GOOD, "expected_participants": 99999, "duration_hours": 0,
                                             "needs": ["Mese", "mese", ""] + [f"x{i}" for i in range(20)]}))
    d = structure_idea(BIKES)
    assert d.source == "gemini"
    assert d.expected_participants == 500
    assert d.duration_hours == 0.5
    assert d.needs[0] == "mese" and len(d.needs) == 10


def test_default_model_when_env_blank(monkeypatch):
    from backend.ai.config import DEFAULT_MODEL, MIN_TIMEOUT_MS, get_settings

    monkeypatch.setenv("GEMINI_MODEL", " ")
    monkeypatch.setenv("GEMINI_TIMEOUT_MS", "500")
    s = get_settings()
    assert s.gemini_model == DEFAULT_MODEL
    assert s.gemini_timeout_ms == MIN_TIMEOUT_MS
