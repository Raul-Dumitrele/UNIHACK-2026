import json

import pytest

from backend.ai import proiect
from backend.ai.costs import Cost, estimate_cost
from backend.ai.proiect import (
    BASE_CHECKS,
    DISCLAIMER,
    cost_sentence,
    generate_dosar,
    money_mentions,
)
from backend.ai.references import Referinta

IDEA = {"id": "i8", "title": "Skatepark în Fabric", "interest_count": 12,
        "text": "Vrem un skatepark mic pentru adolescenți. Am strâns deja 5.000 lei de la vecini.",
        "dossier": {"summary": "Un skatepark mic pentru adolescenții din cartier.", "audience": "adolescenți"}}
SPACE = {"id": "t1", "name": "Teren liber (exemplu)", "kind": "teren_liber", "neighborhood": "Fabric"}


def _r(rid, area, cost):
    return Referinta(id=rid, tip_amenajare="skatepark", oras="Sibiu", an=2020, suprafata_mp=area,
                     cost_total_lei=cost, componente=["rampe", "bănci"], sursa_url="https://exemplu.ro/x",
                     sursa_tip="presa", data_accesarii="2026-11-14")


REFS = [_r("ref-a", 1000, 1_000_000), _r("ref-b", 2000, 3_000_000), _r("ref-c", None, None)]
COST = estimate_cost(REFS, 600)  # 600k .. 900k lei, median 750k
GOOD = {
    "titlu": "Skatepark pe terenul liber din Fabric",
    "descriere": "Un skatepark de cartier cu rampe mici, pentru adolescenți.",
    "justificare": "Tinerii din Fabric nu au un loc dedicat sporturilor urbane.",
    "componente": ["rampe modulare", "bănci", "iluminat"],
    "etape": [{"nume": "Proiectare", "durata_luni": 3}, {"nume": "Execuție", "durata_luni": 5}],
    "riscuri": ["Zgomot pentru vecini."],
    "lista_verificare": ["Cine administrează terenul"],
    "referinte_citate": ["ref-a", "inventat-1"],
}


