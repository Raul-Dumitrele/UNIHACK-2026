"""AI settings, read from the repo .env (own class: backend.app Settings has no model field)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "gemini-3.5-flash-lite"
MIN_TIMEOUT_MS = 10_000  # Gemini API rejects deadlines under 10 s


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = DEFAULT_MODEL
    gemini_timeout_ms: int = MIN_TIMEOUT_MS
    # Live web search for reference projects and project notes (Gemini + Google Search). Needs the key;
    # REFERENCES_LIVE_SEARCH=false turns it off (tests, offline demos).
    references_live_search: bool = True


def get_settings() -> AISettings:
    """Read fresh each call so tests and .env edits take effect without restarts."""
    s = AISettings()
    if not s.gemini_model.strip():
        s.gemini_model = DEFAULT_MODEL
    s.gemini_timeout_ms = max(s.gemini_timeout_ms, MIN_TIMEOUT_MS)
    return s
