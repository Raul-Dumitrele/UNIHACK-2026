"""Which configured models answer right now. Writes backend/ai/llm/models_live.json (ignored by git).

    python -m backend.ai.llm.check                    # every active provider, registry + discovered models
    python -m backend.ai.llm.check --provider groq    # one provider (repeatable)
    python -m backend.ai.llm.check --max-models 5 --no-discover

Sends one tiny prompt per model, paced by each provider's RPM. Prints provider, model, status
(OK / 401-403 / 429 / timeout / JSON invalid / ...) and latency. Never prints keys or answers.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel

from backend.ai.llm.chain import MODELS_LIVE_FILE, parse_json
from backend.ai.llm.providers import Provider, ProviderError, complete, list_models, load_registry
from backend.ai.llm.settings import LLMSettings, get_llm_settings

PING = 'Răspunde doar cu acest obiect JSON: {"ok": true}'
STATUS = {"auth": "401/403", "rate": "429", "timeout": "timeout"}


class Ping(BaseModel):
    ok: bool


UNKNOWN_RPM_PAUSE_S = 2.0  # providers that publish no limit (Gemini free tier, NVIDIA...)


def pace(p: Provider, same_model_next: bool = False) -> None:
    """Stay under the provider's per-minute limit between two calls. OVH's 2 RPM is per model: a pause is
    needed only when the next call goes to the same model (bench), not between different models (check)."""
    if p.id == "ovh":
        if same_model_next:
            time.sleep(31.0)
    elif p.rpm:
        time.sleep(60.0 / p.rpm)
    else:
        time.sleep(UNKNOWN_RPM_PAUSE_S)


def inactive_reason(p: Provider) -> str:
    if p.url() is None:
        return "lipsește " + ", ".join(p.extra_env.values())
    return f"fără cheie ({p.key_env})"


def check(providers: list[Provider], settings: LLMSettings, client: httpx.Client, *, only: set[str] | None = None,
          max_models: int = 20, discover: bool = True, sleep=pace) -> list[dict]:
    rows: list[dict] = []
    for p in providers:
        if only and p.id not in only:
            continue
        if not p.active(settings):
            rows.append({"provider": p.id, "model": "-", "status": inactive_reason(p), "latency_ms": None,
                         "source": "-"})
            continue
        models = [(m, "registry") for m in p.models]
        if discover:
            try:
                models += [(m, "discovered") for m in list_models(p, client=client, timeout=settings.llm_timeout_s)
                           if m not in p.models]
            except ProviderError as err:
                rows.append({"provider": p.id, "model": "(listare)", "status": STATUS.get(err.kind, err.kind),
                             "latency_ms": None, "source": "-"})
        for model, source in models[:max_models]:
            started = time.perf_counter()
            try:
                parse_json(complete(p, model, PING, json_mode=True, timeout=settings.llm_timeout_s, client=client), Ping)
                status = "OK"
            except ProviderError as err:
                status = STATUS.get(err.kind, err.kind)
            except ValueError:
                status = "JSON invalid"
            rows.append({"provider": p.id, "model": model, "status": status, "source": source,
                         "latency_ms": round((time.perf_counter() - started) * 1000)})
            if status == "401/403":
                break  # the key is wrong for the whole provider
            sleep(p)
    return rows


def write_live(rows: list[dict], path=MODELS_LIVE_FILE) -> None:
    tested = [r for r in rows if r["model"] not in ("-", "(listare)")]
    path.write_text(json.dumps({"tested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "models": tested}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def table(rows: list[dict]) -> str:
    out = [f"{'furnizor':<12} {'model':<52} {'stare':<26} {'ms':>6}  sursa"]
    for r in rows:
        ms = "" if r["latency_ms"] is None else str(r["latency_ms"])
        out.append(f"{r['provider']:<12} {r['model'][:52]:<52} {r['status'][:26]:<26} {ms:>6}  {r['source']}")
    ok = sum(r["status"] == "OK" for r in rows)
    out.append(f"\n{ok} modele răspund corect din {sum(r['model'] not in ('-', '(listare)') for r in rows)} testate.")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m backend.ai.llm.check")
    ap.add_argument("--provider", action="append")
    ap.add_argument("--max-models", type=int, default=20)
    ap.add_argument("--no-discover", action="store_true")
    args = ap.parse_args(argv)
    with httpx.Client() as client:
        rows = check(load_registry(), get_llm_settings(), client, only=set(args.provider or []) or None,
                     max_models=args.max_models, discover=not args.no_discover)
    write_live(rows)
    print(table(rows))
    print(f"\nRezultat salvat în {MODELS_LIVE_FILE.name} (ignorat de git).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