def _gemini(monkeypatch, *answers):
    """Fake key and a scripted Gemini: each call returns the next answer (dict, str or exception)."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    prompts = []

    def fake(settings, prompt):
        prompts.append(prompt)
        answer = answers[min(len(prompts), len(answers)) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)

    monkeypatch.setattr(proiect, "_generate", fake)
    return prompts


def _all_text(d) -> str:
    return "\n".join([d.titlu, d.descriere, d.justificare, *d.componente, *d.riscuri, *d.lista_verificare,
                      *(e.nume for e in d.etape)])


def _assert_only_injected_money(d, cost: Cost):
    """Every amount of money in the dossier comes from the code-inserted cost sentence."""
    assert sorted(money_mentions(_all_text(d))) == sorted(money_mentions(cost_sentence(cost)))


@pytest.mark.parametrize("text", ["250.000 lei", "costă 1,2 milioane euro", "RON 5000", "€300", "3 mii de lei",
                                  "11 mil. lei", "2.500.000,00 RON"])
def test_money_detected(text):
    assert money_mentions(text)


@pytest.mark.parametrize("text", ["o suprafață de 400 mp", "durează 3 luni", "12 persoane", "leilor", "anul 2024"])
def test_not_money(text):
    assert money_mentions(text) == []


def test_template_without_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    d = generate_dosar(IDEA, SPACE, "skatepark", 600, REFS, COST)
    assert d.descriere.endswith(DISCLAIMER)
    assert d.justificare.endswith(cost_sentence(COST))
    assert "600.000" in d.justificare and "900.000" in d.justificare
    assert "5.000 lei" not in _all_text(d)  # money from the idea text is not copied
    _assert_only_injected_money(d, COST)
    assert set(BASE_CHECKS) <= set(d.lista_verificare)
    assert d.referinte_citate == ["ref-a", "ref-b", "ref-c"]
    assert [e.nume for e in d.etape][0].startswith("Clarificări")


def test_template_with_insufficient_cost(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    cost = estimate_cost([_r("ref-a", 1000, 1_000_000)], 600)
    d = generate_dosar(IDEA, SPACE, "foișor", 50, [], cost)
    assert "nu poate fi estimat" in d.justificare and money_mentions(_all_text(d)) == []
    assert d.referinte_citate == [] and d.componente and d.descriere.endswith(DISCLAIMER)
    assert "foisor" not in d.titlu and "foișor" in d.titlu


def test_gemini_answer_is_used_and_finalized(monkeypatch):
    prompts = _gemini(monkeypatch, GOOD)
    d = generate_dosar(IDEA, SPACE, "skatepark", 600, REFS, COST)
    assert len(prompts) == 1
    assert d.titlu == GOOD["titlu"]
    assert d.referinte_citate == ["ref-a"]  # ids not in the input are dropped
    assert d.descriere.endswith(DISCLAIMER) and d.justificare.endswith(cost_sentence(COST))
    assert set(BASE_CHECKS) <= set(d.lista_verificare) and "Cine administrează terenul" in d.lista_verificare
    _assert_only_injected_money(d, COST)


def test_gemini_never_sees_cost_figures(monkeypatch):
    prompts = _gemini(monkeypatch, GOOD)
    generate_dosar(IDEA, SPACE, "skatepark", 600, REFS, COST)
    data = prompts[0].split("<<<DATE", 1)[1]
    assert "600000" not in data and "900000" not in data and "750000" not in data
    assert '"cost_disponibil": true' in data
    assert "1000000" not in data  # reference costs are not shown either


def test_money_in_answer_is_rejected_then_retried(monkeypatch):
    bad = {**GOOD, "justificare": "Ar costa în jur de 300.000 lei, ca la Sibiu."}
    prompts = _gemini(monkeypatch, bad, GOOD)
    d = generate_dosar(IDEA, SPACE, "skatepark", 600, REFS, COST)
    assert len(prompts) == 2 and d.titlu == GOOD["titlu"]
    _assert_only_injected_money(d, COST)


def test_money_twice_falls_back_to_template(monkeypatch):
    bad = {**GOOD, "componente": ["rampe de 50.000 euro"]}
    prompts = _gemini(monkeypatch, bad, bad)
    d = generate_dosar(IDEA, SPACE, "skatepark", 600, REFS, COST)
    assert len(prompts) == 2 and d.titlu.startswith("Amenajare:")
    _assert_only_injected_money(d, COST)


@pytest.mark.parametrize("first", [RuntimeError("429 RESOURCE_EXHAUSTED"), "{not json", {"titlu": ""}])
def test_errors_retry_once_then_template(monkeypatch, first):
    prompts = _gemini(monkeypatch, first, first)
    d = generate_dosar(IDEA, SPACE, "skatepark", 600, REFS, COST)
    assert len(prompts) == 2 and d.titlu.startswith("Amenajare:")


def test_error_then_success(monkeypatch):
    prompts = _gemini(monkeypatch, TimeoutError("slow"), GOOD)
    assert generate_dosar(IDEA, SPACE, "skatepark", 600, REFS, COST).titlu == GOOD["titlu"] and len(prompts) == 2


def test_accepts_dicts_and_orm_like_objects(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")

    class Row:
        title, text, interest_count, structurat = "Idee", "Text", 3, {"summary": "Rezumat"}

    d = generate_dosar(Row(), SPACE, "skatepark", 600, [r.model_dump(mode="json") for r in REFS],
                       COST.model_dump(mode="json"))
    assert "Rezumat" in d.descriere and d.descriere.endswith(DISCLAIMER)


def test_values_are_clamped(monkeypatch):
    weird = {**GOOD, "titlu": "x" * 300, "etape": [{"nume": "Execuție", "durata_luni": 999}],
             "riscuri": ["a", "a", "b"]}
    _gemini(monkeypatch, weird)
    d = generate_dosar(IDEA, SPACE, "skatepark", 600, REFS, COST)
    assert len(d.titlu) <= 80 and d.etape[0].durata_luni == 36 and d.riscuri == ["a", "b"]


def test_web_notes_reach_gemini_when_live_search_is_on(monkeypatch):
    prompts = _gemini(monkeypatch, GOOD)
    monkeypatch.setenv("REFERENCES_LIVE_SEARCH", "true")
    monkeypatch.setattr("backend.ai.references.search.research_notes",
                        lambda tip: ["Bazine separate pentru copii", "Necesită sistem de filtrare a apei"])
    generate_dosar(IDEA, SPACE, "Parc acvatic", 5000, [], estimate_cost([], 5000))
    data = prompts[0].split("<<<DATE", 1)[1]
    assert "Necesită sistem de filtrare a apei" in data and '"tip_amenajare": "parc acvatic"' in data


def test_no_web_notes_when_live_search_is_off(monkeypatch):
    prompts = _gemini(monkeypatch, GOOD)
    monkeypatch.setattr("backend.ai.references.search.research_notes",
                        lambda tip: pytest.fail("live search is off in unit tests"))
    generate_dosar(IDEA, SPACE, "skatepark", 600, REFS, COST)
    assert '"informatii_gasite": []' in prompts[0]
