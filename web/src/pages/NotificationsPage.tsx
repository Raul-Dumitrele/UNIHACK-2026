import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Check, Landmark, Loader2, X } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import type { Booking, Notification } from '@/api/models'
import { EmptyState, ErrorState, LoadingCards } from '@/components/StateViews'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { DEMO_USERS } from '@/demoUsers'
import { timeAgo } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { cn } from '@/lib/utils'
import { useUser } from '@/user'

export function NotificationsPage() {
  const navigate = useNavigate()
  const { userId } = useUser()
  const isOwner = DEMO_USERS.find((u) => u.id === userId)?.rol === 'proprietar'
  const { data, error, loading, reload, setData } = useApi<Notification[]>('/notifications')

  function markRead(n: Notification) {
    if (n.citita) return
    setData((list) => list?.map((x) => (x.id === n.id ? { ...x, citita: true } : x)) ?? null)
    api(`/notifications/${n.id}/read`, { method: 'PATCH' }).catch(() => reload())
  }

  function open(n: Notification) {
    markRead(n)
    navigate(n.proiect_id ? `/proiecte/${n.proiect_id}` : `/idei/${n.idea_id}`)
  }

  const list = [...(data ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at))

  return (
    <section className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Notificări</h1>
        <p className="text-muted-foreground">Schimbările de stare ale ideilor, rezervărilor și propunerilor tale.</p>
      </div>
      {loading && !data ? (
        <LoadingCards count={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : list.length === 0 ? (
        <EmptyState title="Nicio notificare">Aici apar mesajele când o idee atinge pragul sau o rezervare e decisă.</EmptyState>
      ) : (
        <Card className="gap-0 divide-y overflow-hidden py-0">
          {list.map((n) => (
            <div key={n.id} className={cn('transition-colors hover:bg-muted/60', !n.citita && 'bg-accent/40')}>
              <button onClick={() => open(n)} className="flex w-full items-start gap-3 px-4 pt-3 pb-3 text-left">
                <span
                  className={cn(
                    'mt-0.5 grid size-8 shrink-0 place-items-center rounded-full',
                    n.citita ? 'bg-muted' : 'bg-primary/10 text-primary',
                  )}
                >
                  {n.proiect_id ? <Landmark className="size-4" /> : <Bell className="size-4" />}
                </span>
                <span className="min-w-0 flex-1 space-y-0.5">
                  <span className={cn('block text-sm', !n.citita && 'font-medium')}>{n.mesaj}</span>
                  <span className="block text-xs text-muted-foreground">{timeAgo(n.created_at)}</span>
                </span>
                {!n.citita ? <span className="mt-2 size-2 shrink-0 rounded-full bg-primary" aria-label="necitită" /> : null}
              </button>
              {isOwner && n.booking_id ? <DecideBooking bookingId={n.booking_id} onDone={() => markRead(n)} /> : null}
            </div>
          ))}
        </Card>
      )}
    </section>
  )
}

/** Owner decides a booking request straight from its notification (works without GET /bookings). */
function DecideBooking({ bookingId, onDone }: { bookingId: string; onDone: () => void }) {
  const [busy, setBusy] = useState<'aprobat' | 'refuzat' | null>(null)
  const [done, setDone] = useState<string | null>(null)

  async function decide(stare: 'aprobat' | 'refuzat') {
    setBusy(stare)
    try {
      await api<Booking>(`/bookings/${bookingId}`, { method: 'PATCH', body: JSON.stringify({ stare }) })
      setDone(stare === 'aprobat' ? 'Ai aprobat cererea.' : 'Ai refuzat cererea.')
      toast.success(stare === 'aprobat' ? 'Rezervare aprobată' : 'Rezervare refuzată')
      onDone()
    } catch (e) {
      setDone((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  if (done) return <p className="px-4 pb-3 pl-15 text-xs text-muted-foreground">{done}</p>
  return (
    <div className="flex gap-2 px-4 pb-3 pl-15">
      <Button size="sm" variant="outline" onClick={() => decide('refuzat')} disabled={busy !== null}>
        {busy === 'refuzat' ? <Loader2 className="animate-spin" /> : <X />} Refuză
      </Button>
      <Button size="sm" onClick={() => decide('aprobat')} disabled={busy !== null}>
        {busy === 'aprobat' ? <Loader2 className="animate-spin" /> : <Check />} Aprobă
      </Button>
    </div>
  )
}
