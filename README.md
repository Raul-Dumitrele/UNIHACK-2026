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
