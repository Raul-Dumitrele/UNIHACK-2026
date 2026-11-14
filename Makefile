.PHONY: setup dev test smoke openapi seed

# Windows venv uses Scripts/, macOS/Linux use bin/.
ifeq ($(OS),Windows_NT)
PY := backend/.venv/Scripts/python
SH := powershell -ExecutionPolicy Bypass -File scripts/$(1).ps1
else
PY := backend/.venv/bin/python
SH := sh scripts/$(1).sh
endif

setup:
	$(call SH,setup)

dev:
	$(PY) -m uvicorn backend.app.main:app --reload --port 8000

test:
	$(call SH,test)

smoke:
	$(call SH,smoke)

seed:
	$(PY) -m backend.seed.run

openapi:
	$(PY) scripts/export_openapi.py
