import { Car, Clock, Landmark, Send, Sparkles, Users } from 'lucide-react'
import type { Impact } from '@/api/models'
import { ErrorState, LoadingCards } from '@/components/StateViews'
import { Card, CardContent } from '@/components/ui/card'
import { useApi } from '@/lib/useApi'

const nf = new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 1 })

export function ImpactPage() {
  const { data, error, loading, reload } = useApi<Impact>('/impact')

  const tiles = data
    ? [
        { icon: Clock, label: 'Ore de spații recuperate', value: nf.format(data.ore_recuperate), note: 'din rezervări aprobate' },
        { icon: Users, label: 'Oameni conectați', value: nf.format(data.oameni_conectati), note: 'participanți la activități' },
        { icon: Car, label: 'Km economisiți', value: nf.format(data.km_economisiti), note: 'estimare: drumuri evitate' },
        { icon: Sparkles, label: 'Proiecte active', value: nf.format(data.proiecte_active), note: 'idei care au loc' },
        { icon: Send, label: 'Propuneri trimise', value: nf.format(data.proiecte_trimise), note: 'către Primărie' },
        { icon: Landmark, label: 'Propuneri cu acord', value: nf.format(data.proiecte_cu_acord), note: 'acord de principiu (simulat)' },
      ]
    : []

  return (
    <section className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Tablou de impact</h1>
        <p className="text-muted-foreground">Ce s-a întâmplat în cartiere datorită spațiilor puse în comun.</p>
      </div>
      {loading && !data ? (
        <LoadingCards count={6} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tiles.map(({ icon: Icon, label, value, note }) => (
            <Card key={label}>
              <CardContent className="space-y-3">
                <span className="grid size-9 place-items-center rounded-lg bg-accent text-accent-foreground">
                  <Icon className="size-4.5" />
                </span>
                <div>
                  <p className="text-3xl font-semibold tracking-tight tabular-nums">{value}</p>
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-muted-foreground">{note}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  )
}
