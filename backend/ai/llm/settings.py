"""Settings for the LLM chain, read from the repo .env (own class; backend/app/config.py is P1's).

Provider keys (<NAME>_API_KEY, see registry.json) are read by name through env_value(), never logged.
"""
import os
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT / ".env"


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    llm_enabled: bool | None = None  # None: on, except inside pytest (tests never call providers)
    llm_chain: str = ""  # override: "groq:openai/gpt-oss-120b,gemini:gemini-3.5-flash-lite"
    llm_timeout_s: float = 15.0  # per request
    llm_total_budget_s: float = 20.0  # per generate_json call, all attempts together
    llm_max_attempts: int = 4
    llm_min_pass_rate: float = 0.7  # bench threshold; 0 = every model that answers
    # Providers that work without a key (LLM7, Kilo, OVH). Off by default, so a fresh checkout only calls
    # providers whose key is in .env; set LLM_ALLOW_KEYLESS=true to add them.
    llm_allow_keyless: bool = False
    llm_cache: bool = True
    llm_cooldown_s: float = 300.0  # a model that failed is skipped this long


def get_llm_settings() -> LLMSettings:
    return LLMSettings()


def llm_enabled(settings: LLMSettings) -> bool:
    if settings.llm_enabled is not None:
        return settings.llm_enabled
    return "PYTEST_CURRENT_TEST" not in os.environ


@lru_cache(maxsize=4)
def _dotenv(mtime: float) -> dict[str, str]:
    return {k: v or "" for k, v in dotenv_values(ENV_FILE).items()} if ENV_FILE.exists() else {}


def env_value(name: str) -> str:
    """Process environment first (also when set to ""), then the .env file. Never printed."""
    if name in os.environ:
        return os.environ[name].strip()
    mtime = ENV_FILE.stat().st_mtime if ENV_FILE.exists() else 0.0
    return _dotenv(mtime).get(name, "").strip()
