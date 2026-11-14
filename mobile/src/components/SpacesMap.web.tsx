// Web fallback: react-native-maps does not run in the browser. The real map lives in web/ (Leaflet).
import { Text, View } from 'react-native'
import type { Space } from '../api/models'

export function SpacesMap({ spaces }: { spaces: Space[] }) {
  return (
    <View className="flex-1 items-center justify-center bg-muted p-6">
      <Text className="text-center text-sm text-muted-foreground">
        Harta apare doar pe telefon (Expo Go). {spaces.length} spații încărcate.
      </Text>
    </View>
  )
}
