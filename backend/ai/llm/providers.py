"""Provider registry and HTTP clients (httpx only): Gemini native API and OpenAI-compatible chat APIs.

Errors are mapped to ProviderError kinds the chain acts on: auth (401/403: disable provider),
rate (429, with Retry-After), server (5xx), timeout, network, bad_request, empty.
Nothing here logs prompts, answers or keys.
"""
import json
import re
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path

import httpx

from backend.ai.llm.settings import LLMSettings, env_value

REGISTRY_FILE = Path(__file__).with_name("registry.json")
# Catalog entries that cannot answer a chat prompt (embeddings, speech, image generation, safety filters...).
NON_CHAT = re.compile(r"embed|rerank|whisper|tts|speech|transcri|guard|safety|bge-|retriever|\bocr\b|parse|flux|"
                      r"diffusion|image-gen|imagen|veo|clip|moderation|audio", re.IGNORECASE)


class ProviderError(Exception):
    def __init__(self, kind: str, message: str = "", retry_after: float | None = None, status: int | None = None):
        super().__init__(f"{kind}: {message}"[:300])
        self.kind, self.retry_after, self.status = kind, retry_after, status


@dataclass
class Provider:
    id: str
    name: str
    kind: str  # "gemini" | "openai_compat"
    base_url: str
    key_env: str
    key_required: bool = True
    send_key: bool = True  # False: never send a key (OVH: a key switches to paid usage)
    gateway: bool = False
    models: list[str] = field(default_factory=list)
    rpm: int | None = None
    rpd: int | None = None
    status: str = "ok"
    extra_env: dict[str, str] = field(default_factory=dict)

    def key(self) -> str:
        return env_value(self.key_env) if self.send_key else ""

    def url(self) -> str | None:
        """Base URL with placeholders filled from extra_env (e.g. Cloudflare account id); None if missing."""
        url = self.base_url
        for placeholder, env in self.extra_env.items():
            value = env_value(env)
            if not value:
                return None
            url = url.replace("{" + placeholder + "}", value)
        return url.rstrip("/")

    def active(self, settings: LLMSettings) -> bool:
        if self.url() is None:
            return False
        if self.key():
            return True
        return not self.key_required and settings.llm_allow_keyless


def load_registry(path: Path = REGISTRY_FILE) -> list[Provider]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for p in doc["providers"]:
        limits = p.get("limits") or {}
        out.append(Provider(
            id=p["id"], name=p["name"], kind=p["kind"], base_url=p["base_url"], key_env=p["key_env"],
            key_required=p.get("key_required", True), send_key=p.get("send_key", True),
            gateway=p.get("gateway", False), models=list(p.get("models", [])), rpm=limits.get("rpm"),
            rpd=limits.get("rpd"), status=p.get("status", "ok"), extra_env=dict(p.get("extra_env") or {}),
        ))
    return out


def _retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        try:
            return max((parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds(), 0.0)
        except (TypeError, ValueError):
            return None


def _check(r: httpx.Response) -> None:
    if r.status_code < 400:
        return
    if r.status_code in (401, 403):
        raise ProviderError("auth", f"HTTP {r.status_code}", status=r.status_code)
    if r.status_code == 429:
        raise ProviderError("rate", "HTTP 429", _retry_after(r.headers.get("retry-after")), 429)
    if r.status_code >= 500:
        raise ProviderError("server", f"HTTP {r.status_code}", status=r.status_code)
    if r.status_code in (400, 404, 422):
        raise ProviderError("bad_request", f"HTTP {r.status_code}", status=r.status_code)
    raise ProviderError("http", f"HTTP {r.status_code}", status=r.status_code)


def _headers(p: Provider) -> dict[str, str]:
    key = p.key()
    if p.kind == "gemini":
        return {"x-goog-api-key": key} if key else {}
    return {"Authorization": f"Bearer {key}"} if key else {}


def _gemini_body(prompt: str, system: str | None, json_mode: bool) -> dict:
    body: dict = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.2}}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    return body


def _openai_body(model: str, prompt: str, system: str | None, json_mode: bool) -> dict:
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body: dict = {"model": model, "messages": messages, "temperature": 0.2}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    return body


def complete(p: Provider, model: str, prompt: str, system: str | None = None, *, json_mode: bool = True,
             timeout: float = 15.0, client: httpx.Client) -> str:
    """One request to one model; returns the text answer or raises ProviderError."""
    base = p.url()
    if base is None:
        raise ProviderError("config", "base URL placeholder not configured")
    try:
        if p.kind == "gemini":
            r = client.post(f"{base}/models/{model}:generateContent", headers=_headers(p),
                            json=_gemini_body(prompt, system, json_mode), timeout=timeout)
            _check(r)
            parts = (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts") or []
            text = "".join(part.get("text", "") for part in parts)
        else:
            body = _openai_body(model, prompt, system, json_mode)
            r = client.post(f"{base}/chat/completions", headers=_headers(p), json=body, timeout=timeout)
            if r.status_code == 400 and json_mode:  # some providers reject response_format: retry plain once
                body.pop("response_format", None)
                r = client.post(f"{base}/chat/completions", headers=_headers(p), json=body, timeout=timeout)
            _check(r)
            choice = (r.json().get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
    except httpx.TimeoutException as exc:
        raise ProviderError("timeout", type(exc).__name__) from exc
    except httpx.HTTPError as exc:
        raise ProviderError("network", type(exc).__name__) from exc
    except (ValueError, KeyError, IndexError, AttributeError) as exc:  # unexpected response shape
        raise ProviderError("bad_response", type(exc).__name__) from exc
    if not text.strip():
        raise ProviderError("empty", "no text in response")
    return text


def _is_free(p: Provider, item: dict) -> bool:
    """Gateways also list paid models: keep only the free ones."""
    if p.id not in ("openrouter", "kilo"):
        return True
    model_id = str(item.get("id", ""))
    if model_id.endswith(":free") or model_id.endswith("/free"):
        return True
    pricing = item.get("pricing") or {}
    try:
        return bool(pricing) and all(float(pricing.get(k, 1)) == 0 for k in ("prompt", "completion"))
    except (TypeError, ValueError):
        return False


def list_models(p: Provider, *, client: httpx.Client, timeout: float = 15.0) -> list[str]:
    """Free chat models the provider's listing endpoint reports (no prompt sent)."""
    base = p.url()
    if base is None:
        return []
    try:
        r = client.get(f"{base}/models", headers=_headers(p), timeout=timeout)
        _check(r)
        doc = r.json()
    except httpx.TimeoutException as exc:
        raise ProviderError("timeout", type(exc).__name__) from exc
    except httpx.HTTPError as exc:
        raise ProviderError("network", type(exc).__name__) from exc
    except ValueError as exc:
        raise ProviderError("bad_response", type(exc).__name__) from exc
    if p.kind == "gemini":
        ids = [m.get("name", "").removeprefix("models/") for m in doc.get("models", [])
               if "generateContent" in (m.get("supportedGenerationMethods") or [])]
    else:
        items = doc.get("data", doc if isinstance(doc, list) else [])
        ids = [str(m.get("id", "")) for m in items if isinstance(m, dict) and _is_free(p, m)]
    return [i for i in dict.fromkeys(ids) if i and not NON_CHAT.search(i)]
