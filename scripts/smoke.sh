#!/bin/sh
# Seed the demo data, start the API, check /health and the demo project's documents, then optional e2e and
# web checks. Stops at the first error. Run from repo root. macOS/Linux.
set -e
PY=backend/.venv/bin/python
"$PY" -m backend.seed.run >/dev/null && echo "[OK] seed"
"$PY" -m uvicorn backend.app.main:app --port 8765 >/dev/null 2>&1 &
API=$!
trap 'kill $API 2>/dev/null' EXIT
for i in $(seq 1 30); do sleep 0.5; curl -sf http://127.0.0.1:8765/health >/dev/null && break; done
curl -sf http://127.0.0.1:8765/health >/dev/null || { echo "[FAIL] /health"; exit 1; }
echo "[OK] /health"
for doc in plan.svg plan.dxf dosar.pdf materiale.csv; do
  size=$(curl -sf -H "X-User-Id: demo-user-5" -o /dev/null -w "%{size_download}" \
    "http://127.0.0.1:8765/proiecte/demo-proiect-1/documente/$doc") || { echo "[FAIL] document $doc"; exit 1; }
  [ "$size" -ge 100 ] || { echo "[FAIL] document $doc"; exit 1; }
done
echo "[OK] documents (plan.svg, plan.dxf, dosar.pdf, materiale.csv)"
if [ -f tests/e2e/run.sh ]; then sh tests/e2e/run.sh && echo "[OK] e2e"; fi
if [ -d web ]; then (cd web && npm run build >/dev/null && npx tsc --noEmit) && echo "[OK] web build + tsc"; fi
