// Native map (Apple Maps on iOS, Google Maps on Android); works in Expo Go without a key.
// The web build uses SpacesMap.web.tsx instead (react-native-maps has no web support).
import MapView, { Marker } from 'react-native-maps'
import type { Space } from '../api/models'
import { MAP_CENTER } from '../config'
import { colors } from '../theme/tokens'

// Space.tip is free text; the seed writes "teren liber".
const isFreePlot = (tip: string) => tip.trim().toLowerCase().replace(/[\s_-]+/g, '_') === 'teren_liber'

export function SpacesMap({ spaces }: { spaces: Space[] }) {
  return (
    <MapView
      style={{ flex: 1 }}
      initialRegion={{ ...MAP_CENTER, latitudeDelta: 0.09, longitudeDelta: 0.09 }}
    >
      {spaces.map((s) => (
        <Marker
          key={s.id}
          coordinate={{ latitude: s.lat, longitude: s.lng }}
          title={s.nume}
          description={`${isFreePlot(s.tip) ? `teren liber${s.suprafata_mp ? ` · ${s.suprafata_mp} mp` : ''}` : `${s.tip} · ${s.capacitate} locuri`}${s.is_demo ? ' · exemplu' : ''}`}
          pinColor={isFreePlot(s.tip) ? colors.demo : colors.primary}
        />
      ))}
    </MapView>
  )
}
