from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str = f"sqlite:///{ROOT / 'loccomun.db'}"
    gemini_api_key: str = ""
    cors_origins: str = "http://localhost:5173"

    @field_validator("database_url")
    @classmethod
    def _anchor_sqlite(cls, v: str) -> str:
        # Relative SQLite paths resolve from the repo root, not the current directory.
        prefix = "sqlite:///./"
        return f"sqlite:///{(ROOT / v[len(prefix):]).as_posix()}" if v.startswith(prefix) else v

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
