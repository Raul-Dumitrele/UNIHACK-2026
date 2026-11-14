"""Score every responding model and write the chain order: backend/ai/llm/chain_order.json (committed).

    python -m backend.ai.llm.bench                  # models that passed check (models_live.json), else registry
    python -m backend.ai.llm.bench --max-models 4   # per provider (protects small daily quotas)
    python -m backend.ai.llm.bench --write-docs     # also refresh the report in docs/DATA.md

Per model: 10 golden ideas (structure_idea prompt, labelled in backend/ai/eval_ideas.json) and 3
owner_message cases. Metrics: valid JSON rate (pass_rate), structure accuracy against the labels,
Romanian quality (diacritics, no English filler, sane length) and median latency.
score = 100 × (0.35 pass_rate + 0.35 accuracy + 0.15 romanian + 0.15 speed). Models under
LLM_MIN_PASS_RATE are listed as excluded (the chain re-applies the threshold when it loads the file).
A provider's daily quota (registry RPD) is never planned past 80 %.
"""
import argparse
import json
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from backend.ai.contract import OWNER_PROMPT, _OwnerDraft
from backend.ai.evaluate import load_cases
from backend.ai.fallback import normalize
from backend.ai.gemini import JSON_KEYS, MAX_INPUT_CHARS, PROMPT
from backend.ai.llm.chain import CHAIN_ORDER_FILE, MODELS_LIVE_FILE, parse_json
from backend.ai.llm.check import pace
from backend.ai.llm.providers import ProviderError, complete, load_registry
from backend.ai.llm.settings import get_llm_settings
from backend.ai.schemas import DossierBase

DATA_MD = Path(__file__).resolve().parents[3] / "docs" / "DATA.md"
DOC_START, DOC_END = "<!-- bench:start -->", "<!-- bench:end -->"
OWNER_CASES = [
    {"activitate": "Atelier de pictură", "vecini_interesati": 6, "persoane": 12, "dotari": ["mese"],
     "spatiu": "Biblioteca Fabric", "zi": "sâmbătă", "de_la": "10:00", "pana_la": "13:00"},
    {"activitate": "Club de șah pentru seniori", "vecini_interesati": 4, "persoane": 10, "dotari": ["mese", "scaune"],
     "spatiu": "Centrul comunitar Iosefin", "zi": "joi", "de_la": "17:00", "pana_la": "19:00"},
    {"activitate": "Curs de programare pentru copii", "vecini_interesati": 9, "persoane": 15, "dotari": ["proiector", "wifi"],
     "spatiu": "Hub-ul din Cetate", "zi": "vineri", "de_la": "16:00", "pana_la": "18:00"},
]
ENGLISH = {"the", "and", "with", "for", "this", "that", "is", "are", "of", "to", "you", "your", "will"}
CALLS_PER_MODEL = 13


def golden_ideas() -> list[dict]:
    cases = load_cases("ideas")
    return cases[::3][:10]  # spread across categories


def romanian_ok(text: str) -> bool:
    words = re.findall(r"[a-zA-ZăâîșțĂÂÎȘȚşţ]+", text or "")
    if len(words) < 3:
        return False
    english = sum(w.lower() in ENGLISH for w in words) / len(words)
    has_diacritics = bool(re.search(r"[ăâîșțşţĂÂÎȘȚ]", text)) or len(text) < 60
    return english < 0.05 and has_diacritics and len(text) <= 1500


def accuracy(case: dict, d: DossierBase) -> float:
    checks = [d.category.value == case["category"]]
    if "participants" in case:
        checks.append(abs(d.expected_participants - case["participants"]) <= max(2, 0.2 * case["participants"]))
    if "setting" in case:
        checks.append(d.setting.value == case["setting"])
    return sum(checks) / len(checks)


def bench_model(p, model: str, client, timeout: float, sleep=lambda p: pace(p, same_model_next=True)) -> dict:
    ok = acc = ro = 0.0
    latencies: list[float] = []
    responded = False
    ideas = golden_ideas()
    for case in ideas:
        started = time.perf_counter()
        try:
            text = complete(p, model, PROMPT.replace("{text}", case["text"][:MAX_INPUT_CHARS]) + JSON_KEYS,
                            timeout=timeout, client=client)
            responded = True
            d = parse_json(text, DossierBase)
            ok += 1
            acc += accuracy(case, d)
            ro += romanian_ok(f"{d.title}. {d.summary}")
        except ProviderError as err:
            if err.kind == "auth":
                return {"responded": False, "error": "401/403"}
        except ValueError:
            responded = True
        latencies.append(time.perf_counter() - started)
        sleep(p)
    for case in OWNER_CASES:
        started = time.perf_counter()
        try:
            text = complete(p, model, OWNER_PROMPT.replace("{data}", json.dumps(case, ensure_ascii=False)),
                            timeout=timeout, client=client)
            responded = True
            msg = parse_json(text, _OwnerDraft).mesaj
            if case["spatiu"] in msg and case["de_la"] in msg:
                ok += 1
            ro += romanian_ok(msg)
        except ProviderError:
            pass
        except ValueError:
            responded = True
        latencies.append(time.perf_counter() - started)
        sleep(p)
    total = len(ideas) + len(OWNER_CASES)
    pass_rate = ok / total
    accuracy_ = acc / len(ideas)
    romanian = ro / total
    latency = statistics.median(latencies) if latencies else None
    speed = max(0.0, 1 - (latency or 10) / 10)
    return {"responded": responded, "pass_rate": round(pass_rate, 3), "accuracy": round(accuracy_, 3),
            "romanian": round(romanian, 3), "latency_s": round(latency, 2) if latency else None,
            "score": round(100 * (0.35 * pass_rate + 0.35 * accuracy_ + 0.15 * romanian + 0.15 * speed), 1)}


