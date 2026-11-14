# mobile/ (P2) - Loc Comun

Only P2 edits this folder. Never touch backend/, docs/, scripts/ or web/ from here; if the API or the
contract needs a change, stop and say what to ask P1 (contract) or P3 (AI, seed, impact).
See also AGENTS.md (Expo's own guidance: check versioned docs, use `npx expo install`).

## Stack
Expo SDK 58 (React Native 0.88, React 19.3), expo-router (tabs in `app/(tabs)/`), NativeWind 4 + Tailwind 3
(`className` on RN components), @expo/vector-icons (Ionicons), expo-haptics, react-native-maps (Expo Go, no key).

## Conventions
- UI text in Romanian; code, comments and commits in English.
- Every request goes through `api()` in `src/api/client.ts` (adds EXPO_PUBLIC_API_URL and `X-User-Id`).
- No URLs or keys in code: settings live in `mobile/.env` (`src/config.ts` reads them). Expo does not read the root .env.
- On a physical phone the API URL must be the laptop's LAN IP, not localhost.
- Items with `is_demo: true` show `<DemoBadge />` ("exemplu") from `src/components/ui.tsx`.
- Colors come from `tailwind.config.js` (`bg-primary`, `text-muted-foreground`...) and `src/theme/tokens.ts`
  for props that need a raw value (icons, tab bar). Keep them in sync with web/.
- Install native packages only with `npx expo install <pkg>`; run `npx expo-doctor` afterwards.
- Platform-specific files: `X.web.tsx` for the web build (react-native-maps has no web support).

## Types and mocks
- `src/api/types.ts` and `src/mocks/` are COPIES from web/ (`npm run sync:mocks`). Edit them in web/, then sync.
- `EXPO_PUBLIC_USE_MOCKS=true` makes `api()` answer from `src/mocks/mockApi.ts` (P3 example data).
- When P1 publishes `docs/openapi.json`: `npm run gen:types` -> `src/api/schema.d.ts`.

## Commands
npx expo start | npx expo start --clear | npm run typecheck | npx expo-doctor | npm run sync:mocks | npm run gen:types
