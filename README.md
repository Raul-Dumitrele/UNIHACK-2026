# Loc Comun
Găsești un teren liber în Timișoara, spui ce vrei acolo (skatepark, loc de joacă, grădină...), iar aplicația generează un proiect complet: dosar, cost estimat din proiecte reale, plan schematic (SVG și DXF pentru AutoCAD), listă de materiale cu prețuri SEAP, dosar PDF. Proiectul merge la Primărie, apoi la un verificator, care dă acord de principiu (simulat), cere clarificări sau respinge.
UniHack 2026.

## Structură
- `backend/` FastAPI + SQLModel (`app/` P1, `ai/` `impact/` `seed/` P3)
- `web/` React + Vite + TS (P2)
- `mobile/` Expo + TS (P2, pe pauză)
- `docs/` contract (`CONTRACT.md`), `ARCHITECTURE.md`, `openapi.json`, `DATA.md`
- `tests/e2e/` (P3)

## Pornire
Din rădăcina repo-ului. Variabile: copiază `.env.example` în `.env` și completează `GEMINI_API_KEY` (opțional; fără cheie merge pe varianta de rezervă). `GEMINI_MODEL` are implicit `gemini-3.5-flash-lite`.

Windows (PowerShell):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1   # venv, dependențe, hook-uri, .env
powershell -ExecutionPolicy Bypass -File scripts/seed.ps1    # date demo (terenuri, utilizatori, proiect exemplu)
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1     # API pe http://localhost:8000 (/docs)
powershell -ExecutionPolicy Bypass -File scripts/test.ps1    # teste backend P1
powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1   # seed, /health, documente, e2e, build web
```

macOS / Linux:
```sh
sh scripts/setup.sh && sh scripts/seed.sh && sh scripts/dev.sh
sh scripts/test.sh
sh scripts/smoke.sh
```

Web (alt terminal): `cd web && npm install && npm run dev` -> http://localhost:5173 (`web/.env`: `VITE_USE_MOCKS=false` pentru API-ul real).
Cu `make`: `make setup | seed | dev | test | smoke | openapi`. După o schimbare de contract: `make openapi`, apoi în web `npm run gen:types`.
Ramuri: `p1-backend`, `p2-front`, `p3-data-ai`; hook-ul pre-commit blochează fișierele din afara zonei ramurii.

## Repetiție de demo
Fă-o de două ori, pe `main` la zi:
1. **Fără chei** (cum ar fi dacă pică internetul sau cheia): în `.env` lasă `GEMINI_API_KEY=` gol și pune `REFERENCES_LIVE_SEARCH=false`. Dosarul iese din șablon, AI-ul de structurare din reguli; totul trebuie să meargă.
2. **Cu cheie**: completează `GEMINI_API_KEY`, păstrează `REFERENCES_LIVE_SEARCH=false` (căutarea live poate dura până la un minut).

Scenariu (schimbi utilizatorul din dreapta sus):
1. Cetățean (`demo-user-1`): hartă -> alege un teren sau marchează unul nou -> propune un proiect (ex. loc de joacă) -> vezi dosarul, costul, planul, materialele, descarcă PDF/DXF -> trimite la Primărie.
2. Primărie (`demo-user-9`): proiectul apare la „Proiecte primite” -> înaintează la verificator.
3. Verificator (`demo-user-10`): acord de principiu / clarificări / respins (cu mesaj).
4. Cetățeanul vede notificarea și istoricul; Impact arată proiectele trimise și cu acord.

De spus cinstit la prezentare: terenurile sunt candidate (proprietarul și regimul juridic le confirmă Primăria); cele 15 din lista Primăriei sunt loturi Legea 15/2003 (locuințe pentru tineri); costul e o estimare din proiecte de referință; planul e o schiță, nu un proiect tehnic; acordul e simulat.

## Deploy backend (Render sau Railway)
- Build: `pip install -r backend/requirements.txt`
- Start: `python -m backend.seed.run && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Variabile: `PYTHON_VERSION=3.12`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `CORS_ORIGINS` (URL-ul web, fără `/` final), `DATABASE_URL` (implicit SQLite), `REFERENCES_LIVE_SEARCH=false`.
- SQLite se resetează la fiecare redeploy; seed-ul rulează la pornire (acceptat pentru demo).
- Verifică `/health` și `/docs` pe URL-ul public. Pe Render/Railway nu se aplică wheel-ul pur-Python din `setup.ps1` (doar Windows).
