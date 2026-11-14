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
os.environ["DATABASE_URL"] = "sqlite:///" + (_TMP / "e2e.db").as_posix()
os.environ["GEMINI_API_KEY"] = ""  # always the deterministic fallback; overrides .env
os.environ["REFERENCES_LIVE_SEARCH"] = "false"  # e2e never reaches the web

import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlmodel import Session  # noqa: E402

from backend.app.db import engine, init_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.seed.build import build_seed  # noqa: E402
from backend.seed.run import seed  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def seed_data():
    assert engine.url.database == (_TMP / "e2e.db").as_posix(), "e2e must never touch the dev database"
    init_db()
    data = build_seed()
    with Session(engine) as session:
        seed(session, data)
    yield data
    engine.dispose()
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture
async def client():
    # ASGITransport skips lifespan; init_db() already ran in seed_data.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def as_user(user_id: str) -> dict[str, str]:
    return {"X-User-Id": user_id}
