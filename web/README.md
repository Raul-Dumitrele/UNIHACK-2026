# web (P2)

React + Vite + TS, Tailwind CSS 4 + shadcn/ui, iconițe lucide-react, font Geist, hartă Leaflet, mock-uri MSW.

## Pornire
```sh
cp .env.example .env         # o singură dată
npm install
npm run dev                  # http://localhost:5173
```

## Setări (`web/.env`)
| Variabilă | Rol |
|---|---|
| `VITE_API_URL` | adresa backend-ului (implicit `http://localhost:8000`) |
| `VITE_USE_MOCKS` | `true` = date mock (exemplele lui P3), fără backend; `false` = API-ul real |
| `VITE_MAP_TILE_URL` / `VITE_MAP_ATTRIBUTION` | sursa hărții (OpenStreetMap) |

## Comenzi
```sh
npm run build                # typecheck + build
npm run typecheck
npm run lint
npm run gen:types            # src/api/schema.d.ts din docs/openapi.json
npm run mocks:update         # recopiază exemplele lui P3 (după ce ajung în main)
npx shadcn@latest add <nume> # componentă nouă
```

Datele hărții: © OpenStreetMap contributors (ODbL).
