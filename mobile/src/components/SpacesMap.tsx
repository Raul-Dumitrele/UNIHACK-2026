// Native map (Apple Maps on iOS, Google Maps on Android); works in Expo Go without a key.
// The web build uses SpacesMap.web.tsx instead (react-native-maps has no web support).
import MapView, { Marker } from 'react-native-maps'
import type { Space } from '../api/types'
import { MAP_CENTER } from '../config'
import { colors } from '../theme/tokens'

export function SpacesMap({ spaces }: { spaces: Space[] }) {
  return (
    <MapView
      style={{ flex: 1 }}
      initialRegion={{ ...MAP_CENTER, latitudeDelta: 0.09, longitudeDelta: 0.09 }}
    >
      {spaces.map((s) => (
        <Marker
          key={s.id}
          coordinate={{ latitude: s.lat, longitude: s.lon }}
          title={s.name}
          description={`${s.kind_label} · ${s.neighborhood} · ${s.capacity} locuri${s.is_demo ? ' · exemplu' : ''}`}
          pinColor={colors.primary}
        />
      ))}
    </MapView>
  )
}
