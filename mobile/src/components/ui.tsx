// Small shared building blocks, styled with NativeWind classes.
import type { ReactNode } from 'react'
import { Text, View } from 'react-native'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <View className={`rounded-2xl border border-border bg-card p-4 ${className}`}>{children}</View>
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <View className={`rounded-md bg-muted ${className}`} />
}

// Shown next to any item with is_demo=true (rule 2 in CLAUDE.md).
export function DemoBadge({ show = true }: { show?: boolean }) {
  if (!show) return null
  return (
    <View className="self-start rounded-full border border-demo/40 bg-demo-soft px-2 py-0.5">
      <Text className="text-xs font-medium text-demo">exemplu</Text>
    </View>
  )
}
