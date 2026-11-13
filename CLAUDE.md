# Loc Comun - UniHack 2026

## Obiectiv
Idee -> dosar structurat de AI -> spații libere potrivite -> interes din comunitate -> aprobare rezervare de către proprietar -> tablou de impact.

## Monorepo și zone (fiecare modifică doar zona sa)
- P1 (Raul): CLAUDE.md, README.md, Makefile, .gitignore, .env.example, scripts/, .githooks/, docs/CONTRACT.md, docs/openapi.json, backend/__init__.py, backend/pytest.ini, backend/app/, backend/requirements.txt, backend/tests/app/
- P2: web/ (React + Vite + TS), mobile/ (Expo + TS)
- P3: backend/ai/, backend/impact/, backend/seed/, backend/tests/ai/, backend/tests/seed/, tests/e2e/, docs/DATA.md

## Stack
Python 3.11+ (FastAPI + SQLModel, SQLite) | React + Vite + TS | Expo + TS | Gemini (google-genai, cheie în .env, cu fallback fără Gemini).

## Reguli
1. Contractul e docs/CONTRACT.md; nu-l schimba fără acordul echipei. După schimbare: `make openapi`, apoi tipurile TS se regenerează din docs/openapi.json
2. Datele demo au `is_demo=true` și insigna „exemplu” în UI; utilizatorul demo vine din header `X-User-Id`
3. Notificările în aplicație la schimbarea stării ideii/rezervării fac parte din proiect
4. Fără chei în repo (.env e ignorat; hook-ul pre-commit blochează .env și chei)
5. UI în română; cod și commit-uri în engleză; commit-uri mici, o ramură per persoană
6. Proiectul vechi („Semnal”) e abandonat; codul lui e doar în tag-ul git `arhiva-semnal`

## Comenzi (din rădăcină)
scripts/setup.ps1 | scripts/dev.ps1 | scripts/test.ps1 | scripts/smoke.ps1 | make openapi

## Cum lucrezi
Plan înainte de cod. Referă fișiere precise. Răspunsuri scurte.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
