// One plot: small map, data, the projects already proposed here, and "Propune un proiect aici".
// GET /spaces/{id}/proiecte is public: every submitted project on the plot, plus the caller's own drafts.
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ChevronRight, Landmark, Plus } from 'lucide-react'
import type { Proiect } from '@/api/models'
import { DemoBadge } from '@/components/DemoBadge'
import { ProiectStatusBadge } from '@/components/proiect/parts'
import { EmptyState, ErrorState, LoadingCards } from '@/components/StateViews'
import { TerenMap } from '@/components/TerenMap'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DEMO_USERS } from '@/demoUsers'
import { timeAgo, tipLabel } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { useTerenuri } from '@/lib/useTerenuri'
import { useUser } from '@/user'

export function TerenDetaliuPage() {
  const { id = '' } = useParams()
  const { userId } = useUser()
  const { terenuri, error, loading, reload, data } = useTerenuri()
  const proiecte = useApi<Proiect[]>(`/spaces/${id}/proiecte`)
  const canPropose = DEMO_USERS.find((u) => u.id === userId)?.rol === 'cetatean'

  if (loading && !data) return <LoadingCards count={2} />
  if (error) return <ErrorState message={error} onRetry={reload} />
  const t = terenuri.find((s) => s.id === id)
  if (!t) return <ErrorState message="Terenul nu există." />
  const aici = proiecte.data ?? []

  return (
    <section className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Harta terenurilor
      </Link>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <DemoBadge show={t.is_demo} />
            <span className="text-sm text-muted-foreground">teren liber{t.suprafata_mp ? ` · ${t.suprafata_mp} mp` : ''}</span>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">{t.nume}</h1>
          <p className="text-xs text-muted-foreground tabular-nums">
            {t.lat.toFixed(5)}, {t.lng.toFixed(5)}
          </p>
          {t.descriere ? <p className="max-w-2xl text-sm">{t.descriere}</p> : null}
          <p className="text-xs text-muted-foreground">
            Proprietar, regim juridic și disponibilitate: de verificat cu Primăria.
            {t.status_verificare ? ` Stare: ${t.status_verificare}.` : ''}
          </p>
        </div>
        {canPropose ? (
          <Button size="lg" asChild>
            <Link to={`/proiect/nou?teren=${t.id}`}>
              <Plus /> Propune un proiect aici
            </Link>
          </Button>
        ) : null}
      </header>

      <TerenMap terenuri={[t]} center={[t.lat, t.lng]} zoom={16} compact className="h-72 w-full" />

      <Card>
        <CardHeader>
          <CardTitle>Proiecte propuse aici</CardTitle>
        </CardHeader>
        <CardContent>
          {proiecte.loading && !proiecte.data ? (
            <LoadingCards count={1} />
          ) : aici.length === 0 ? (
            <EmptyState title="Niciun proiect încă">
              {canPropose ? 'Fii primul care propune ce s-ar putea construi aici.' : 'Nu sunt proiecte trimise pe acest teren.'}
            </EmptyState>
          ) : (
            <div className="space-y-2">
              {aici.map((p) => (
                <Link key={p.id} to={`/proiecte/${p.id}`} className="group flex items-center gap-3 rounded-lg border p-3 hover:bg-muted/50">
                  <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground">
                    <Landmark className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <ProiectStatusBadge stare={p.stare} />
                      <DemoBadge show={p.is_demo} />
                      <span className="text-xs text-muted-foreground">{tipLabel(p.tip_amenajare)}</span>
                    </div>
                    <p className="truncate font-medium group-hover:text-primary">{p.dosar.titlu}</p>
                    <p className="text-xs text-muted-foreground">actualizat {timeAgo(p.updated_at)}</p>
                  </div>
                  <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  )
}
