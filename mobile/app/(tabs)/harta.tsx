import { useEffect, useState } from 'react'
import { Text, View } from 'react-native'
import { api } from '../../src/api/client'
import type { Space } from '../../src/api/models'
import { SpacesMap } from '../../src/components/SpacesMap'

export default function MapScreen() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // PROVISIONAL endpoint (not in the contract yet); served by the mocks for now.
    api<Space[]>('/spaces')
      .then(setSpaces)
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <View className="flex-1 bg-background">
      <View className="px-4 py-3">
        <Text className="text-2xl font-bold tracking-tight text-foreground">Spații libere</Text>
        <Text className="text-sm text-muted-foreground">
          {error ? `Nu am putut încărca spațiile: ${error}` : `${spaces.length} spații în Timișoara`}
        </Text>
      </View>
      <SpacesMap spaces={spaces} />
      <Text className="absolute bottom-1 right-2 text-[10px] text-muted-foreground">Date spații: © OpenStreetMap contributors</Text>
    </View>
  )
}
