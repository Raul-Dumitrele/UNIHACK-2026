// Leaflet map of spaces. Tile server and attribution come from web/.env (VITE_MAP_TILE_URL).
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import type { Space } from '@/api/types'
import { MAP_ATTRIBUTION, MAP_CENTER, MAP_TILE_URL } from '@/config'
import { DemoBadge } from './DemoBadge'

// A CSS dot instead of Leaflet's default PNG pin (those break under bundlers).
const pin = L.divIcon({
  className: '',
  html: '<span style="display:block;width:18px;height:18px;border-radius:999px;background:var(--primary);border:3px solid var(--card);box-shadow:0 1px 4px rgb(0 0 0 / .35)"></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

export function SpacesMap({ spaces, className = '' }: { spaces: Space[]; className?: string }) {
  if (!MAP_TILE_URL) {
    return (
      <div className={`grid place-items-center rounded-xl border bg-muted text-sm text-muted-foreground ${className}`}>
        Setează VITE_MAP_TILE_URL în web/.env ca să vezi harta.
      </div>
    )
  }
  return (
    <MapContainer center={MAP_CENTER} zoom={13} scrollWheelZoom className={`z-0 rounded-xl border ${className}`}>
      <TileLayer url={MAP_TILE_URL} attribution={MAP_ATTRIBUTION} className="map-tiles" />
      {spaces.map((s) => (
        <Marker key={s.id} position={[s.lat, s.lon]} icon={pin}>
          <Popup>
            <div className="space-y-1">
              <div className="flex items-center gap-2 font-medium">
                {s.name} <DemoBadge show={s.is_demo} />
              </div>
              <div className="text-xs text-muted-foreground">
                {s.kind_label} · {s.neighborhood} · {s.capacity} locuri
              </div>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
