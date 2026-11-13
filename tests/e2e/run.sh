#!/bin/sh
# Wrapper for: python -m pytest tests/e2e (uses the backend venv). Works from any directory.
set -e
root="$(cd "$(dirname "$0")/../.." && pwd)"
for py in "$root/backend/.venv/Scripts/python.exe" "$root/backend/.venv/bin/python"; do
  if [ -x "$py" ]; then cd "$root" && exec "$py" -m pytest tests/e2e "$@"; fi
done
echo "backend venv not found; run scripts/setup first" >&2
exit 1
