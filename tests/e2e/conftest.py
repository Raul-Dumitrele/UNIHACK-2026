"""E2E setup: temporary SQLite + seed + in-process ASGI client. Run from the repo root:
    python -m pytest tests/e2e        (or tests/e2e/run.ps1 / run.sh)
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Must happen before anything imports backend.app: its engine is built from settings at import time.
_TMP = Path(tempfile.mkdtemp(prefix="loccomun-e2e-"))
E2E_DB_URL = "sqlite:///" + (_TMP / "e2e.db").as_posix()
# If this suite imports backend.app first, its own engine gets a separate throwaway file: e2e data lives
# only in E2E_ENGINE, so a suite that resets the app database (backend/tests/app) cannot wipe it.
os.environ["DATABASE_URL"] = "sqlite:///" + (_TMP / "app-unused.db").as_posix()
os.environ["GEMINI_API_KEY"] = ""  # always the deterministic fallback; overrides .env
os.environ["REFERENCES_LIVE_SEARCH"] = "false"  # e2e never reaches the web

import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

import backend.app.db as app_db  # noqa: E402
from backend.app import models  # noqa: E402,F401  (registers the contract tables)
from backend.app.main import app  # noqa: E402
from backend.seed.build import build_seed  # noqa: E402
from backend.seed.run import seed  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# Own engine for this suite. The app gets it through FastAPI dependency overrides in `client`, so
# nothing global changes: other suites in the same run (backend/tests/app) keep their own database.
E2E_ENGINE = create_engine(E2E_DB_URL, connect_args={"check_same_thread": False})


@pytest.fixture(scope="session", autouse=True)
def seed_data():
    SQLModel.metadata.create_all(E2E_ENGINE)
    data = build_seed()
    with Session(E2E_ENGINE) as session:
        seed(session, data)
    yield data
    E2E_ENGINE.dispose()
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture
def e2e_engine():
    return E2E_ENGINE


def _e2e_session():
    with Session(E2E_ENGINE) as session:
        yield session


@pytest.fixture
async def client():
    # ASGITransport skips lifespan; the tables already exist (seed_data).
    app.dependency_overrides[app_db.get_session] = _e2e_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(app_db.get_session, None)


def as_user(user_id: str) -> dict[str, str]:
    return {"X-User-Id": user_id}
