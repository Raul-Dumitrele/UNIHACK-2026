#!/bin/sh
# Load the demo data (idempotent, offline). Run from repo root. macOS/Linux.
exec backend/.venv/bin/python -m backend.seed.run
