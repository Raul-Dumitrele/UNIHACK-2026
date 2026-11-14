"""Fallback chain over every configured free model: generate_json(prompt, schema) -> Pydantic instance.

Order: LLM_CHAIN (override) > chain_order.json (bench, filtered by LLM_MIN_PASS_RATE) > registry order.
Per request: answers from the cache first; then models in order, moving on at 429 (provider skipped
until Retry-After), 5xx, timeout, network errors or JSON that does not validate after one retry;
401/403 disables the provider until restart. Bounded by LLM_TOTAL_BUDGET_S and LLM_MAX_ATTEMPTS;
a failed model rests LLM_COOLDOWN_S; providers are rate limited by their registry RPM. When nothing
works it raises LLMUnavailable and the caller uses its deterministic fallback. No aggressive retries.
Logged: provider, model, outcome and duration only, never prompts, answers or keys.
"""
import json
import logging
import re
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from backend.ai.llm import cache
from backend.ai.llm.providers import Provider, ProviderError, complete, load_registry
from backend.ai.llm.settings import LLMSettings, get_llm_settings, llm_enabled

log = logging.getLogger("backend.ai.llm")

HERE = Path(__file__).resolve().parent
CHAIN_ORDER_FILE = HERE / "chain_order.json"
MODELS_LIVE_FILE = HERE / "models_live.json"
DEFAULT_RETRY_AFTER_S = 60.0
MIN_REMAINING_S = 0.5
JSON_REMINDER = "\n\nRăspunde DOAR cu un singur obiect JSON valid, fără text înainte sau după."

T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    """No configured model produced a valid answer within the budget."""


@dataclass(frozen=True)
class Candidate:
    provider: str
    model: str

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.model}"


def parse_candidates(spec: str) -> list[Candidate]:
    """'groq:openai/gpt-oss-120b, llm7:gpt-oss:20b' -> candidates (split on the first ':')."""
    out = []
    for item in (s.strip() for s in spec.split(",")):
        if ":" in item:
            provider, model = item.split(":", 1)
            out.append(Candidate(provider.strip(), model.strip()))
    return out


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_order(settings: LLMSettings, providers: dict[str, Provider], *, order_file: Path = CHAIN_ORDER_FILE,
               live_file: Path = MODELS_LIVE_FILE) -> list[Candidate]:
    """Candidate order for active providers (see module docstring)."""
    active = {pid for pid, p in providers.items() if p.active(settings)}
    if settings.llm_chain.strip():
        order = parse_candidates(settings.llm_chain)
    else:
        bench = _read_json(order_file)
        if bench and bench.get("models"):
            threshold = settings.llm_min_pass_rate
            order = [Candidate(m["provider"], m["model"]) for m in bench["models"]
                     if (m.get("responded") if threshold <= 0 else m.get("pass_rate", 0) >= threshold)]
        else:
            order = [Candidate(p.id, m) for p in providers.values() for m in p.models]
        live = _read_json(live_file)
        if live and live.get("models"):  # drop what the last check saw failing; add what it discovered
            status = {f"{m['provider']}:{m['model']}": m.get("status") for m in live["models"]}
            order = [c for c in order if status.get(c.key, "OK") == "OK"]
            if not (bench and bench.get("models")):
                known = {c.key for c in order}
                order += [Candidate(m["provider"], m["model"]) for m in live["models"]
                          if m.get("status") == "OK" and f"{m['provider']}:{m['model']}" not in known]
    seen: set[str] = set()
    result = []
    for c in order:
        if c.provider in active and c.key not in seen:
            seen.add(c.key)
            result.append(c)
    return result


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def parse_json(text: str, schema: type[T]) -> T:
    """Model text -> validated schema instance. Tolerates <think> blocks, code fences and chatter around
    a single JSON object. Raises ValueError / ValidationError."""
    text = _THINK.sub("", text or "").strip()
    if m := _FENCE.search(text):
        text = m.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in answer")
    return schema.model_validate_json(text[start:end + 1])


