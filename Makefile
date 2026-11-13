.PHONY: setup dev test smoke openapi

PY := backend/.venv/Scripts/python

setup:
	powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

dev:
	$(PY) -m uvicorn backend.app.main:app --reload --port 8000

test:
	cd backend && .venv/Scripts/python -m pytest tests/app

smoke:
	powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1

openapi:
	$(PY) scripts/export_openapi.py
