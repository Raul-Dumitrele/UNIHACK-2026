// Leaflet map of free plots. Tile server and attribution come from web/.env (VITE_MAP_TILE_URL).
// Optionally lets the user click to choose a position (onPick), used when marking a new plot.
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { Link } from 'react-router-dom'
import { MapContainer, Marker, Popup, TileLayer, useMapEvents } from 'react-leaflet'
import type { Space } from '@/api/models'
import { MAP_ATTRIBUTION, MAP_CENTER, MAP_TILE_URL } from '@/config'
import { DemoBadge } from './DemoBadge'

// CSS markers instead of Leaflet's default PNG pin (those break under bundlers).
const plot = L.divIcon({
  className: '',
  html: '<span style="display:block;width:24px;height:24px;border-radius:6px;background:var(--demo);border:3px solid var(--card);box-shadow:0 1px 4px rgb(0 0 0 / .35);transform:rotate(45deg)"></span>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})
const picked = L.divIcon({
  className: '',
  html: '<span style="display:block;width:22px;height:22px;border-radius:999px;background:var(--primary);border:3px solid var(--card);box-shadow:0 1px 6px rgb(0 0 0 / .45)"></span>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
})

const clusterIcon = (n: number) =>
  L.divIcon({
    className: '',
    html: `<span style="display:grid;place-items:center;width:34px;height:34px;border-radius:999px;background:var(--demo);color:#fff;font-weight:700;font-size:13px;border:3px solid var(--card);box-shadow:0 1px 5px rgb(0 0 0 / .4)">${n}</span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  })

/** Plots within ~400 m of the first plot of a group share one marker (e.g. a row of lots on the same street). */
function groupNearby(spaces: Space[]): Space[][] {
  const groups: Space[][] = []
  for (const s of spaces) {
    const home = groups.find((g) => Math.hypot(g[0].lat - s.lat, (g[0].lng - s.lng) * 0.7) < 0.004)
    if (home) home.push(s)
    else groups.push([s])
  }
  return groups
}

function ClickPicker({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) })
  return null
}

type Props = {
  terenuri: Space[]
  className?: string
  center?: [number, number]
  zoom?: number
  /** Click on the map to choose a position. */
  onPick?: (lat: number, lng: number) => void
  /** Position chosen so far (shown as a blue dot). */
  picked?: [number, number] | null
  /** Small preview: no scroll zoom, no link inside the popup. */
  compact?: boolean
}

export function TerenMap({ terenuri, className = '', center = MAP_CENTER, zoom = 13, onPick, picked: pos, compact = false }: Props) {
  if (!MAP_TILE_URL) {
    return (
      <div className={`grid place-items-center rounded-xl border bg-muted text-sm text-muted-foreground ${className}`}>
        Setează VITE_MAP_TILE_URL în web/.env ca să vezi harta.
      </div>
    )
  }
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      scrollWheelZoom={!compact}
      className={`z-0 rounded-xl border ${onPick ? 'cursor-crosshair' : ''} ${className}`}
    >
      <TileLayer url={MAP_TILE_URL} attribution={MAP_ATTRIBUTION} className="map-tiles" />
      {onPick ? <ClickPicker onPick={onPick} /> : null}
      {groupNearby(terenuri).map((g) => {
        if (g.length === 1) {
          const s = g[0]
          return (
            <Marker key={s.id} position={[s.lat, s.lng]} icon={plot}>
              <Popup>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 font-medium">
                    {s.nume} <DemoBadge show={s.is_demo} />
                  </div>
                  <div className="text-xs text-muted-foreground">teren liber{s.suprafata_mp ? ` · ${s.suprafata_mp} mp` : ''}</div>
                  {compact ? null : (
                    <Link to={`/teren/${s.id}`} className="text-sm font-medium text-primary underline">
                      Vezi terenul
                    </Link>
                  )}
                </div>
              </Popup>
            </Marker>
          )
        }
        const lat = g.reduce((t, s) => t + s.lat, 0) / g.length
        const lng = g.reduce((t, s) => t + s.lng, 0) / g.length
        return (
          <Marker key={g.map((s) => s.id).join('|')} position={[lat, lng]} icon={clusterIcon(g.length)}>
            <Popup>
              <div className="max-h-48 space-y-1 overflow-y-auto">
                <p className="font-medium">{g.length} terenuri în aceeași zonă</p>
                {g.map((s) => (
                  <Link key={s.id} to={`/teren/${s.id}`} className="block text-sm text-primary underline">
                    {s.nume.replace(/^Teren din lista Primăriei \(Legea 15\/2003\), /, '')}
                    {s.suprafata_mp ? ` · ${s.suprafata_mp} mp` : ''}
                  </Link>
                ))}
              </div>
            </Popup>
          </Marker>
        )
      })}
      {pos ? <Marker position={pos} icon={picked} /> : null}
    </MapContainer>
  )
}
