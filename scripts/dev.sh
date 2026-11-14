#!/bin/sh
# Start the backend on http://localhost:8000 (docs at /docs). Run from repo root. macOS/Linux.
exec backend/.venv/bin/python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
