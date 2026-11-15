# web/ - Loc Comun

Since 15.11 the project runs in "solo" mode: one person (with Claude) edits every zone, on branch `solo`. The rules below
still describe how the web client is built; contract changes go through docs/CONTRACT.md + `make openapi` + `npm run gen:types`.

## Product
Free plot -> project -> community vote -> city hall. Flow: map of free plots (`/`) -> plot (`/teren/:id`) -> propose project
(`/proiect/nou?teren=`: 3 steps, with POST /proiecte/analiza shown before generating) -> full project (`/proiecte/:id`: feasibility,
memorandum, technical specification, plot, cost = reference interval + itemised sum, stages, risks, documents needed, request
templates, references; tab "Planșe și materiale": plan 2D/3D, A3 sheets PDF, DXF, dossier PDF, XLSX/CSV, materials by chapter
with price source) -> publish (`/proiecte/{id}/publica`) -> votes (`/comunitate`, one per user, 409 on a second) -> at prag_voturi
the server sends it to the city hall -> verifier -> decision. The old endpoints (ideas, bookings) stay in the backend, never called.

## Stack
React 19 + Vite 8 + TypeScript 7, react-router 7, Tailwind CSS 4 + shadcn/ui, lucide-react, Leaflet, three.js (3D view), MSW mocks.

## Conventions
- UI text in Romanian; code, comments and commits in English.
- Every request goes through `api()` / `apiBlob()` in `src/api/client.ts` (adds VITE_API_URL and `X-User-Id`). No raw fetch.
- Settings live in `web/.env` (`src/config.ts`). `.env.example` has `VITE_USE_MOCKS=false`: the real API is the default; mocks show a banner.
- Items with `is_demo: true` show `<DemoBadge />` ("exemplu"). Never compute business values (costs, scores, states) in the UI.
- Types come from `docs/openapi.json` (`npm run gen:types` -> `src/api/schema.d.ts`, never edited by hand); `src/api/models.ts` names them
  and mirrors the JSON-typed objects (Specificatie, Fezabilitate, Act, CerereTip).
- Mocks (`src/mocks`) are a snapshot of the real API and may lag behind it; the real API is right.

## Commands
npm run dev | npm run build | npm run typecheck | npm run lint | npm run gen:types
