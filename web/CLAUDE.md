# web/ (P2) - Loc Comun

Only P2 edits this folder. Never touch backend/, docs/, scripts/ or mobile/ from here; if the API or the
contract needs a change, stop and say what to ask P1 (contract) or P3 (AI, seed, impact).

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
- `src/mocks/mockApi.ts` is an in-memory fake of P1's backend that follows the contract rules, over
  `src/mocks/data/*.json` (P3's demo seed converted to contract shape by `scripts/seed_to_mocks.py`).
  `VITE_USE_MOCKS=true` turns it on (MSW, `src/mocks/browser.ts`). Endpoints marked PROVISIONAL are not in the contract.
- Never compute business values (costs, scores, statuses) in the UI: they come from the API (or the mock standing in for it).
- mobile/ keeps a copy of `src/mocks` and `src/api/{models,schema.d}.ts`: after editing them run `npm run sync:mocks` in mobile/.

## Commands
npm run dev | npm run build | npm run typecheck | npm run lint | npm run gen:types
