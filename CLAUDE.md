# Semnal (nume de lucru) - UniHack 2026, track Nokia Connected Communities

## Obiectiv
Alerte personalizate, pe clădire / linie / stație, pentru întreruperi de utilități (căldură, apă, curent) și devieri de transport din Timișoara.
Flux: anunțuri reale -> date structurate -> hartă -> abonare -> alertă.
Plus: "ce deservește efectiv stația X acum" (GTFS minus alerte plus vehicule live), cu stații fantomă și alternative.
Provocări: CH-08 + CH-09 (docs/challenges.md). Livrăm modul compatibil cu Timișoara City App (API REST + widget + endpoint pentru Timi).

## Foldere (fiecare persoană își are zona)
- backend/  : ingestie, OCR, extracție LLM cu încredere, geocodare, API
- frontend/ : PWA mobil-first, hartă, abonări, machetă City App
- transit/  : GTFS + alerte + vehicule live, stații fantomă, evaluare
- data/     : mock și snapshot-uri cu date reale
- docs/     : context și contracte (citește doar ce ai nevoie)

## Stack (propus, de confirmat în plan)
Python 3.11 + FastAPI | React + Vite (PWA) + MapLibre | SQLite (Postgres+PostGIS dacă e nevoie) | LLM prin API (cheie în .env) | OSM Nominatim/Overpass.

## Reguli
1. Doar software, doar date reale; orice simulare e marcată clar în demo
2. Extracția LLM întoarce JSON cu câmpul `incredere` (0-1), `sursa` (URL) și `necitit`; se abține când nu e sigură
3. STPT: endpoint-uri nedocumentate (docs/stpt-endpoints.md); cache, rate-limit mic, snapshot în data/ pentru demo
4. Contractul JSON dintre module e în docs/api-contract.md; UI-ul lucrează pe mock din data/
5. Fără chei în repo (.env e în .gitignore); commit-uri mici; o ramură per persoană
6. UI în română (engleză opțional); cod și commit-uri în engleză
7. Nu extinde scope-ul; MVP-ul: 10 anunțuri reale -> hartă -> abonare -> alertă -> stație fantomă

## Cum lucrezi
Plan înainte de cod. Referă fișiere precise. Răspunsuri scurte.
## Documente
- docs/brief.md: componente, echipa, plan pe ore, demo, plan B
- docs/challenges.md, docs/stpt-endpoints.md
- scripts/check_connections.py: verifica uneltele, cheile ?i accesul la date

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
