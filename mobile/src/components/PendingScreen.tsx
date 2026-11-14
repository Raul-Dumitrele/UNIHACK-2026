// Placeholder screen until docs/CONTRACT.md defines the entities.
import { Ionicons } from '@expo/vector-icons'
import { ScrollView, Text, View } from 'react-native'
import { colors } from '../theme/tokens'
import { Card, Skeleton } from './ui'

export function PendingScreen({ title, endpoint, intro }: { title: string; endpoint: string; intro?: string }) {
  return (
    <ScrollView className="flex-1 bg-background" contentContainerClassName="gap-4 p-4">
      <View className="gap-1">
        <Text className="text-3xl font-bold tracking-tight text-foreground">{title}</Text>
        {intro ? <Text className="text-base text-muted-foreground">{intro}</Text> : null}
      </View>
      <Card className="flex-row items-start gap-3">
        <Ionicons name="construct-outline" size={20} color={colors.muted} />
        <Text className="flex-1 text-sm text-muted-foreground">
          În lucru: aștept câmpurile din contract pentru {endpoint}.
        </Text>
      </Card>
      {[0, 1].map((i) => (
        <Card key={i} className="gap-3">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-1/2" />
        </Card>
      ))}
    </ScrollView>
  )
}
