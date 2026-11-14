// All runtime settings come from web/.env (see web/.env.example). No URLs hardcoded elsewhere.
const env = import.meta.env

export const API_URL: string = env.VITE_API_URL ?? 'http://localhost:8000'
export const USE_MOCKS: boolean = env.VITE_USE_MOCKS === 'true'

export const MAP_TILE_URL: string = env.VITE_MAP_TILE_URL ?? ''
export const MAP_ATTRIBUTION: string = env.VITE_MAP_ATTRIBUTION ?? '© OpenStreetMap contributors'
// Timișoara centre; P3's data covers bbox 45.70,21.14 - 45.81,21.32 (docs/DATA.md).
export const MAP_CENTER: [number, number] = [Number(env.VITE_MAP_CENTER_LAT ?? 45.7537), Number(env.VITE_MAP_CENTER_LON ?? 21.2257)]

/** Marking a plot (POST /spaces). On unless VITE_ENABLE_MARK_PLOT=false. */
export const MARK_PLOT_ENABLED: boolean = env.VITE_ENABLE_MARK_PLOT !== 'false'
