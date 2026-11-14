// Owner panel + my requests. GET /bookings returns the user's requests (as idea author) and those for spaces they own.
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Loader2, X } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import type { Booking, Idea, Space } from '@/api/models'
import { EmptyState, ErrorState, LoadingCards } from '@/components/StateViews'
import { BookingStatusBadge } from '@/components/StatusBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { fmtDate, fmtSlot } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { useUser } from '@/user'

export function BookingsPage() {
  const { userId } = useUser()
  const bookings = useApi<Booking[]>('/bookings')
  const ideas = useApi<Idea[]>('/ideas')
  const spaces = useApi<Space[]>('/spaces')

  const loading = (bookings.loading && !bookings.data) || (ideas.loading && !ideas.data) || (spaces.loading && !spaces.data)
  const error = bookings.error ?? ideas.error ?? spaces.error
  const ideaById = new Map((ideas.data ?? []).map((i) => [i.id, i]))
  const spaceById = new Map((spaces.data ?? []).map((s) => [s.id, s]))
  const all = bookings.data ?? []
  const forMySpaces = all.filter((b) => spaceById.get(b.space_id)?.owner_id === userId)
  const mine = all.filter((b) => ideaById.get(b.idea_id)?.author_id === userId)
  const pending = forMySpaces.filter((b) => b.stare === 'cerut')

  return (
    <section className="space-y-8">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Rezervări</h1>
        <p className="text-muted-foreground">Cererile pentru spațiile tale și cererile trimise de tine.</p>
      </div>

      {loading ? (
        <LoadingCards count={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => (bookings.reload(), ideas.reload(), spaces.reload())} />
      ) : (
        <>
          {forMySpaces.length > 0 || pending.length > 0 ? (
            <div className="space-y-3">
              <h2 className="text-xl font-semibold tracking-tight">
                Cereri pentru spațiile mele {pending.length ? <span className="text-demo">({pending.length} în așteptare)</span> : null}
              </h2>
              {forMySpaces.map((b) => (
                <BookingRow key={b.id} b={b} idea={ideaById.get(b.idea_id)} space={spaceById.get(b.space_id)} owner onDecided={bookings.reload} />
              ))}
            </div>
          ) : null}

          <div className="space-y-3">
            <h2 className="text-xl font-semibold tracking-tight">Cererile mele</h2>
            {mine.length === 0 ? (
              <EmptyState title="Nu ai trimis încă nicio cerere">
                Cererile se trimit din pagina unei idei proprii, după ce atinge pragul de interes.
              </EmptyState>
            ) : (
              mine.map((b) => <BookingRow key={b.id} b={b} idea={ideaById.get(b.idea_id)} space={spaceById.get(b.space_id)} />)
            )}
          </div>
        </>
      )}
    </section>
  )
}

function BookingRow({
  b,
  idea,
  space,
  owner = false,
  onDecided,
}: {
  b: Booking
  idea?: Idea
  space?: Space
  owner?: boolean
  onDecided?: () => void
}) {
  const [busy, setBusy] = useState<'aprobat' | 'refuzat' | null>(null)

  async function decide(stare: 'aprobat' | 'refuzat') {
    setBusy(stare)
    try {
      await api<Booking>(`/bookings/${b.id}`, { method: 'PATCH', body: JSON.stringify({ stare }) })
      toast.success(stare === 'aprobat' ? 'Rezervare aprobată' : 'Rezervare refuzată')
      onDecided?.()
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <BookingStatusBadge stare={b.stare} />
            <span className="text-sm font-medium">{fmtSlot(b.slot)}</span>
          </div>
          <p className="truncate font-semibold">
            {idea ? (
              <Link to={`/idei/${idea.id}`} className="hover:text-primary">
                {idea.titlu}
              </Link>
            ) : (
              b.idea_id
            )}
          </p>
          <p className="text-xs text-muted-foreground">
            {space?.nume ?? b.space_id} · cerută {fmtDate(b.created_at)}
          </p>
          {b.mesaj ? (
            <blockquote className="mt-2 border-l-2 border-primary/40 pl-3 text-sm text-muted-foreground italic">{b.mesaj}</blockquote>
          ) : null}
        </div>
        {owner && b.stare === 'cerut' ? (
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => decide('refuzat')} disabled={busy !== null}>
              {busy === 'refuzat' ? <Loader2 className="animate-spin" /> : <X />} Refuză
            </Button>
            <Button size="sm" onClick={() => decide('aprobat')} disabled={busy !== null}>
              {busy === 'aprobat' ? <Loader2 className="animate-spin" /> : <Check />} Aprobă
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
