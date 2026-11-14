import { Landmark, MapPin, Send } from 'lucide-react'
import type { Impact } from '@/api/models'
import { ErrorState, LoadingCards } from '@/components/StateViews'
import { Card, CardContent } from '@/components/ui/card'
import { useApi } from '@/lib/useApi'
import { useTerenuri } from '@/lib/useTerenuri'

const nf = new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 0 })

export function ImpactPage() {
  const { data, error, loading, reload } = useApi<Impact>('/impact')
  const terenuri = useTerenuri()

  const tiles = data
    ? [
        { icon: MapPin, label: 'Terenuri libere pe hartă', value: terenuri.data ? nf.format(terenuri.terenuri.length) : '–', note: 'candidate pentru amenajare' },
        { icon: Send, label: 'Proiecte trimise', value: nf.format(data.proiecte_trimise), note: 'către Primărie' },
        { icon: Landmark, label: 'Proiecte cu acord', value: nf.format(data.proiecte_cu_acord), note: 'acord de principiu (simulat)' },
      ]
    : []

  return (
    <section className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Tablou de impact</h1>
        <p className="text-muted-foreground">De la terenuri libere la proiecte aprobate în principiu.</p>
      </div>
      {loading && !data ? (
        <LoadingCards count={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
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
