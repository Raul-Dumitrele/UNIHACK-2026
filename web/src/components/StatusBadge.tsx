import { Badge } from '@/components/ui/badge'
import type { BookingStatus, IdeaStatus } from '@/api/models'
import { BOOKING_STARE, IDEA_STARE } from '@/lib/format'
import { cn } from '@/lib/utils'

const IDEA_STYLE: Record<IdeaStatus, string> = {
  deschisa: 'border-border bg-muted text-muted-foreground',
  prag_atins: 'border-primary/30 bg-accent text-accent-foreground',
  rezervata: 'border-success/30 bg-success/10 text-success',
}
const BOOKING_STYLE: Record<BookingStatus, string> = {
  cerut: 'border-demo/30 bg-demo-soft text-demo',
  aprobat: 'border-success/30 bg-success/10 text-success',
  refuzat: 'border-destructive/30 bg-destructive/10 text-destructive',
}

export function IdeaStatusBadge({ stare }: { stare: IdeaStatus }) {
  return (
    <Badge variant="outline" className={cn(IDEA_STYLE[stare])}>
      {IDEA_STARE[stare]}
    </Badge>
  )
}

export function BookingStatusBadge({ stare }: { stare: BookingStatus }) {
  return (
    <Badge variant="outline" className={cn(BOOKING_STYLE[stare])}>
      {BOOKING_STARE[stare]}
    </Badge>
  )
}
