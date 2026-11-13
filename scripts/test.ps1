# Run P1 backend tests. Run from repo root.
Push-Location backend
try { .venv/Scripts/python -m pytest tests/app; exit $LASTEXITCODE } finally { Pop-Location }
