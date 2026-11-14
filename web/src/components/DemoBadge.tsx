import { Badge } from '@/components/ui/badge'

// Shown next to any item with is_demo=true (rule 2 in CLAUDE.md).
export function DemoBadge({ show = true }: { show?: boolean }) {
  if (!show) return null
  return (
    <Badge variant="outline" className="border-demo/40 bg-demo-soft text-demo">
      exemplu
    </Badge>
  )
}
