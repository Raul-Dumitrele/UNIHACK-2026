// GET /proiecte is filtered by role on the server (rule 7): author -> own, primarie -> all but drafts,
// verificator -> assigned. One page, a title per role.
import { Link } from 'react-router-dom'
import { ChevronRight, Landmark } from 'lucide-react'
import type { Proiect } from '@/api/models'
import { DemoBadge } from '@/components/DemoBadge'
import { ProiectStatusBadge } from '@/components/proiect/parts'
import { EmptyState, ErrorState, LoadingCards } from '@/components/StateViews'
import { Card, CardContent } from '@/components/ui/card'
import { DEMO_USERS } from '@/demoUsers'
import { fmtLei, timeAgo, tipLabel } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { useUser } from '@/user'

const HEADINGS = {
  primarie: ['Proiecte primite', 'Propunerile trimise de comunitate. Înaintează-le la un verificator.'],
  verificator: ['Proiecte de verificat', 'Propunerile care ți-au fost desemnate. Decide pentru fiecare.'],
  default: ['Proiectele mele', 'Propunerile tale către Primărie și stadiul lor.'],
} as const

export function ProiectePage() {
  const { userId } = useUser()
  const rol = DEMO_USERS.find((u) => u.id === userId)?.rol
  const [title, intro] = rol === 'primarie' || rol === 'verificator' ? HEADINGS[rol] : HEADINGS.default
  const { data, error, loading, reload } = useApi<Proiect[]>('/proiecte')
  const list = [...(data ?? [])].sort((a, b) => b.updated_at.localeCompare(a.updated_at))

  return (
    <section className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="text-muted-foreground">{intro}</p>
      </div>
      {loading && !data ? (
        <LoadingCards count={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : list.length === 0 ? (
        <EmptyState title="Niciun proiect deocamdată">
          {rol === 'primarie' || rol === 'verificator'
            ? 'Când apar propuneri pentru tine, le vezi aici.'
            : 'Din pagina unei idei proprii care a atins pragul, apasă „Propune ca proiect către Primărie”.'}
        </EmptyState>
      ) : (
        <div className="space-y-3">
          {list.map((p) => (
            <Link key={p.id} to={`/proiecte/${p.id}`} className="group block">
              <Card className="transition-shadow group-hover:shadow-md">
                <CardContent className="flex items-center gap-4">
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
                      {p.cost.suficient && p.cost.mediana_lei != null
                        ? `Cost estimat (mediană): ${fmtLei(p.cost.mediana_lei)}`
                        : 'Date insuficiente pentru estimare'}{' '}
                      · actualizat {timeAgo(p.updated_at)}
                    </p>
                  </div>
                  <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
