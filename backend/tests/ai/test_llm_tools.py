"""check / bench / sync_registry with a simulated transport (no live calls, no sleeping)."""
import json

import httpx
import pytest

from backend.ai.llm import bench, check, sync_registry
from backend.ai.llm.providers import Provider
from backend.ai.llm.settings import LLMSettings

GOOD_DOSSIER = {"title": "Atelier", "summary": "Vecinii învață să-și repare bicicletele.", "category": "atelier",
                "audience": "vecinii", "expected_participants": 8, "duration_hours": 2, "needs": ["mese"],
                "setting": "interior", "tags": ["atelier"]}


def _p(pid, **kw):
    return Provider(id=pid, name=pid, kind="openai_compat", base_url=f"https://{pid}.test/v1",
                    key_env=f"{pid.upper()}_API_KEY", models=kw.pop("models", ["m1"]), **kw)


def _ok(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


@pytest.fixture
def settings():
    return LLMSettings(llm_enabled=True, llm_allow_keyless=True, llm_timeout_s=5, llm_min_pass_rate=0.7)


def test_check_statuses_and_inactive(monkeypatch, settings, tmp_path):
    monkeypatch.setenv("A_API_KEY", "k")
    monkeypatch.setenv("B_API_KEY", "k")
    monkeypatch.delenv("C_API_KEY", raising=False)

    def handler(request):
        host = request.url.host.split(".")[0]
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "m1"}, {"id": "new-model"}, {"id": "x-embed"}]})
        model = json.loads(request.content)["model"]
        if host == "b":
            return httpx.Response(401)
        return _ok('{"ok": true}') if model == "m1" else _ok("nu știu")

    rows = check.check([_p("a"), _p("b", models=["m1", "m2"]), _p("c")], settings,
                       httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda p: None)
    got = {(r["provider"], r["model"]): r["status"] for r in rows}
    assert got[("a", "m1")] == "OK" and got[("a", "new-model")] == "JSON invalid"
    assert ("a", "x-embed") not in got  # embeddings are never tested
    assert got[("b", "m1")] == "401/403" and ("b", "m2") not in got  # wrong key: stop that provider
    assert got[("c", "-")].startswith("fără cheie")
    live = tmp_path / "live.json"
    check.write_live(rows, live)
    assert {m["model"] for m in json.loads(live.read_text())["models"]} == {"m1", "new-model"}
    assert "1 modele răspund corect" in check.table(rows)


def test_bench_scores_and_excludes(monkeypatch, settings):
    monkeypatch.setenv("A_API_KEY", "k")
    monkeypatch.setenv("B_API_KEY", "k")

    def handler(request):
        body = json.loads(request.content)
        prompt = body["messages"][-1]["content"]
        if request.url.host.startswith("b"):
            return _ok("nu e json")
        if "proprietarul" in prompt:
            data = json.loads(prompt.split("<<<DATE", 1)[1].split("DATE>>>", 1)[0])
            return _ok(json.dumps({"mesaj": f"Bună ziua! Am dori să folosim {data['spatiu']} {data['zi']}, "
                                            f"între {data['de_la']} și {data['pana_la']}. Vă mulțumim!"}))
        return _ok(json.dumps(GOOD_DOSSIER))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    a = bench.bench_model(_p("a"), "m1", client, 5, sleep=lambda p: None)
    assert a["responded"] and a["pass_rate"] == 1.0 and 0 < a["accuracy"] <= 1 and a["score"] > 50
    b = bench.bench_model(_p("b"), "m1", client, 5, sleep=lambda p: None)
    assert b["responded"] and b["pass_rate"] == 0


def test_bench_run_order_threshold_and_quota(monkeypatch):
    regs = [_p("a"), _p("b"), _p("q", rpd=15)]
    monkeypatch.setattr(bench, "load_registry", lambda: regs)
    monkeypatch.setattr(bench, "candidates", lambda registry, only, max_models: [(p, "m1") for p in regs])
    monkeypatch.setattr(bench, "get_llm_settings", lambda: LLMSettings(llm_min_pass_rate=0.7))
    for pid in "ABQ":
        monkeypatch.setenv(f"{pid}_API_KEY", "k")
    results = {"a": {"responded": True, "pass_rate": 0.9, "score": 80},
               "b": {"responded": True, "pass_rate": 0.5, "score": 60}}
    monkeypatch.setattr(bench, "bench_model", lambda p, model, client, timeout, sleep: results[p.id])
    rows = bench.run(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    by = {r["provider"]: r for r in rows}
    assert [r["provider"] for r in rows][:2] == ["a", "b"]
    assert "excluded" not in by["a"] and by["b"]["excluded"].startswith("sub prag")
    assert by["q"]["excluded"].startswith("cota zilnică")  # 13 calls > 80 % of 15 RPD
    assert "| 1 | a |" in bench.table(rows)


def test_bench_writes_docs_between_markers(tmp_path):
    doc = tmp_path / "DATA.md"
    doc.write_text("# Date\n\ntext\n", encoding="utf-8")
    rows = [{"provider": "a", "model": "m1", "score": 80, "pass_rate": 1, "accuracy": 1, "romanian": 1,
             "latency_s": 1.2, "responded": True}]
    bench.write_docs(rows, doc)
    bench.write_docs(rows, doc)
    text = doc.read_text(encoding="utf-8")
    assert text.count(bench.DOC_START) == 1 and "| 1 | a | `m1` |" in text and text.startswith("# Date")


@pytest.mark.parametrize("text, ok", [
    ("Bună ziua! Am dori să folosim sala sâmbătă între 10 și 12.", True),
    ("Hello! We would like to use the room for the workshop with the kids.", False),
    ("ok", False),
])
def test_romanian_check(text, ok):
    assert bench.romanian_ok(text) is ok


def test_sync_registry_diff():
    remote = {"providers": [
        {"name": "Groq", "models": [{"id": "openai/gpt-oss-120b"}, {"id": "new/model"}]},
        {"name": "Brand New AI", "baseUrl": "https://x", "models": [{"id": "x"}]}]}
    regs = [_p("groq", models=["openai/gpt-oss-120b", "old/model"]), _p("llm7")]
    lines = sync_registry.diff(remote, regs)
    assert "+ groq: model nou new/model" in lines and any(line.startswith("- groq: old/model") for line in lines)
    assert any("Brand New AI" in line for line in lines) and "- furnizor absent din listă: llm7" in lines


def test_committed_registry_is_complete():
    from backend.ai.llm.providers import load_registry

    regs = load_registry()
    assert len(regs) == 14 and sum(len(p.models) for p in regs) >= 70
    assert {p.id for p in regs if not p.key_required} == {"llm7", "kilo", "ovh"}
    assert next(p for p in regs if p.id == "ovh").send_key is False
    assert all(p.key_env.endswith("_API_KEY") and p.kind in ("gemini", "openai_compat") for p in regs)
