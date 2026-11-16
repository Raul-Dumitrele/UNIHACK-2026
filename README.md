# Loc Comun
Găsești un teren liber în Timișoara, spui ce vrei acolo (skatepark, loc de joacă, grădină...), iar aplicația generează un proiect complet: dosar, cost estimat din proiecte reale, plan schematic (SVG și DXF pentru AutoCAD), listă de materiale cu prețuri SEAP, dosar PDF. Proiectul merge la Primărie, apoi la un verificator, care dă acord de principiu (simulat), cere clarificări sau respinge.
UniHack 2026.

## Structură
- `backend/` FastAPI + SQLModel (`app/` P1, `ai/` `impact/` `seed/` P3)
- `web/` React + Vite + TS (P2)
- `mobile/` Expo + TS (P2, pe pauză)
- `docs/` contract (`CONTRACT.md`), `ARCHITECTURE.md`, `openapi.json`, `DATA.md`
- `tests/e2e/` (P3)

## Pornire rapidă pentru demo (macOS, Node 22 prin nvm)
Toate comenzile se dau din rădăcina repo-ului. Ai nevoie de două terminale.

**O singură dată** (instalare):
```sh
sh scripts/setup.sh                              # venv Python, dependențe, hook-uri, .env
cp -n web/.env.example web/.env                  # setările web (nu suprascrie un fișier existent)
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 22
cd web && npm install && cd ..
```

