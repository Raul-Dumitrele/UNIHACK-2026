// All runtime settings come from mobile/.env (see mobile/.env.example). Restart `npx expo start` after changes.
// On a physical phone EXPO_PUBLIC_API_URL must be the laptop's LAN IP, not localhost.
export const API_URL: string = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000'
export const USE_MOCKS: boolean = process.env.EXPO_PUBLIC_USE_MOCKS === 'true'

// Timișoara centre; P3's data covers bbox 45.70,21.14 - 45.81,21.32 (docs/DATA.md).
export const MAP_CENTER = {
  latitude: Number(process.env.EXPO_PUBLIC_MAP_CENTER_LAT ?? 45.7537),
  longitude: Number(process.env.EXPO_PUBLIC_MAP_CENTER_LON ?? 21.2257),
}
