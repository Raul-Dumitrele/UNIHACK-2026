"""Live reference search, fully offline: Gemini, DNS and page fetches are faked."""
import json
import socket
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from backend.ai.references import core, search
from backend.ai.references.search import Candidate, Source

PAGE = """<html><head><script>var x = "999.999 lei";</script></head><body>
<p>Primăria a aprobat amenajarea unui foișor din lemn pe o suprafață de 48 mp.</p>
<p>Valoarea totală a investiției este de 125.400,50 lei, fără TVA.</p></body></html>"""


def _cand(**over):
    base = {"oras": "Oradea", "an": 2024, "suprafata_mp": 48, "cost_total": 125400.5, "moneda": "lei",
            "componente": ["foișor din lemn", "bănci"], "sursa_index": 0, "potrivire": 90}
    return Candidate(**{**base, **over})


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "CACHE_DIR", tmp_path / "cache")
    return tmp_path / "cache"


@pytest.fixture
def web(monkeypatch, cache):
    """Scripted search: sources, candidates and pages (url -> (final_url, html) or exception)."""
    state = {"sources": [Source(uri="https://vertexaisearch.cloud.google.com/redirect/abc", title="primarie")],
             "candidates": [_cand()], "pages": {}, "searches": 0}

    def fake_search(label):
        state["searches"] += 1
        return "text", state["sources"]

    def fake_fetch(url):
        page = state["pages"].get(url, ("https://www.oradea.ro/stiri/foisor", PAGE))
        if isinstance(page, Exception):
            raise page
        return page

    monkeypatch.setattr(search, "_search", fake_search)
    monkeypatch.setattr(search, "_extract", lambda label, text, sources: state["candidates"])
    monkeypatch.setattr(search, "safe_fetch", fake_fetch)
    return state


# --- number parsing and verification ------------------------------------------------------------

@pytest.mark.parametrize("raw, value", [("1.250.000,50", 1250000.5), ("7.681,50", 7681.5), ("2,5", 2.5),
                                        ("11 000", 11000), ("2100840", 2100840), ("1.240.520,4", 1240520.4)])
def test_ro_number(raw, value):
    assert search.ro_number(raw) == value


def test_amounts_and_areas_in_romanian_text():
    text = "Investiție de 11 mil. lei și 2,5 milioane de lei; contract 1.126.285,56 RON; 7.681,50 mp și 300 m²."
    assert search.amounts_in(text) == [11_000_000, 2_500_000, 1_126_285.56]
    assert search.areas_in(text) == [7681.5, 300]
    assert search.amounts_in("costă 600.000 de euro") == []


def test_html_text_skips_scripts():
    text = search.html_text(PAGE)
    assert "125.400,50 lei" in text and "999.999" not in text


# --- pipeline -----------------------------------------------------------------------------------

def test_verified_figures_are_kept_with_final_url(web, cache):
    [ref] = search.search_references("foișor")
    assert ref.sursa_tip == "cautare_ai_verificata"
    assert (ref.suprafata_mp, ref.cost_total_lei) == (48, 125400.5)
    assert ref.sursa_url == "https://www.oradea.ro/stiri/foisor"  # resolved, not the expiring redirect
    assert ref.id.startswith("foisor-live-oradea-2024-") and ref.tip_amenajare == "foisor"


def test_figures_missing_from_page_become_null(web):
    web["candidates"] = [_cand(cost_total=300000, suprafata_mp=120)]
    [ref] = search.search_references("foisor")
    assert ref.cost_total_lei is None and ref.suprafata_mp is None and ref.sursa_tip == "cautare_ai"


def test_euro_amounts_are_dropped(web):
    web["candidates"] = [_cand(moneda="euro")]
    [ref] = search.search_references("foisor")
    assert ref.cost_total_lei is None and ref.suprafata_mp == 48


@pytest.mark.parametrize("bad", [{"sursa_index": 5}, {"sursa_index": -1}, {"potrivire": 30}])
def test_candidates_without_a_search_source_or_weak_match_are_dropped(web, bad):
    web["candidates"] = [_cand(**bad)]
    assert search.search_references("foisor") == []


def test_unresolved_grounding_redirect_is_dropped(web):
    uri = web["sources"][0].uri
    web["pages"][uri] = (uri, PAGE)  # the redirect answered 200 itself (interstitial page)
    assert search.search_references("foisor") == []


def test_unreachable_or_blocked_pages_are_dropped(web):
    web["pages"][web["sources"][0].uri] = ValueError("blocked URL")
    assert search.search_references("foisor") == []


