// Page skeletons. Fields are filled in once docs/CONTRACT.md defines the entities.
import type { ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { Construction } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

function Pending({ title, endpoint, children }: { title: string; endpoint: string; children?: ReactNode }) {
  return (
    <section className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        {children ? <p className="text-muted-foreground">{children}</p> : null}
      </div>
      <Card>
        <CardContent className="flex items-start gap-3">
          <Construction className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            În lucru: aștept câmpurile din contract pentru{' '}
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{endpoint}</code>.
          </p>
        </CardContent>
      </Card>
      <div className="grid gap-4 sm:grid-cols-2">
        {[0, 1].map((i) => (
          <Card key={i}>
            <CardContent className="space-y-3">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-1/2" />
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  )
}

export function IdeasPage() {
  return <Pending title="Idei din comunitate" endpoint="GET /ideas" />
}

export function NewIdeaPage() {
  return (
    <Pending title="Propune o idee" endpoint="POST /ideas">
      Descrie ideea în câteva fraze; AI-ul o transformă într-un dosar structurat.
    </Pending>
  )
}

export function IdeaDetailPage() {
  const { id } = useParams()
  return (
    <Pending title={`Idee #${id}`} endpoint="GET /ideas/{id}/matches, POST /ideas/{id}/interest">
      Dosarul structurat, spațiile potrivite (cu scor și motiv) și butonul „Mă interesează”.
    </Pending>
  )
}

export function BookingsPage() {
  return (
    <Pending title="Rezervări" endpoint="POST /bookings, PATCH /bookings/{id}">
      Cererile tale și, pentru proprietari, cererile de aprobat sau refuzat.
    </Pending>
  )
}

export function NotificationsPage() {
  return <Pending title="Notificări" endpoint="Notification" />
}

export function ImpactPage() {
  return <Pending title="Tablou de impact" endpoint="GET /impact" />
}