def candidates(registry, only=None, max_models=4) -> list[tuple]:
    live = json.loads(MODELS_LIVE_FILE.read_text(encoding="utf-8")) if MODELS_LIVE_FILE.exists() else None
    by_id = {p.id: p for p in registry}
    if live:
        pairs = [(m["provider"], m["model"]) for m in live["models"] if m.get("status") == "OK"]
    else:
        pairs = [(p.id, m) for p in registry for m in p.models]
    out, per = [], {}
    for pid, model in pairs:
        if pid in by_id and (not only or pid in only) and per.get(pid, 0) < max_models:
            per[pid] = per.get(pid, 0) + 1
            out.append((by_id[pid], model))
    return out


def run(only=None, max_models=4, client=None, sleep=lambda p: pace(p, same_model_next=True)) -> list[dict]:
    settings = get_llm_settings()
    registry = load_registry()
    used: dict[str, int] = {}
    rows = []
    with (client or httpx.Client()) as http:
        for p, model in candidates(registry, only, max_models):
            row = {"provider": p.id, "model": model}
            if not p.active(settings):
                rows.append({**row, "responded": False, "excluded": "furnizor inactiv (fără cheie)"})
                continue
            if p.rpd and used.get(p.id, 0) + CALLS_PER_MODEL > 0.8 * p.rpd:
                rows.append({**row, "responded": False, "excluded": f"cota zilnică ({p.rpd} RPD) protejată"})
                continue
            used[p.id] = used.get(p.id, 0) + CALLS_PER_MODEL
            result = bench_model(p, model, http, settings.llm_timeout_s, sleep)
            rows.append({**row, **result})
    threshold = settings.llm_min_pass_rate
    for r in rows:
        if "excluded" in r:
            continue
        if not r.get("responded"):
            r["excluded"] = r.get("error") or "nu răspunde"
        elif threshold > 0 and r["pass_rate"] < threshold:
            r["excluded"] = f"sub prag ({r['pass_rate']:.0%} < {threshold:.0%})"
    rows.sort(key=lambda r: (-(r.get("score") or -1), r["provider"], r["model"]))
    return rows


def write_order(rows: list[dict], path: Path = CHAIN_ORDER_FILE) -> None:
    doc = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "threshold": get_llm_settings().llm_min_pass_rate,
           "models": [{k: r.get(k) for k in ("provider", "model", "score", "pass_rate", "accuracy", "romanian",
                                             "latency_s", "responded", "excluded")} for r in rows]}
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def table(rows: list[dict]) -> str:
    out = ["| # | Furnizor | Model | Scor | JSON valid | Acuratețe | Română | Latență (s) | În lanț |",
           "|---|---|---|---|---|---|---|---|---|"]
    rank = 0
    for r in rows:
        inside = "excluded" not in r
        rank += inside
        pct = lambda v: "-" if v is None else f"{v:.0%}"  # noqa: E731
        out.append(f"| {rank if inside else '-'} | {r['provider']} | `{r['model']}` | {r.get('score', '-')} | "
                   f"{pct(r.get('pass_rate'))} | {pct(r.get('accuracy'))} | {pct(r.get('romanian'))} | "
                   f"{r.get('latency_s') or '-'} | {'da' if inside else 'nu: ' + r['excluded']} |")
    return "\n".join(out)


def write_docs(rows: list[dict], path: Path = DATA_MD) -> None:
    text = path.read_text(encoding="utf-8")
    block = (f"{DOC_START}\nUltimul bench: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, prag "
             f"LLM_MIN_PASS_RATE = {get_llm_settings().llm_min_pass_rate}.\n\n{table(rows)}\n{DOC_END}")
    if DOC_START in text and DOC_END in text:
        text = text[:text.index(DOC_START)] + block + text[text.index(DOC_END) + len(DOC_END):]
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    path.write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m backend.ai.llm.bench")
    ap.add_argument("--provider", action="append")
    ap.add_argument("--max-models", type=int, default=4)
    ap.add_argument("--write-docs", action="store_true")
    args = ap.parse_args(argv)
    rows = run(set(args.provider or []) or None, args.max_models)
    write_order(rows)
    print(table(rows))
    print(f"\nLanț scris în {CHAIN_ORDER_FILE.name}: {sum('excluded' not in r for r in rows)} modele.")
    if args.write_docs:
        write_docs(rows)
        print("Raport actualizat în docs/DATA.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
