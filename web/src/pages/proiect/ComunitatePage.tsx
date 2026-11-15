// Public list (GET /proiecte/publice): every published project, with votes and the threshold. One vote per
// user per project (the server answers 409 on a second one); at the threshold the project goes to the city hall.
import { Link } from 'react-router-dom'
import { ChevronRight, Landmark, ThumbsUp, Users } from 'lucide-react'
import type { Proiect } from '@/api/models'
import { DemoBadge } from '@/components/DemoBadge'
import { ProiectStatusBadge, VotButon } from '@/components/proiect/parts'
import { EmptyState, ErrorState, LoadingCards } from '@/components/StateViews'
import { Card, CardContent } from '@/components/ui/card'
import { fmtLei, timeAgo, tipLabel } from '@/lib/format'
import { useApi } from '@/lib/useApi'

export function ComunitatePage() {
  const { data, error, loading, reload } = useApi<Proiect[]>('/proiecte/publice')
  const list = [...(data ?? [])].sort((a, b) => b.updated_at.localeCompare(a.updated_at))
  const inVot = list.filter((p) => p.stare === 'publicat')
  const rest = list.filter((p) => p.stare !== 'publicat')

  return (
    <section className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Comunitate</h1>
        <p className="text-muted-foreground">
          Proiectele propuse de locuitori. Susține-le cu un vot: când un proiect strânge destui susținători, ajunge automat la Primărie.
        </p>
      </div>
      {loading && !data ? (
        <LoadingCards count={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : list.length === 0 ? (
        <EmptyState title="Niciun proiect publicat">Propune unul de pe hartă și publică-l, ca vecinii să-l poată vota.</EmptyState>
      ) : (
        <>
          {inVot.length ? (
            <div className="space-y-3">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <ThumbsUp className="size-5 text-primary" /> În vot acum
              </h2>
              {inVot.map((p) => (
                <ProiectRow key={p.id} p={p} onVoted={reload} />
              ))}
            </div>
          ) : null}
          {rest.length ? (
            <div className="space-y-3">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Landmark className="size-5 text-primary" /> La Primărie și decise
              </h2>
              {rest.map((p) => (
                <ProiectRow key={p.id} p={p} onVoted={reload} />
              ))}
            </div>
          ) : null}
        </>
      )}
    </section>
  )
}

function ProiectRow({ p, onVoted }: { p: Proiect; onVoted: () => void }) {
  const voturi = p.voturi ?? 0
  const prag = p.prag_voturi ?? 3
  const pct = Math.min(100, Math.round((100 * voturi) / Math.max(prag, 1)))
  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-4">
        <Link to={`/proiecte/${p.id}`} className="group flex min-w-0 flex-1 items-center gap-4">
          <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground">
            <Landmark className="size-5" />
          </span>
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <ProiectStatusBadge stare={p.stare} />
              <DemoBadge show={p.is_demo} />
              <span className="text-xs text-muted-foreground">
                {tipLabel(p.tip_amenajare)} · {p.suprafata_mp} mp
              </span>
            </div>
            <p className="truncate font-semibold group-hover:text-primary">{p.dosar.titlu}</p>
            <p className="text-xs text-muted-foreground">
              {p.cost.suficient && p.cost.mediana_lei != null ? `Cost estimat (mediană): ${fmtLei(p.cost.mediana_lei)}` : 'Fără interval de cost din referințe'}
              {' · '}actualizat {timeAgo(p.updated_at)}
            </p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Users className="size-3.5" />
              <span className="tabular-nums">
                {voturi} / {prag} susținători
              </span>
              <span className="h-1.5 w-32 overflow-hidden rounded-full bg-muted">
                <span className="block h-full bg-primary" style={{ width: `${pct}%` }} />
              </span>
            </div>
          </div>
          <ChevronRight className="hidden size-5 shrink-0 text-muted-foreground sm:block" />
        </Link>
        <VotButon p={p} onDone={onVoted} />
      </CardContent>
    </Card>
  )
}