### Modul A – cu backend real (recomandat)
Terminal 1 (backend, http://localhost:8000, documentație la `/docs`):
```sh
sh scripts/seed.sh                               # date demo: 24 de terenuri, utilizatori, un proiect exemplu
sh scripts/dev.sh                                # lasă-l pornit
```
Terminal 2 (cazurile de demo, apoi web pe http://localhost:5173):
```sh
backend/.venv/bin/python scripts/demo_cases.py   # 6 proiecte pregătite prin API (vezi „Repetiție de demo”)
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 22
cd web && VITE_USE_MOCKS=false npm run dev
```
Fără cheie `GEMINI_API_KEY` în `.env` aplicația merge pe varianta deterministă (dosarul iese din șablon); totul funcționează.

### Modul B – fără backend (mod demonstrativ)
Un singur terminal; răspunsurile vin dintr-un instantaneu al API-ului real (`web/src/mocks/data`):
```sh
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 22
cd web && VITE_USE_MOCKS=true npm run dev        # http://localhost:5173
```
Limite ale modului demonstrativ, de știut înainte:
- ce creezi dispare la reîncărcarea paginii (F5); navighează din meniu, nu din bara de adrese;
- un proiect nou primește dosarul, planul și materialele proiectului-exemplu de același tip (nu sunt recalculate pentru terenul ales);
- cartierul nu schimbă scorul terenurilor, iar un tip de amenajare scris liber e recunoscut după câteva cuvinte-cheie.
Pentru prezentare folosește Modul A; Modul B e planul de rezervă.

### Oprire și repornire
- Oprire: `Ctrl+C` în fiecare terminal.
- Repornire cu aceleași date: `sh scripts/dev.sh` (terminal 1) și `cd web && VITE_USE_MOCKS=false npm run dev` (terminal 2).
- Bază de date curată: oprește backend-ul, mută `loccomun.db` în altă parte (`mv loccomun.db loccomun.vechi.db`), apoi
  `sh scripts/seed.sh`, `sh scripts/dev.sh` și din nou `backend/.venv/bin/python scripts/demo_cases.py`.
- „Server indisponibil” în colțul din dreapta sus înseamnă că backend-ul nu rulează sau rulează pe alt port.

### Verificări
```sh
backend/.venv/bin/python -m pytest backend/tests tests/e2e -q    # toate testele backend, AI, seed, e2e
sh scripts/smoke.sh                                              # seed, /health, documente, e2e, build web
cd web && npm test && npm run build && npm run lint              # test web, build (cu tsc), lint
```

### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
powershell -ExecutionPolicy Bypass -File scripts/seed.ps1
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```
Web: `cd web; npm install; $env:VITE_USE_MOCKS="false"; npm run dev`.

Cu `make`: `make setup | seed | dev | test | smoke | openapi`. După o schimbare de contract: `make openapi`, apoi în web `npm run gen:types`.
Ramura de lucru din 15.11 este `solo` (o singură persoană modifică toate zonele; hook-ul pre-commit verifică doar secretele).

## Ce face aplicația (pe scurt)
1. Hartă cu terenuri libere (lista Primăriei, candidați OSM, terenuri marcate de locuitori) + „Marchează un teren”.
2. Wizard: ce vrei -> terenuri potrivite (scor + motiv) -> **analiză de fezabilitate** (realist / atenție / nerealist, cu motive).
3. Proiect complet: memoriu pe capitole, specificație tehnică, cost (interval din referințe + suma articolelor cu preț), etape,
   riscuri, documente și avize necesare cu temei legal, cereri-tip, referințe; planșe A3 (PDF) și DXF, vedere 3D, listă de
   materiale XLSX/CSV cu sursa fiecărui preț (SEAP / plafon / catalog / de cotat).
4. Publicare -> vot (un vot per persoană) -> la 3 susținători ajunge automat la Primărie -> verificator -> decizie; notificări.
5. Tablou de impact: terenuri, proiecte, voturi, oameni implicați, trimise, cu acord.

## Repetiție de demo
`scripts/demo_cases.py` pregătește prin API șase proiecte (rulează-l după seed; sare peste cele care există deja):

| Caz | Ce arată | Stare |
|---|---|---|
| Loc de joacă, teren candidat din Mehala | cazul pozitiv: analiză, teren, dosar, cost, planșă | publicat, un susținător |
| Skatepark, Tipografilor | vot -> prag atins -> Primărie -> verificator | acord de principiu (simulat) |
| Parc acvatic, Bucovina | aplicația spune cinstit ce nu știe: nerealist pe teren, cost total neestimabil, suma parțială separat | publicat |
| Teren de sport / grădină comunitară / pistă de biciclete | restul stărilor | ciornă / clarificări cerute / respins |

Scenariu de 3–4 minute (rolul se schimbă din „Văd aplicația ca”, dreapta sus):
1. **Ana Popescu (locuitor)** – Hartă -> „Propune un proiect” -> „Loc de joacă”, o frază, cartier „Mehala” -> „Analizează ideea”.
   Arată „Am interpretat propunerea ca…”, apoi terenurile cu scor și motiv, apoi verificarea pe teren -> „Generează proiectul”.
2. Pe pagina proiectului: Rezumat (este realist?, cât ar putea costa, terenul), apoi „Planșe și materiale” (plan, 3D, PDF A3, DXF,
   listă de materiale cu prețuri SEAP și articole „de cotat”) și „Avize și cereri”.
3. „Publică pentru vot”; **Mihai, Ioana, Andrei** apasă „Susțin proiectul” -> la al treilea vot proiectul pleacă singur la Primărie.
4. **Cont demo Primărie** -> Proiecte -> „Înaintează”; **Cont demo verificator** -> „Acord de principiu” -> „Trimite decizia”.
5. **Ana** -> Notificări, apoi Impact.
6. Cazul cinstit: Comunitate -> „parc acvatic”: „Nerealistă pe acest teren”, „Cost total: nu poate fi estimat din datele disponibile”,
   suma parțială marcată ca atare. Sau scrie „ceva frumos pentru copii” în wizard: aplicația cere o descriere mai concretă.

Repetă o dată fără cheie (`GEMINI_API_KEY=` gol, `REFERENCES_LIVE_SEARCH=false`) și, dacă ai chei, o dată cu ele
(păstrează `REFERENCES_LIVE_SEARCH=false`: căutarea live poate dura până la un minut).

Limite de spus cinstit la prezentare:
- prețurile sunt parțiale: doar articolele cu cel puțin 3 achiziții directe în SEAP au preț; restul sunt „de cotat”, iar suma lor nu e costul proiectului;
- intervalul de cost există doar unde sunt cel puțin două proiecte de referință cu cost și suprafață publicate;
- terenurile din OpenStreetMap sunt candidați neconfirmați (proprietar, regim juridic și disponibilitate necunoscute);
- cele 15 terenuri din lista Primăriei sunt loturi Legea 15/2003 (locuințe pentru tineri): folosirea lor cere o hotărâre a Consiliului Local;
- acordul de principiu este simulat în aplicație, nu o aprobare reală;
- planșele și planul sunt schițe orientative, nu documentație tehnică; dimensiunile sunt ipoteze ale aplicației;
- lista de avize e orientativă: lista reală o stabilește certificatul de urbanism; aplicația nu garantează obținerea lor;
- totul depinde de datele publice disponibile (SEAP pe data.gov.ro, OpenStreetMap, HCL 20/2019).

## Deploy backend (Render sau Railway)
- Build: `pip install -r backend/requirements.txt`
- Start: `python -m backend.seed.run && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Variabile: `PYTHON_VERSION=3.12`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `CORS_ORIGINS` (URL-ul web, fără `/` final), `DATABASE_URL` (implicit SQLite), `REFERENCES_LIVE_SEARCH=false`.
- SQLite se resetează la fiecare redeploy; seed-ul rulează la pornire (acceptat pentru demo).
- Verifică `/health` și `/docs` pe URL-ul public. Pe Render/Railway nu se aplică wheel-ul pur-Python din `setup.ps1` (doar Windows).