class Chain:
    def __init__(self, providers: list[Provider] | None = None, settings: LLMSettings | None = None, *,
                 client: httpx.Client | None = None, clock: Callable[[], float] = time.monotonic,
                 order: list[Candidate] | None = None, cache_dir: Path | None = None):
        self.settings = settings or get_llm_settings()
        self.providers = {p.id: p for p in (providers if providers is not None else load_registry())}
        self.client = client or httpx.Client()
        self.clock = clock
        self._order = order
        self.cache_dir = cache_dir
        self.disabled: set[str] = set()  # providers that answered 401/403 (until restart)
        self.blocked_until: dict[str, float] = {}  # provider -> time (429 / Retry-After)
        self.cooldown_until: dict[str, float] = {}  # candidate key -> time
        self.calls: dict[str, deque] = defaultdict(deque)  # provider -> recent call times (RPM limiter)

    # --- order and availability ---------------------------------------------------------------

    def candidates(self) -> list[Candidate]:
        order = self._order if self._order is not None else load_order(self.settings, self.providers)
        return [c for c in order if c.provider in self.providers and c.provider not in self.disabled
                and self.providers[c.provider].active(self.settings)]

    def _skip_reason(self, c: Candidate, now: float) -> str | None:
        if c.provider in self.disabled:  # also within the same request, right after a 401/403
            return "provider disabled (401/403)"
        if self.blocked_until.get(c.provider, 0) > now:
            return "rate limited (Retry-After)"
        if self.cooldown_until.get(c.key, 0) > now:
            return "cooldown"
        rpm = self.providers[c.provider].rpm
        recent = self.calls[c.provider]
        while recent and now - recent[0] >= 60:
            recent.popleft()
        if rpm and len(recent) >= rpm:
            return "RPM limit"
        return None

    def _fail(self, c: Candidate, err: ProviderError, now: float) -> None:
        if err.kind == "auth":
            self.disabled.add(c.provider)
            log.error("llm provider %s disabled until restart: %s (check %s)", c.provider, err.kind,
                      self.providers[c.provider].key_env)
        elif err.kind == "rate":
            self.blocked_until[c.provider] = now + (err.retry_after if err.retry_after is not None
                                                    else DEFAULT_RETRY_AFTER_S)
            self.cooldown_until[c.key] = now + self.settings.llm_cooldown_s
        else:
            self.cooldown_until[c.key] = now + self.settings.llm_cooldown_s

    # --- the call ---------------------------------------------------------------------------------

    def generate_json(self, prompt: str, schema: type[T], system: str | None = None, task: str = "generic",
                      validator: Callable[[T], None] | None = None) -> T:
        if not llm_enabled(self.settings):
            raise LLMUnavailable("LLM chain disabled (LLM_ENABLED=false or running under pytest)")
        candidates = self.candidates()
        if not candidates:
            raise LLMUnavailable("no active provider (no keys configured)")

        def accept(text: str) -> T:
            obj = parse_json(text, schema)
            if validator is not None:
                validator(obj)  # raises ValueError to reject (e.g. amounts of money in a dossier)
            return obj

        if self.settings.llm_cache:
            for c in candidates:
                text = cache.get(cache.cache_key(task, c.provider, c.model, system, prompt), self.cache_dir)
                if text is not None:
                    try:
                        obj = accept(text)
                        log.info("llm %s %s cache hit", task, c.key)
                        return obj
                    except (ValueError, ValidationError):
                        continue

        s = self.settings
        deadline = self.clock() + s.llm_total_budget_s
        attempts = 0
        outcomes: list[str] = []
        for c in candidates:
            if attempts >= s.llm_max_attempts or deadline - self.clock() <= MIN_REMAINING_S:
                break
            reason = self._skip_reason(c, self.clock())
            if reason:
                outcomes.append(f"{c.key}: skipped ({reason})")
                continue
            provider, ask = self.providers[c.provider], prompt
            for retry in (False, True):  # one retry on the same model, for invalid JSON only
                remaining = deadline - self.clock()
                if attempts >= s.llm_max_attempts or remaining <= MIN_REMAINING_S:
                    break
                attempts += 1
                started = self.clock()
                self.calls[c.provider].append(started)
                try:
                    text = complete(provider, c.model, ask, system, json_mode=True,
                                    timeout=min(s.llm_timeout_s, remaining), client=self.client)
                except ProviderError as err:
                    self._fail(c, err, self.clock())
                    log.warning("llm %s %s failed: %s (%.1fs)", task, c.key, err.kind, self.clock() - started)
                    outcomes.append(f"{c.key}: {err.kind}")
                    break
                try:
                    obj = accept(text)
                except (ValueError, ValidationError):
                    log.warning("llm %s %s invalid JSON%s (%.1fs)", task, c.key, " after retry" if retry else "",
                                self.clock() - started)
                    if retry:
                        self.cooldown_until[c.key] = self.clock() + s.llm_cooldown_s
                        outcomes.append(f"{c.key}: invalid JSON")
                    ask = prompt + JSON_REMINDER
                    continue
                log.info("llm %s %s ok (%.1fs)", task, c.key, self.clock() - started)
                if s.llm_cache:
                    cache.put(cache.cache_key(task, c.provider, c.model, system, prompt), text,
                              provider=c.provider, model=c.model, task=task, directory=self.cache_dir)
                return obj
        raise LLMUnavailable("; ".join(outcomes) or "budget exhausted before any attempt")


_chain: Chain | None = None


def get_chain() -> Chain:
    global _chain
    if _chain is None:
        _chain = Chain()
    return _chain


def reset_chain() -> None:
    """Forget disabled providers, cooldowns and rate limits (e.g. after editing .env)."""
    global _chain
    _chain = None


def generate_json(prompt: str, schema: type[T], system: str | None = None, task: str = "generic",
                  validator: Callable[[T], None] | None = None) -> T:
    """Contract-agnostic entry point used by structure_idea, owner_message, classify_proposal and generate_dosar."""
    return get_chain().generate_json(prompt, schema, system=system, task=task, validator=validator)
