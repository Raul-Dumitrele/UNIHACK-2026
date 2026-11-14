"""Answer cache on disk: backend/ai/llm/cache/<sha256>.json (ignored by git).

Key = hash(task + provider + model + system + prompt). Used so demos replay without live APIs
(python -m backend.ai.llm.pregenerate). Stores only the model's text answer for demo data.
"""
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(__file__).with_name("cache")


def cache_key(task: str, provider: str, model: str, system: str | None, prompt: str) -> str:
    raw = "\x1f".join([task, provider, model, system or "", prompt])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get(key: str, directory: Path | None = None) -> str | None:
    path = (directory or CACHE_DIR) / f"{key}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))["text"]
    except (OSError, ValueError, KeyError):
        return None


def put(key: str, text: str, *, provider: str, model: str, task: str, directory: Path | None = None) -> None:
    directory = directory or CACHE_DIR
    try:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{key}.json").write_text(
            json.dumps({"task": task, "provider": provider, "model": model, "text": text}, ensure_ascii=False),
            encoding="utf-8")
    except OSError:
        pass  # the cache is an optimisation; never fail a request because of it