def test_search_failure_returns_empty(monkeypatch, cache):
    monkeypatch.setattr(search, "_search", lambda label: (_ for _ in ()).throw(RuntimeError("429")))
    assert search.search_references("foisor") == []
    assert not (cache / "foisor.json").exists()  # a failed search is retried next time


def test_results_are_cached_and_not_searched_again(web, cache):
    first = search.search_references("foisor")
    assert len(first) == 1 and web["searches"] == 1
    doc = json.loads((cache / "foisor.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in doc["referinte"]] == [first[0].id]
    assert search.search_references("foisor") == [] and web["searches"] == 1  # cached rows come via the base
    assert [r.id for r in core.local_references("foisor")] == [first[0].id]


def test_stale_cache_is_refreshed(web, cache):
    search.search_references("foisor")
    path = cache / "foisor.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["cautat_la"] = (datetime.now(timezone.utc) - timedelta(days=search.CACHE_DAYS + 1)).isoformat()
    path.write_text(json.dumps(doc), encoding="utf-8")
    search.search_references("foisor")
    assert web["searches"] == 2


# --- SSRF guard ---------------------------------------------------------------------------------

def _resolve_to(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: [(None, None, None, "", (ip, 0))])


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1"])
def test_private_addresses_are_blocked(monkeypatch, ip):
    _resolve_to(monkeypatch, ip)
    assert search.is_public_host("exemplu.ro") is False
    with pytest.raises(ValueError, match="blocked"):
        search.safe_fetch("https://exemplu.ro/pagina")


def test_localhost_and_bad_schemes_are_blocked(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    assert search.is_public_host("localhost") is False
    with pytest.raises(ValueError, match="blocked"):
        search.safe_fetch("file:///etc/passwd")


def test_every_redirect_hop_is_checked(monkeypatch):
    hosts = {"public.ro": "93.184.216.34", "internal.ro": "10.0.0.1"}
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: [(None, None, None, "", (hosts[host], 0))])

    def handler(request):
        if request.url.host == "public.ro":
            return httpx.Response(302, headers={"location": "https://internal.ro/secret"})
        pytest.fail("the internal host must never be contacted")

    real_client = httpx.Client
    monkeypatch.setattr(search.httpx, "Client",
                        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    with pytest.raises(ValueError, match="blocked URL: https://internal.ro"):
        search.safe_fetch("https://public.ro/start")


def test_safe_fetch_follows_public_redirects(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")

    def handler(request):
        if request.url.path == "/r":
            return httpx.Response(301, headers={"location": "/final"})
        return httpx.Response(200, html=PAGE)

    real_client = httpx.Client
    monkeypatch.setattr(search.httpx, "Client",
                        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    final, body = search.safe_fetch("https://primarie.ro/r")
    assert final == "https://primarie.ro/final" and "125.400,50" in body


# --- any type, abroad, notes --------------------------------------------------------------------

def test_foreign_projects_are_examples_without_cost(web):
    web["candidates"] = [_cand(oras="Viena", tara="Austria")]
    [ref] = search.search_references("parc acvatic")
    assert ref.oras == "Viena, Austria" and ref.cost_total_lei is None and ref.suprafata_mp == 48
    assert ref.tip_amenajare == "parc_acvatic"


def test_free_text_label_is_used_for_the_search(monkeypatch, cache):
    seen = []
    monkeypatch.setattr(search, "_search", lambda label, prompt=search.SEARCH_PROMPT: seen.append(label) or ("", []))
    search.search_references("Fântână arteziană")
    assert seen == ["fântână arteziană"]


def test_research_notes_drop_money_and_are_cached(monkeypatch, cache):
    answers = ["- Bazine pentru copii și adulți\n- Costă în jur de 20 milioane de lei\n* Studiu de fezabilitate\n- ok"]
    calls = []

    def fake(label, prompt=search.SEARCH_PROMPT):
        calls.append((label, prompt))
        return answers[0], []

    monkeypatch.setattr(search, "_search", fake)
    notes = search.research_notes("parc acvatic")
    assert notes == ["Bazine pentru copii și adulți", "Studiu de fezabilitate"]
    assert calls[0][1] is search.NOTES_PROMPT
    assert search.research_notes("parc acvatic") == notes and len(calls) == 1  # cached


def test_research_notes_failure_is_empty(monkeypatch, cache):
    monkeypatch.setattr(search, "_search", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("429")))
    assert search.research_notes("parc acvatic") == []
