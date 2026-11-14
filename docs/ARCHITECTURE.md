# Arhitectură - Loc Comun

## Straturi
- **Clienți** (P2): `web/` (React + Vite + TS) și `mobile/` (Expo + TS). Tipurile TS se generează din `docs/openapi.json`.
- **API** (P1): `backend/app/` FastAPI. `routers/` (HTTP, validare), `schemas.py` (cereri/răspunsuri), `models.py` (tabele SQLModel), `db.py`, `config.py`.
- **Module P3**: `backend/ai/` (Gemini + fallback), `backend/impact/`, `backend/seed/`. P1 le importă prin `backend/app/p3.py` (real dacă există, altfel `stubs/`).
- **Date**: SQLite. Câmpurile complexe (dotari, sloturi, structurat) sunt JSON.

## Flux pas cu pas
1. `POST /ideas` -> `ai.structure_idea` -> idee `deschisa` cu dosar structurat.
2. `GET /ideas/{id}/matches` -> scor 0-100 și motiv per spațiu.
3. `POST /ideas/{id}/interest` -> la prag, idee `prag_atins` + notificare autor.
4. `POST /ideas/{id}/owner-message` -> mesaj pentru proprietar (`ai.owner_message`).
5. `POST /bookings` -> cerere `cerut` + notificare proprietar.
6. `PATCH /bookings/{id}` -> proprietarul aprobă/refuză; la aprobare: idee `rezervata`, slot scos, cereri suprapuse refuzate, notificare autor.
7. `GET /impact` -> `impact.compute_impact`.

## Extensia „Propunere către Primărie”
8. `POST /ideas/{id}/proiect` -> `find_references` -> `estimate_cost` -> `generate_dosar` -> proiect `draft`.
9. `POST /proiecte/{id}/trimite` -> `trimis` (notifică utilizatorii `primarie`).
10. `POST /proiecte/{id}/inainteaza` -> `in_verificare` (primarie desemnează un `verificator`).
11. `POST /proiecte/{id}/decizie` -> `acord_de_principiu` | `respins` | `clarificari` (verificatorul desemnat).
Roluri noi: `primarie`, `verificator`. Acordul e un acord de principiu simulat; estimările sunt orientative.

## Reguli de stare
- Proiect: `draft` -> `trimis` -> `in_verificare` -> `acord_de_principiu` | `respins` | `clarificari`; `clarificari` -> `trimis` (autorul retrimite). Fiecare tranziție scrie un `ProiectEveniment`.
- Idee: `deschisa` -> `prag_atins` (interesati >= prag) -> `rezervata` (rezervare aprobată).
- Rezervare: `cerut` -> `aprobat` | `refuzat` (final).
- Notificare la fiecare tranziție; doar în aplicație.

## Zone (fiecare modifică doar zona sa)
- P1: CLAUDE.md, README.md, Makefile, .gitignore, .env.example, scripts/, .githooks/, docs/CONTRACT.md, docs/openapi.json, docs/ARCHITECTURE.md, backend/__init__.py, backend/pytest.ini, backend/app/, backend/requirements.txt, backend/tests/app/
- P2: web/, mobile/
- P3: backend/ai/, backend/impact/, backend/seed/, backend/tests/ai/, backend/tests/seed/, tests/e2e/, docs/DATA.md

Ramuri: `p1-backend`, `p2-front`, `p3-data-ai`; hook-ul pre-commit blochează fișierele din afara zonei.

## Cum se schimbă contractul
1. Propunere în echipă; acord.
2. Se editează `docs/CONTRACT.md` (P1).
3. `make openapi`; P2 regenerează tipurile TS; P3 adaptează modulele.

## Ce nu facem
Autentificare cu parole, plăți, chat, PostGIS, microservicii, Docker, alerte despre oraș.
