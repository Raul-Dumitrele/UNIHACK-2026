// Home: map of free plots. Click a marker for the card, or "Marchează un teren" to add one.
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, MapPinPlus, Plus } from 'lucide-react'
import { DemoBadge } from '@/components/DemoBadge'
import { EmptyState, ErrorState, LoadingCards } from '@/components/StateViews'
import { TerenMap } from '@/components/TerenMap'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { MARK_PLOT_ENABLED } from '@/config'
import { DEMO_USERS } from '@/demoUsers'
import { useTerenuri } from '@/lib/useTerenuri'
import { useUser } from '@/user'

export function MapPage() {
  const { userId } = useUser()
  const { terenuri, error, loading, reload, data } = useTerenuri()
  const [all, setAll] = useState(false)
  const shown = all ? terenuri : terenuri.slice(0, 9)
  const canMark = DEMO_USERS.find((u) => u.id === userId)?.rol === 'cetatean'

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">Terenuri libere</h1>
          <p className="text-muted-foreground">
            Alege un teren din Timișoara și propune ce ar trebui construit pe el. Aplicația pregătește dosarul complet.
          </p>
        </div>
        {canMark ? (
          <div className="flex flex-wrap gap-2">
            {MARK_PLOT_ENABLED ? (
              <Button size="lg" variant="outline" asChild>
                <Link to="/teren/nou">
                  <MapPinPlus /> Marchează un teren
                </Link>
              </Button>
            ) : null}
            <Button size="lg" asChild>
              <Link to="/proiect/nou">
                <Plus /> Propune un proiect
              </Link>
            </Button>
          </div>
        ) : null}
      </div>

      {error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : (
        <>
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="size-3 rotate-45 rounded-sm bg-demo" /> teren liber · {loading && !data ? 'se încarcă…' : `${terenuri.length} terenuri`}
          </p>
          <TerenMap terenuri={terenuri} className="h-[60vh] min-h-80 w-full" />
          {loading && !data ? (
            <LoadingCards count={3} />
          ) : terenuri.length === 0 ? (
            <EmptyState title="Niciun teren încă">Nu există terenuri libere încă.</EmptyState>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {shown.map((t) => (
                <Link key={t.id} to={`/teren/${t.id}`} className="group block">
                  <Card className="h-full transition-shadow group-hover:shadow-md">
                    <CardContent className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <DemoBadge show={t.is_demo} />
                        {t.suprafata_mp ? <span className="text-xs text-muted-foreground">{t.suprafata_mp} mp</span> : null}
                      </div>
                      <p className="font-semibold group-hover:text-primary">{t.nume}</p>
                      <p className="flex items-center gap-1 text-sm text-primary">
                        Vezi terenul <ArrowRight className="size-4" />
                      </p>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
          {!all && terenuri.length > shown.length ? (
            <Button variant="outline" onClick={() => setAll(true)}>
              Arată toate cele {terenuri.length} terenuri
            </Button>
          ) : null}
        </>
      )}
    </section>
  )
}
