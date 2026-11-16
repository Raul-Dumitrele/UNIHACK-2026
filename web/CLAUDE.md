# web/ - Loc Comun

Since 15.11 the project runs in "solo" mode: one person (with Claude) edits every zone, on branch `solo`. The rules below
still describe how the web client is built; contract changes go through docs/CONTRACT.md + `make openapi` + `npm run gen:types`.

## Product
Free plot -> project -> community vote -> city hall. Flow: map of free plots (`/`) -> wizard (`/proiect/nou`, 4 steps: the idea;
how it was understood, which the user confirms or corrects; the plot from GET /terenuri/potrivite; feasibility on that plot and
"Generează proiectul") -> project page (`/proiecte/:id`, tabs Rezumat / Dosar / Avize și cereri / Planșe și materiale) -> publish ->
votes (`/comunitate`, one per user) -> at prag_voturi the server sends it to the city hall -> verifier -> decision.
The old endpoints (ideas, bookings) stay in the backend, never called.
Rules the UI keeps:
- a proposal that is too vague is not turned into a project unless the user explicitly asks for a generic sketch;
- the cost headline is `cost.titlu`; the partial sum of priced lines sits in a secondary block under `cost.eticheta_suma`, with the
  unpriced lines and `cost.nota_suma`. It is never the headline and never called "the cost";
- nothing shown to the user names variables, fallbacks, env settings or the AI pipeline; technical facts are said in plain Romanian;
- the mandatory texts stay visible (contract rule 10, plan disclaimer, SEAP CC BY 4.0, TVA, © OpenStreetMap, "din lista Primăriei – de confirmat").

## Stack
React 19 + Vite 8 + TypeScript 7, react-router 7, Tailwind CSS 4 + shadcn/ui, lucide-react, Leaflet, three.js (3D view), MSW mocks.

## Conventions
- UI text in Romanian; code, comments and commits in English.
- Every request goes through `api()` / `apiBlob()` in `src/api/client.ts` (adds VITE_API_URL and `X-User-Id`). No raw fetch.
- Settings live in `web/.env` (`src/config.ts`). `.env.example` has `VITE_USE_MOCKS=false`: the real API is the default; mocks show a banner.
- Items with `is_demo: true` show `<DemoBadge />` ("exemplu"). Never compute business values (costs, scores, states) in the UI.
- Types come from `docs/openapi.json` (`npm run gen:types` -> `src/api/schema.d.ts`, never edited by hand); `src/api/models.ts` names them
  and mirrors the JSON-typed objects (Specificatie, Fezabilitate, Act, CerereTip).
- Demo mode (`VITE_USE_MOCKS=true`, `src/mocks/mockApi.ts` behind MSW) answers from `src/mocks/data`, a SNAPSHOT of the real API
  made by `scripts/dump_api_mocks.py` (throwaway DB + seed + `/scripts/demo_cases.py`). Its limits are listed at the top of
  `mockApi.ts`. If it differs from the real API, the real API is right: re-run the dump.
- `.env.example` documents the settings; a setting given on the command line wins (`VITE_USE_MOCKS=false npm run dev`).

## Commands
npm run dev | npm run build | npm run typecheck | npm run lint | npm test | npm run gen:types
