// Only notifications about projects are shown (they carry proiect_id). Old idea/booking ones are ignored.
import { useNavigate } from 'react-router-dom'
import { Landmark } from 'lucide-react'
import { api } from '@/api/client'
import type { Notification } from '@/api/models'
import { EmptyState, ErrorState, LoadingCards } from '@/components/StateViews'
import { Card } from '@/components/ui/card'
import { timeAgo } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { cn } from '@/lib/utils'

export function NotificationsPage() {
  const navigate = useNavigate()
  const { data, error, loading, reload, setData } = useApi<Notification[]>('/notifications')

  function open(n: Notification) {
    if (!n.citita) {
      setData((list) => list?.map((x) => (x.id === n.id ? { ...x, citita: true } : x)) ?? null)
      api(`/notifications/${n.id}/read`, { method: 'PATCH' }).catch(() => reload())
    }
    if (n.proiect_id) navigate(`/proiecte/${n.proiect_id}`)
  }

  const list = (data ?? []).filter((n) => n.proiect_id).sort((a, b) => b.created_at.localeCompare(a.created_at))

  return (
    <section className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Notificări</h1>
        <p className="text-muted-foreground">Schimbările de stare ale proiectelor tale.</p>
      </div>
      {loading && !data ? (
        <LoadingCards count={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : list.length === 0 ? (
        <EmptyState title="Nicio notificare">Aici apar mesajele când un proiect e trimis, înaintat sau decis.</EmptyState>
      ) : (
        <Card className="gap-0 divide-y overflow-hidden py-0">
          {list.map((n) => (
            <button
              key={n.id}
              onClick={() => open(n)}
              className={cn('flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/60', !n.citita && 'bg-accent/40')}
            >
              <span className={cn('mt-0.5 grid size-8 shrink-0 place-items-center rounded-full', n.citita ? 'bg-muted' : 'bg-primary/10 text-primary')}>
                <Landmark className="size-4" />
              </span>
              <span className="min-w-0 flex-1 space-y-0.5">
                <span className={cn('block text-sm', !n.citita && 'font-medium')}>{n.mesaj}</span>
                <span className="block text-xs text-muted-foreground">{timeAgo(n.created_at)}</span>
              </span>
              {!n.citita ? <span className="mt-2 size-2 shrink-0 rounded-full bg-primary" aria-label="necitită" /> : null}
            </button>
          ))}
        </Card>
      )}
    </section>
  )
}
