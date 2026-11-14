# mobile (P2)

Expo SDK 58 + TS, expo-router (tab-uri în `app/(tabs)/`), NativeWind 4, Ionicons, expo-haptics, react-native-maps.

## Pornire
```sh
cp .env.example .env         # o singură dată
npm install
npx expo start               # scanează QR-ul cu Expo Go (telefonul în același Wi-Fi)
```

## Setări (`mobile/.env`, Expo nu citește .env din rădăcină)
| Variabilă | Rol |
|---|---|
| `EXPO_PUBLIC_API_URL` | adresa backend-ului; pe telefon: IP-ul laptopului (`ipconfig getifaddr en0`), ex. `http://192.168.1.20:8000` |
| `EXPO_PUBLIC_USE_MOCKS` | `true` = date mock (exemplele lui P3), fără backend; `false` = API-ul real |

Pentru API-ul real pe telefon, backend-ul trebuie pornit cu `--host 0.0.0.0`.

## Comenzi
```sh
npx expo start --clear       # după schimbări în tailwind.config.js / babel / metro / .env
npm run typecheck
npx expo-doctor
npm run sync:mocks           # recopiază mock-urile și tipurile din web/
npm run gen:types            # src/api/schema.d.ts din docs/openapi.json
npx expo install <pachet>    # mereu așa, nu npm install
```
