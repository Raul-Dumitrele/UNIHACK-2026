import { CheckCircle2, Landmark, MapPin, Send, ThumbsUp, Users, Vote } from 'lucide-react'
import type { Impact } from '@/api/models'
import { ErrorState, LoadingCards } from '@/components/StateViews'
import { Card, CardContent } from '@/components/ui/card'
import { useApi } from '@/lib/useApi'

const nf = new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 0 })

export function ImpactPage() {
  const { data, error, loading, reload } = useApi<Impact>('/impact')

  const tiles = data
    ? [
        { icon: MapPin, label: 'Terenuri libere pe hartă', value: data.terenuri_libere ?? 0, note: 'candidate pentru amenajare (de confirmat cu Primăria)' },
        { icon: Landmark, label: 'Proiecte propuse', value: data.proiecte_propuse ?? 0, note: 'dosare generate de locuitori' },
        { icon: Vote, label: 'În vot acum', value: data.proiecte_publicate ?? 0, note: 'publicate, așteaptă susținători' },
        { icon: ThumbsUp, label: 'Voturi exprimate', value: data.voturi_total ?? 0, note: 'un vot per persoană per proiect' },
        { icon: Users, label: 'Oameni implicați', value: data.oameni_implicati ?? 0, note: 'autori și votanți distincți' },
        { icon: Send, label: 'Trimise la Primărie', value: data.proiecte_trimise, note: `${nf.format(data.proiecte_peste_prag ?? 0)} au trecut pragul de voturi` },
        { icon: CheckCircle2, label: 'Cu acord de principiu', value: data.proiecte_cu_acord, note: 'acord simulat, în aplicație' },
      ]
    : []

  return (
    <section className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Tablou de impact</h1>
        <p className="text-muted-foreground">De la terenuri libere la proiecte votate de comunitate și aprobate în principiu.</p>
      </div>
      {loading && !data ? (
        <LoadingCards count={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {tiles.map(({ icon: Icon, label, value, note }) => (
            <Card key={label}>
              <CardContent className="space-y-3">
                <span className="grid size-9 place-items-center rounded-lg bg-accent text-accent-foreground">
                  <Icon className="size-4.5" />
                </span>
                <div>
                  <p className="text-3xl font-semibold tracking-tight tabular-nums">{nf.format(value)}</p>
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-muted-foreground">{note}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        Toate valorile vin din baza de date a aplicației (proiecte, voturi, terenuri). Acordul de principiu este simulat; deciziile reale le ia
        Primăria.
      </p>
    </section>
  )
}
