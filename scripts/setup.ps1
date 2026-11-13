# One-time local setup: venv + backend deps + git hooks. Run from repo root.
$ErrorActionPreference = "Stop"
if (-not (Test-Path backend/.venv)) { python -m venv backend/.venv }
backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
git config core.hooksPath .githooks
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env from .env.example - set GEMINI_API_KEY" }
