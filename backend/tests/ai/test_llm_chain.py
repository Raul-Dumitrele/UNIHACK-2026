"""LLM chain (backend.ai.llm) against a simulated HTTP transport and a fake clock: no live calls."""
import json

import httpx
import pytest
from pydantic import BaseModel

from backend.ai.llm import Candidate, Chain, LLMUnavailable
from backend.ai.llm.chain import load_order, parse_candidates, parse_json
from backend.ai.llm.providers import Provider, ProviderError, complete, list_models
from backend.ai.llm.settings import LLMSettings


class Out(BaseModel):
    titlu: str
    n: int


GOOD = {"titlu": "Atelier", "n": 3}


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def _openai_ok(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _provider(pid="a", kind="openai_compat", key_env=None, **kw):
    return Provider(id=pid, name=pid, kind=kind, base_url=f"https://{pid}.test/v1", key_env=key_env or f"{pid.upper()}_API_KEY",
                    models=kw.pop("models", ["m1"]), **kw)


@pytest.fixture
def keys(monkeypatch):
    for pid in ("A", "B", "C", "D", "E", "G"):
        monkeypatch.setenv(f"{pid}_API_KEY", f"key-{pid.lower()}")


def _settings(**kw):
    base = dict(llm_enabled=True, llm_chain="", llm_timeout_s=5, llm_total_budget_s=20, llm_max_attempts=4,
                llm_min_pass_rate=0.7, llm_allow_keyless=True, llm_cache=False, llm_cooldown_s=300)
    return LLMSettings(**{**base, **kw})


def _chain(handler, providers, order, clock=None, **settings):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return Chain(providers, _settings(**settings), client=client, clock=clock or Clock(),
                 order=[Candidate(*o) for o in order])


def _route(answers):
    """answers: host -> list of responses (or exceptions) served in order; records calls per host."""
    calls: dict[str, int] = {}

    def handler(request):
        host = request.url.host.split(".")[0]
        calls[host] = calls.get(host, 0) + 1
        seq = answers[host]
        item = seq[min(calls[host], len(seq)) - 1]
        if isinstance(item, Exception):
            raise item
        return item

    return handler, calls


# --- providers ----------------------------------------------------------------------------------

def test_provider_without_key_is_skipped(monkeypatch):
    monkeypatch.delenv("A_API_KEY", raising=False)
    monkeypatch.setenv("B_API_KEY", "x")
    handler, calls = _route({"b": [_openai_ok(json.dumps(GOOD))]})
    chain = _chain(handler, [_provider("a"), _provider("b")], [("a", "m1"), ("b", "m1")])
    assert chain.generate_json("p", Out).titlu == "Atelier"
    assert calls == {"b": 1}


def test_keyless_provider_is_used_only_when_allowed(monkeypatch):
    monkeypatch.delenv("K_API_KEY", raising=False)
    handler, calls = _route({"k": [_openai_ok(json.dumps(GOOD))]})
    keyless = _provider("k", key_required=False)
    assert _chain(handler, [keyless], [("k", "m1")]).generate_json("p", Out).n == 3
    with pytest.raises(LLMUnavailable, match="no active provider"):
        _chain(handler, [keyless], [("k", "m1")], llm_allow_keyless=False).generate_json("p", Out)


def test_no_key_is_ever_sent_to_send_key_false(monkeypatch):
    monkeypatch.setenv("O_API_KEY", "paid-key")
    seen = []

    def handler(request):
        seen.append(request.headers.get("authorization"))
        return _openai_ok(json.dumps(GOOD))

    ovh = _provider("o", key_required=False, send_key=False)
    _chain(handler, [ovh], [("o", "m1")]).generate_json("p", Out)
    assert seen == [None]


def test_gemini_request_shape_and_key_header(monkeypatch):
    monkeypatch.setenv("G_API_KEY", "gk")
    seen = {}

    def handler(request):
        seen.update(url=str(request.url), key=request.headers.get("x-goog-api-key"), body=json.loads(request.content))
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(GOOD)}]}}]})

    p = _provider("g", kind="gemini")
    text = complete(p, "gemini-x", "salut", "sistem", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert json.loads(text) == GOOD
    assert seen["url"].endswith("/models/gemini-x:generateContent") and "key=" not in seen["url"]
    assert seen["key"] == "gk" and seen["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "sistem"


def test_response_format_rejected_is_retried_plain(keys):
    bodies = []

    def handler(request):
        body = json.loads(request.content)
        bodies.append(body)
        return httpx.Response(400) if "response_format" in body else _openai_ok(json.dumps(GOOD))

    assert complete(_provider("a"), "m1", "p", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert len(bodies) == 2 and "response_format" not in bodies[1]


def test_cloudflare_account_placeholder(monkeypatch, keys):
    cf = _provider("c", extra_env={"account_id": "C_ACCOUNT"})
    cf.base_url = "https://c.test/accounts/{account_id}/ai/v1"
    monkeypatch.delenv("C_ACCOUNT", raising=False)
    assert cf.active(_settings()) is False
    monkeypatch.setenv("C_ACCOUNT", "acc1")
    assert cf.url() == "https://c.test/accounts/acc1/ai/v1" and cf.active(_settings())


# --- discovery ----------------------------------------------------------------------------------

def test_discovery_keeps_free_chat_models(keys):
    def handler(request):
        return httpx.Response(200, json={"data": [
            {"id": "x/model:free"}, {"id": "y/paid", "pricing": {"prompt": "0.1", "completion": "0.2"}},
            {"id": "z/zero", "pricing": {"prompt": "0", "completion": "0"}}, {"id": "e/text-embed:free"}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert list_models(_provider("openrouter", key_env="A_API_KEY"), client=client) == ["x/model:free", "z/zero"]
    assert list_models(_provider("a"), client=client) == ["x/model:free", "y/paid", "z/zero"]


def test_gemini_discovery_needs_generate_content(keys):
    def handler(request):
        return httpx.Response(200, json={"models": [
            {"name": "models/gemini-ok", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/text-embedding-4", "supportedGenerationMethods": ["embedContent"]}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert list_models(_provider("g", kind="gemini"), client=client) == ["gemini-ok"]


# --- falling back -------------------------------------------------------------------------------

@pytest.mark.parametrize("failure", [
    httpx.Response(429), httpx.Response(500), httpx.Response(503), httpx.ReadTimeout("slow"), httpx.ConnectError("x"),
])
def test_moves_to_next_model(keys, failure):
    handler, calls = _route({"a": [failure], "b": [_openai_ok(json.dumps(GOOD))]})
    chain = _chain(handler, [_provider("a"), _provider("b")], [("a", "m1"), ("b", "m1")])
    assert chain.generate_json("p", Out) == Out(**GOOD)
    assert calls == {"a": 1, "b": 1}


def test_invalid_json_is_retried_once_then_next(keys):
    handler, calls = _route({"a": [_openai_ok("nu e json"), _openai_ok("tot nu")],
                             "b": [_openai_ok("<think>...</think>```json\n" + json.dumps(GOOD) + "\n```")]})
    chain = _chain(handler, [_provider("a"), _provider("b")], [("a", "m1"), ("b", "m1")])
    assert chain.generate_json("p", Out).titlu == "Atelier"
    assert calls == {"a": 2, "b": 1}
    assert "a:m1" in chain.cooldown_until


def test_invalid_then_valid_on_retry(keys):
    handler, calls = _route({"a": [_openai_ok('{"titlu": 5}'), _openai_ok(json.dumps(GOOD))]})
    assert _chain(handler, [_provider("a")], [("a", "m1")]).generate_json("p", Out).n == 3
    assert calls == {"a": 2}


def test_validator_rejection_counts_as_invalid(keys):
    def no_three(o):
        if o.n == 3:
            raise ValueError("rejected")

    handler, calls = _route({"a": [_openai_ok(json.dumps(GOOD))], "b": [_openai_ok(json.dumps({"titlu": "x", "n": 4}))]})
    chain = _chain(handler, [_provider("a"), _provider("b")], [("a", "m1"), ("b", "m1")])
    assert chain.generate_json("p", Out, validator=no_three).n == 4
    assert calls == {"a": 2, "b": 1}


def test_401_disables_the_provider_until_restart(keys):
    handler, calls = _route({"a": [httpx.Response(401)], "b": [_openai_ok(json.dumps(GOOD))]})
    chain = _chain(handler, [_provider("a", models=["m1", "m2"]), _provider("b")],
                   [("a", "m1"), ("a", "m2"), ("b", "m1")])
    chain.generate_json("p", Out)
    chain.generate_json("p", Out)
    assert "a" in chain.disabled and calls == {"a": 1, "b": 2}  # a:m2 never tried


def test_retry_after_blocks_the_provider(keys):
    clock = Clock()
    handler, calls = _route({"a": [httpx.Response(429, headers={"Retry-After": "30"}), _openai_ok(json.dumps(GOOD))],
                             "b": [_openai_ok(json.dumps(GOOD))]})
    chain = _chain(handler, [_provider("a", models=["m1", "m2"]), _provider("b")],
                   [("a", "m1"), ("a", "m2"), ("b", "m1")], clock=clock)
    chain.generate_json("p", Out)
    assert chain.blocked_until["a"] == clock.t + 30 and calls == {"a": 1, "b": 1}
    clock.t += 31  # after Retry-After, a:m2 (not in cooldown) is tried again
    chain.generate_json("p", Out)
    assert calls == {"a": 2, "b": 1}


def test_cooldown_skips_a_failed_model_for_five_minutes(keys):
    clock = Clock()
    handler, calls = _route({"a": [httpx.Response(500), _openai_ok(json.dumps(GOOD))], "b": [_openai_ok(json.dumps(GOOD))]})
    chain = _chain(handler, [_provider("a"), _provider("b")], [("a", "m1"), ("b", "m1")], clock=clock)
    chain.generate_json("p", Out)
    clock.t += 299
    chain.generate_json("p", Out)
    assert calls == {"a": 1, "b": 2}
    clock.t += 2
    chain.generate_json("p", Out)
    assert calls == {"a": 2, "b": 2}


def test_rpm_limit_from_registry(keys):
    handler, calls = _route({"a": [_openai_ok(json.dumps(GOOD))], "b": [_openai_ok(json.dumps(GOOD))]})
    chain = _chain(handler, [_provider("a", rpm=2), _provider("b")], [("a", "m1"), ("b", "m1")])
    for _ in range(3):
        chain.generate_json("p", Out)
    assert calls == {"a": 2, "b": 1}


def test_max_attempts(keys):
    handler, calls = _route({h: [httpx.Response(500)] for h in "abcde"})
    chain = _chain(handler, [_provider(h) for h in "abcde"], [(h, "m1") for h in "abcde"], llm_max_attempts=3)
    with pytest.raises(LLMUnavailable):
        chain.generate_json("p", Out)
    assert sum(calls.values()) == 3


def test_total_time_budget(keys):
    clock = Clock()

    def handler(request):
        clock.t += 12  # each call takes 12 s
        return httpx.Response(503)

    chain = _chain(handler, [_provider("a"), _provider("b"), _provider("c")], [("a", "m1"), ("b", "m1"), ("c", "m1")],
                   clock=clock, llm_total_budget_s=20)
    with pytest.raises(LLMUnavailable):
        chain.generate_json("p", Out)
    assert clock.t - 1000 == 24  # a (12 s) + b (12 s), then the 20 s budget is spent: c is never called


def test_everything_fails_raises_for_the_caller_fallback(keys):
    handler, _ = _route({"a": [httpx.Response(500)], "b": [_openai_ok("nope"), _openai_ok("nope")]})
    chain = _chain(handler, [_provider("a"), _provider("b")], [("a", "m1"), ("b", "m1")])
    with pytest.raises(LLMUnavailable) as err:
        chain.generate_json("p", Out)
    assert "a:m1: server" in str(err.value) and "b:m1: invalid JSON" in str(err.value)


def test_disabled_chain_never_calls(keys):
    handler, calls = _route({"a": [_openai_ok(json.dumps(GOOD))]})
    with pytest.raises(LLMUnavailable, match="disabled"):
        _chain(handler, [_provider("a")], [("a", "m1")], llm_enabled=False).generate_json("p", Out)
    assert calls == {}


# --- cache --------------------------------------------------------------------------------------

def test_cache_answers_without_calling(keys, tmp_path):
    handler, calls = _route({"a": [_openai_ok(json.dumps(GOOD))]})
    client = httpx.Client(transport=httpx.MockTransport(handler))

    def make():
        return Chain([_provider("a")], _settings(llm_cache=True), client=client, clock=Clock(),
                     order=[Candidate("a", "m1")], cache_dir=tmp_path)

    assert make().generate_json("p", Out, task="t").n == 3
    assert make().generate_json("p", Out, task="t").n == 3  # new chain, same disk cache
    assert calls == {"a": 1} and len(list(tmp_path.glob("*.json"))) == 1
    make().generate_json("alt prompt", Out, task="t")
    assert calls == {"a": 2}


# --- order --------------------------------------------------------------------------------------

def _write(path, doc):
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_order_from_bench_and_threshold(keys, tmp_path):
    providers = {p.id: p for p in [_provider("a", models=["m1", "m2"]), _provider("b")]}
    order = _write(tmp_path / "order.json", {"models": [
        {"provider": "b", "model": "m1", "pass_rate": 0.9, "responded": True},
        {"provider": "a", "model": "m2", "pass_rate": 0.5, "responded": True},
        {"provider": "a", "model": "m1", "pass_rate": 0.0, "responded": False}]})
    live = tmp_path / "missing.json"

    def keys_of(cs):
        return [c.key for c in cs]

    assert keys_of(load_order(_settings(), providers, order_file=order, live_file=live)) == ["b:m1"]
    assert keys_of(load_order(_settings(llm_min_pass_rate=0.4), providers, order_file=order, live_file=live)) == \
        ["b:m1", "a:m2"]
    assert keys_of(load_order(_settings(llm_min_pass_rate=0), providers, order_file=order, live_file=live)) == \
        ["b:m1", "a:m2"]  # 0: every model that answered


def test_llm_chain_override_wins(keys, tmp_path):
    providers = {p.id: p for p in [_provider("a", models=["m1", "x:y"]), _provider("b")]}
    order = _write(tmp_path / "order.json", {"models": [{"provider": "b", "model": "m1", "pass_rate": 1, "responded": True}]})
    got = load_order(_settings(llm_chain="a:x:y, zzz:m, a:m1"), providers, order_file=order, live_file=tmp_path / "n")
    assert [c.key for c in got] == ["a:x:y", "a:m1"]  # unknown provider dropped, model ids may contain ':'
    assert parse_candidates("llm7:gpt-oss:20b") == [Candidate("llm7", "gpt-oss:20b")]


def test_default_order_registry_then_live_check(keys, tmp_path):
    providers = {p.id: p for p in [_provider("a", models=["m1", "m2"]), _provider("b")]}
    live = _write(tmp_path / "live.json", {"models": [
        {"provider": "a", "model": "m1", "status": "timeout"}, {"provider": "a", "model": "m2", "status": "OK"},
        {"provider": "b", "model": "new", "status": "OK"}]})
    got = load_order(_settings(), providers, order_file=tmp_path / "none.json", live_file=live)
    assert [c.key for c in got] == ["a:m2", "b:m1", "b:new"]


# --- parsing ------------------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    json.dumps(GOOD), "Sigur! " + json.dumps(GOOD) + " Gata.", "```json\n" + json.dumps(GOOD) + "\n```",
    "<think>hmm {not this}</think>" + json.dumps(GOOD),
])
def test_parse_json_tolerates_wrapping(text):
    assert parse_json(text, Out) == Out(**GOOD)


def test_parse_json_rejects_missing_object():
    with pytest.raises(ValueError):
        parse_json("nimic aici", Out)


def test_provider_error_kinds(keys):
    for status, kind in [(401, "auth"), (403, "auth"), (429, "rate"), (502, "server"), (404, "bad_request")]:
        client = httpx.Client(transport=httpx.MockTransport(lambda r, s=status: httpx.Response(s)))
        with pytest.raises(ProviderError) as err:
            complete(_provider("a"), "m1", "p", json_mode=False, client=client)
        assert err.value.kind == kind
