# web/ (P2) - Loc Comun

Only P2 edits this folder. Never touch backend/, docs/, scripts/ or mobile/ from here; if the API or the
contract needs a change, stop and say what to ask P1 (contract, backend, AI, seed, impact; P3's zone is now P1's).

## Product (since the restructuring)
Free plot -> project. Flow: map of free plots (`/`) -> plot (`/teren/:id`) -> propose project (`/proiect/nou?teren=`) ->
full project (`/proiecte/:id`) -> send to Primărie -> verifier -> decision. No bookings, no ideas, no interest threshold,
no "proprietar" in the user switcher; the old endpoints stay in the backend but the UI never calls them.
Project page has tabs Dosar / Documente (plan SVG, PDF/DXF/CSV downloads, materials with SEAP prices); the wizard has 3 steps
(what, choose the plot via GET /terenuri/potrivite, generate with POST /proiecte). Files are fetched with `apiBlob()` because a link
cannot send X-User-Id. All of this is on main; types are generated from `docs/openapi.json`.
Not on the backend: `POST /spaces` (so "Marchează un teren" is hidden unless `VITE_ENABLE_MARK_PLOT=true`), budget per component and
the company profile (not shown, not simulated). `tip_amenajare` is an enum on the server; the wizard also accepts free text and shows
the server's `detail` on 422. Mobile is paused.

## Stack
React 19 + Vite 8 + TypeScript 7, react-router 7, Tailwind CSS 4 + shadcn/ui (`src/components/ui/`, preset radix-nova),
lucide-react icons, Geist font, Leaflet (react-leaflet), MSW 3 for mocks.

## Conventions
- UI text in Romanian; code, comments and commits in English.
- Every request goes through `api()` in `src/api/client.ts` (adds VITE_API_URL and `X-User-Id`). No raw fetch.
- No URLs or keys in code: settings live in `web/.env` (`src/config.ts` reads them). `.env.example` is the template.
- Items with `is_demo: true` show `<DemoBadge />` ("exemplu").
- Colors and radii come from the CSS variables in `src/index.css` (`bg-primary`, `text-muted-foreground`, `text-demo`...).
  Never hardcode hex colors in components; keep `src/theme/tokens.ts` and `mobile/` tokens in sync.
- Add shadcn components with `npx shadcn@latest add <name>`; edit them freely afterwards.
- Import from `src` with the `@/` alias.

## Types and mocks
- Types come from `docs/openapi.json`: `npm run gen:types` -> `src/api/schema.d.ts` (never edit by hand);
  `src/api/models.ts` gives them short names. Fields marked PROVISIONAL there are not in openapi yet.
  After regenerating, report any tsc diff instead of working around it.
- `src/mocks/mockApi.ts` is an in-memory fake of P1's backend over `src/mocks/data/*.json`, which is a SNAPSHOT of the real API:
  `scripts/dump_api_mocks.py` (throwaway DB + seed + `--create-projects`; it also adds the candidate plots of `terenuri_osm.json`, made by
  `scripts/terenuri_osm.py`). Plans, materials, documents and plot scores are what the API answered. If a mock differs from the real
  API, the real API is right: re-run the dump. `VITE_USE_MOCKS=true` turns it on (MSW, `src/mocks/browser.ts`).
  A project created in the mock is cloned from a snapshot project of the same kind (the mock never writes costs or prices).
- Never compute business values (costs, scores, statuses) in the UI: they come from the API (or the mock standing in for it).
- mobile/ keeps a copy of `src/mocks` and `src/api/{models,schema.d}.ts`: after editing them run `npm run sync:mocks` in mobile/.

## Commands
npm run dev | npm run build | npm run typecheck | npm run lint | npm run gen:types
