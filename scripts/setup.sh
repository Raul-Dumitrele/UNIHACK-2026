#!/bin/sh
# One-time local setup on macOS/Linux: venv + backend deps + git hooks + .env. Run from repo root.
set -e
PYTHON=${PYTHON:-python3}
[ -d backend/.venv ] || "$PYTHON" -m venv backend/.venv
backend/.venv/bin/python -m pip install -q --upgrade pip
backend/.venv/bin/python -m pip install -q -r backend/requirements.txt
backend/.venv/bin/python -c "import sqlalchemy, sqlmodel; print('sqlalchemy', sqlalchemy.__version__, 'ok')"
git config core.hooksPath .githooks
[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example - set GEMINI_API_KEY"; }
echo "Setup done. Next: sh scripts/seed.sh && sh scripts/dev.sh"
