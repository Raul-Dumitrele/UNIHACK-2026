# Loc Comun
Idee -> dosar structurat de AI -> spații libere potrivite -> interes din comunitate -> aprobare rezervare de către proprietar -> tablou de impact.
UniHack 2026.

## Structură
- `backend/` FastAPI + SQLModel (`app/` P1, `ai/` `impact/` `seed/` P3)
- `web/` React + Vite + TS (P2)
- `mobile/` Expo + TS (P2)
- `docs/` contract (`CONTRACT.md`), `ARCHITECTURE.md`, `openapi.json`, `DATA.md`
- `tests/e2e/` (P3)

## Pornire (Windows, PowerShell, din rădăcina repo-ului)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1   # venv, dependențe, hook-uri, .env
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1     # API pe http://localhost:8000 (/docs)
powershell -ExecutionPolicy Bypass -File scripts/test.ps1    # teste backend P1
powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1   # /health, apoi e2e și build web dacă există
.\backend\.venv\Scripts\python scripts/export_openapi.py     # regenerează docs/openapi.json
```
Ramuri: `p1-backend`, `p2-front`, `p3-data-ai`; hook-ul pre-commit blochează fișierele din afara zonei ramurii.
Cu `make`: `make setup | dev | test | smoke | openapi`.

Variabile: copiază `.env.example` în `.env` și completează `GEMINI_API_KEY` (`GEMINI_MODEL` are implicit `gemini-flash-latest`).

## Deploy backend (Render sau Railway)
- Build: `pip install -r backend/requirements.txt`
- Start: `python -m backend.seed.run && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Variabile: `PYTHON_VERSION=3.12`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `CORS_ORIGINS` (URL-ul web al lui P2, fără `/` final), `DATABASE_URL` (implicit SQLite).
- SQLite se resetează la fiecare redeploy; seed-ul rulează la pornire (datele reale se pierd, acceptat pentru demo).
- Verifică `/health` și `/docs` pe URL-ul public. Pe Render/Railway nu se aplică wheel-ul pur-Python din `setup.ps1` (doar Windows).
- `python -m backend.seed.run` vine de la P3 (încă pe `origin/p3`, nu pe main).
