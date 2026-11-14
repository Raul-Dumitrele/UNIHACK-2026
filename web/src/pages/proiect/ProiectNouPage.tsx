// POST /ideas/{id}/proiect (rule 6). References, cost and dossier are produced by the API; the call can
// take up to a minute when P3's live reference search runs, so the waiting state says what is happening.
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Landmark, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import type { Idea, ProiectCreate, ProiectDetaliu, Space, TipAmenajare } from '@/api/models'
import { Disclaimer } from '@/components/proiect/parts'
import { ErrorState, LoadingCards } from '@/components/StateViews'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from '@/components/ui/select'
import { isFreePlot, TIP_AMENAJARE } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { useUser } from '@/user'

export function ProiectNouPage() {
  const [params] = useSearchParams()
  const ideaId = params.get('idea') ?? ''
  const navigate = useNavigate()
  const { userId } = useUser()
  const idea = useApi<Idea>(ideaId ? `/ideas/${ideaId}` : null)
  const spaces = useApi<Space[]>('/spaces')

  const [tip, setTip] = useState<TipAmenajare | ''>('')
  const [spaceId, setSpaceId] = useState('')
  const [suprafata, setSuprafata] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!ideaId) return <ErrorState message="Lipsește ideea pentru care faci propunerea." />
  if ((idea.loading && !idea.data) || (spaces.loading && !spaces.data)) return <LoadingCards count={2} />
  if (idea.error || !idea.data) return <ErrorState message={idea.error ?? 'Ideea nu există.'} onRetry={idea.reload} />
  if (spaces.error) return <ErrorState message={spaces.error} onRetry={spaces.reload} />

  const i = idea.data
  const plots = (spaces.data ?? []).filter((s) => isFreePlot(s.tip))
  const others = (spaces.data ?? []).filter((s) => !isFreePlot(s.tip))
  const space = (spaces.data ?? []).find((s) => s.id === spaceId)
  const needsArea = !!space && space.suprafata_mp == null
  const allowed = i.author_id === userId && (i.stare === 'prag_atins' || i.stare === 'rezervata')

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!tip || !spaceId) return
    setSending(true)
    setError(null)
    try {
      const body: ProiectCreate = {
        space_id: spaceId,
        tip_amenajare: tip,
        suprafata_mp: needsArea ? Number(suprafata) : null,
      }
      const p = await api<ProiectDetaliu>(`/ideas/${i.id}/proiect`, { method: 'POST', body: JSON.stringify(body) })
      toast.success('Dosarul a fost generat')
      navigate(`/proiecte/${p.id}`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="mx-auto max-w-2xl space-y-6">
      <Link to={`/idei/${i.id}`} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Înapoi la idee
      </Link>
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Propune ca proiect către Primărie</h1>
        <p className="text-muted-foreground">
          Pornind de la „{i.titlu}”. Alegi tipul amenajării și locul; aplicația caută proiecte de referință, estimează costul
          și scrie dosarul.
        </p>
      </div>

      {!allowed ? (
        <ErrorState message="Doar autorul ideii poate face o propunere, după ce ideea a atins pragul sau are o rezervare." />
      ) : (
        <Card>
          <CardContent>
            <form onSubmit={submit} className="space-y-4">
              <label className="block space-y-1.5">
                <span className="text-sm font-medium">Tipul amenajării</span>
                <Select value={tip} onValueChange={(v) => setTip(v as TipAmenajare)}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Alege tipul" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(TIP_AMENAJARE).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium">Locul</span>
                <Select value={spaceId} onValueChange={setSpaceId}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Alege terenul sau spațiul" />
                  </SelectTrigger>
                  <SelectContent>
                    {plots.length ? (
                      <SelectGroup>
                        <SelectLabel>Terenuri libere</SelectLabel>
                        {plots.map((s) => (
                          <SelectItem key={s.id} value={s.id}>
                            {s.nume}
                            {s.suprafata_mp ? ` · ${s.suprafata_mp} mp` : ''}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    ) : null}
                    <SelectGroup>
                      <SelectLabel>Alte spații</SelectLabel>
                      {others.map((s) => (
                        <SelectItem key={s.id} value={s.id}>
                          {s.nume}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </label>
              {needsArea ? (
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium">Suprafața propusă (mp)</span>
                  <Input type="number" min={1} value={suprafata} onChange={(e) => setSuprafata(e.target.value)} required />
                  <span className="text-xs text-muted-foreground">Spațiul ales nu are suprafața înregistrată.</span>
                </label>
              ) : null}

              {sending ? (
                <div className="flex items-start gap-3 rounded-lg bg-muted/60 p-3 text-sm">
                  <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin" />
                  <span>
                    Căutăm proiecte de referință, estimăm costul și scriem dosarul. Poate dura până la un minut; nu închide
                    pagina.
                  </span>
                </div>
              ) : null}
              {error ? <p className="text-sm text-destructive">{error}</p> : null}
              <Button type="submit" disabled={sending || !tip || !spaceId || (needsArea && !Number(suprafata))}>
                {sending ? <Loader2 className="animate-spin" /> : <Landmark />} Generează dosarul
              </Button>
              <Disclaimer />
            </form>
          </CardContent>
        </Card>
      )}
    </section>
  )
}
