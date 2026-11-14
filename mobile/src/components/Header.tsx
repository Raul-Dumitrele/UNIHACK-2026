// App header: brand, API status and the demo-user switcher (sets X-User-Id).
import * as Haptics from 'expo-haptics'
import { useEffect, useState } from 'react'
import { Pressable, ScrollView, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { api, DEMO_USERS, getUserId, setUserId } from '../api/client'
import { USE_MOCKS } from '../config'

function ApiStatus() {
  const [ok, setOk] = useState<boolean | null>(null)
  useEffect(() => {
    api<{ status: string }>('/health')
      .then((r) => setOk(r.status === 'ok'))
      .catch(() => setOk(false))
  }, [])
  const label = ok === null ? 'se verifică…' : ok ? 'API conectat' : 'API indisponibil'
  const dot = ok === null ? 'bg-muted-foreground/40' : ok ? 'bg-success' : 'bg-destructive'
  return (
    <View className="flex-row items-center gap-1.5">
      <View className={`h-2 w-2 rounded-full ${dot}`} />
      <Text className="text-xs text-muted-foreground">{label}</Text>
    </View>
  )
}

export function Header() {
  const insets = useSafeAreaInsets()
  const [userId, setUser] = useState(getUserId)

  const choose = (id: string) => {
    Haptics.selectionAsync()
    setUserId(id)
    setUser(id)
  }

  return (
    <View className="border-b border-border bg-background px-4 pb-3" style={{ paddingTop: insets.top + 8 }}>
      <View className="flex-row items-center justify-between">
        <Text className="text-xl font-bold tracking-tight text-primary">Loc Comun</Text>
        {USE_MOCKS ? (
          <View className="rounded-full bg-demo-soft px-2 py-0.5">
            <Text className="text-xs font-medium text-demo">date mock</Text>
          </View>
        ) : (
          <ApiStatus />
        )}
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mt-3" contentContainerClassName="gap-2">
        {DEMO_USERS.map((u) => {
          const active = userId === u.id
          return (
            <Pressable
              key={u.id}
              onPress={() => choose(u.id)}
              className={`rounded-full border px-3 py-1.5 active:opacity-70 ${
                active ? 'border-primary bg-primary' : 'border-border bg-card'
              }`}
            >
              <Text className={`text-sm ${active ? 'font-medium text-primary-foreground' : 'text-foreground'}`}>
                {u.name.split(' ')[0]}
                {u.role === 'proprietar' ? ' · proprietar' : ''}
              </Text>
            </Pressable>
          )
        })}
      </ScrollView>
    </View>
  )
}
