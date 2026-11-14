import { Ionicons } from '@expo/vector-icons'
import * as Haptics from 'expo-haptics'
import { Tabs } from 'expo-router'
import type { ComponentProps } from 'react'
import { Header } from '../../src/components/Header'
import { colors } from '../../src/theme/tokens'

type IconName = ComponentProps<typeof Ionicons>['name']

const TABS: { name: string; title: string; icon: IconName }[] = [
  { name: 'index', title: 'Idei', icon: 'bulb-outline' },
  { name: 'propune', title: 'Propune', icon: 'add-circle-outline' },
  { name: 'harta', title: 'Hartă', icon: 'map-outline' },
  { name: 'rezervari', title: 'Rezervări', icon: 'calendar-outline' },
  { name: 'notificari', title: 'Notificări', icon: 'notifications-outline' },
  { name: 'impact', title: 'Impact', icon: 'stats-chart-outline' },
]

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        header: () => <Header />,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: { backgroundColor: colors.card, borderTopColor: colors.border },
        tabBarLabelStyle: { fontSize: 11 },
      }}
      screenListeners={{ tabPress: () => Haptics.selectionAsync() }}
    >
      {TABS.map((t) => (
        <Tabs.Screen
          key={t.name}
          name={t.name}
          options={{
            title: t.title,
            tabBarIcon: ({ color, size }) => <Ionicons name={t.icon} size={size} color={color as string} />,
          }}
        />
      ))}
    </Tabs>
  )
}
