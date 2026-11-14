#!/bin/sh
# Run P1 backend tests. Run from repo root. macOS/Linux.
cd backend && exec .venv/bin/python -m pytest tests/app
