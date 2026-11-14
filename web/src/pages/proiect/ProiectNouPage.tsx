// Wizard in 3 steps. 1) what to build, for whom, how big; 2) choose the plot (GET /terenuri/potrivite, ranked by
// P3's find_plots); 3) review and "Generează proiectul". Scores, reasons, dossier, budget, references and cost
// come from the API, never from the client. Generation can take 10-30 s (up to ~1 min with live search).
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Landmark, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { api, describeError } from '@/api/client'
import type { ProiectDetaliu, ProiectNou, TerenPotrivit } from '@/api/models'
import { DemoBadge } from '@/components/DemoBadge'
import { Disclaimer } from '@/components/proiect/parts'
import { EmptyState, ErrorState, LoadingCards } from '@/components/StateViews'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { DEMO_USERS } from '@/demoUsers'
import { TIP_AMENAJARE, tipLabel } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { useTerenuri } from '@/lib/useTerenuri'
import { cn } from '@/lib/utils'
import { useUser } from '@/user'

const ALT = '__altceva'
const STEPS = ['Ce vrei să construiești', 'Alege terenul', 'Generează proiectul']

export function ProiectNouPage() {
  const [params] = useSearchParams()
  const terenParam = params.get('teren') ?? ''
  const navigate = useNavigate()
  const { userId } = useUser()
  const terenuri = useTerenuri()

  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [tipSel, setTipSel] = useState('')
  const [tipLiber, setTipLiber] = useState('')
  const [descriere, setDescriere] = useState('')
  const [suprafata, setSuprafata] = useState<string | null>(null)
  const [cartier, setCartier] = useState('')
  const [picked, setPicked] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // One of the known kinds, or any text ("Altceva"): the server decides if it accepts it and answers with a `detail`.
  const tip = tipSel === ALT ? tipLiber.trim().toLowerCase().replace(/\s+/g, '_') : tipSel
  const fromTeren = terenuri.terenuri.find((s) => s.id === terenParam)
  const area = suprafata ?? (fromTeren?.suprafata_mp != null ? String(fromTeren.suprafata_mp) : '')
  const areaOk = Number(area) > 0

  const query = new URLSearchParams({ tip_amenajare: tip, suprafata_minima: String(Number(area) || ''), limit: '20' })
  if (cartier.trim()) query.set('cartier', cartier.trim())
  const candidates = useApi<TerenPotrivit[]>(step >= 2 && tip && areaOk ? `/terenuri/potrivite?${query}` : null)

  const list = candidates.data ?? []
  // The first result is preselected (or the plot the user came from, if it is in the list); the user can change it.
  const chosenId = picked && list.some((c) => c.space_id === picked) ? picked : list.some((c) => c.space_id === terenParam) ? terenParam : list[0]?.space_id
  const chosen = list.find((c) => c.space_id === chosenId)

  const isCitizen = DEMO_USERS.find((u) => u.id === userId)?.rol === 'cetatean'
  const step1Ok = !!tip && descriere.trim().length >= 10 && areaOk

  async function generate() {
    if (!tip || !chosen) return
    setSending(true)
    setError(null)
    try {
      const body: ProiectNou = { space_id: chosen.space_id, tip_amenajare: tip, descriere: descriere.trim(), suprafata_mp: Number(area) }
      const p = await api<ProiectDetaliu>('/proiecte', { method: 'POST', body: JSON.stringify(body) })
      toast.success('Proiectul a fost generat')
      navigate(`/proiecte/${p.id}`)
    } catch (err) {
      setError(describeError(err, 'Generarea proiectului'))
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="mx-auto max-w-2xl space-y-6">
      <Link to={terenParam ? `/teren/${terenParam}` : '/'} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> {fromTeren ? fromTeren.nume : 'Harta terenurilor'}
      </Link>
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Propune un proiect</h1>
        <p className="text-muted-foreground">
          Spui ce vrei să construiești; aplicația găsește terenurile potrivite și pregătește dosarul complet: buget, plan, materiale, acte și
          proiecte de referință.
        </p>
      </div>

      <ol className="flex flex-wrap gap-2 text-sm">
        {STEPS.map((label, i) => (
          <li
            key={label}
            className={cn(
              'flex items-center gap-2 rounded-full border px-3 py-1',
              step === i + 1 ? 'border-primary bg-primary text-primary-foreground' : 'text-muted-foreground',
            )}
          >
            <span className="font-semibold">{i + 1}</span> {label}
          </li>
        ))}
      </ol>

      {!isCitizen ? (
        <ErrorState message="Doar cetățenii pot propune proiecte. Alege un cetățean din selectorul de sus." />
      ) : (
        <Card>
          <CardContent className="space-y-4">
            {step === 1 ? (
              <>
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium">Tipul amenajării</span>
                  <Select value={tipSel} onValueChange={setTipSel}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Alege tipul" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(TIP_AMENAJARE).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                      <SelectItem value={ALT}>Altceva…</SelectItem>
                    </SelectContent>
                  </Select>
                </label>
                {tipSel === ALT ? (
                  <label className="block space-y-1.5">
                    <span className="text-sm font-medium">Ce fel de amenajare?</span>
                    <Input value={tipLiber} onChange={(e) => setTipLiber(e.target.value)} placeholder="ex. foișor, parc acvatic, fântână" />
                    <span className="text-xs text-muted-foreground">Pentru un tip care nu e în listă, planul schematic arată o zonă propusă și mobilier de bază.</span>
                  </label>
                ) : null}
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium">Ce vreți aici și pentru cine?</span>
                  <Textarea
                    value={descriere}
                    onChange={(e) => setDescriere(e.target.value)}
                    rows={5}
                    placeholder="ex. Un skatepark mic pentru adolescenții din cartier, cu câteva rampe și bănci."
                  />
                  <span className="text-xs text-muted-foreground">Minimum 10 caractere.</span>
                </label>
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium">Suprafața de care ai nevoie (mp)</span>
                  <Input type="number" min={1} value={area} onChange={(e) => setSuprafata(e.target.value)} />
                  <span className="text-xs text-muted-foreground">Terenurile mai mici nu apar în pasul următor.</span>
                </label>
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium">Cartier (opțional)</span>
                  <Input value={cartier} onChange={(e) => setCartier(e.target.value)} placeholder="ex. Ronaț" />
                  <span className="text-xs text-muted-foreground">Terenurile din cartier primesc un scor mai bun.</span>
                </label>
                <Button onClick={() => setStep(2)} disabled={!step1Ok}>
                  Continuă <ArrowRight />
                </Button>
              </>
            ) : step === 2 ? (
              <>
                <p className="text-sm text-muted-foreground">
                  Terenuri libere pentru {tip ? tipLabel(tip).toLowerCase() : 'proiectul tău'}, de cel puțin {area} mp, de la cel mai potrivit.
                </p>
                {candidates.loading && !candidates.data ? (
                  <LoadingCards count={2} />
                ) : candidates.error ? (
                  <ErrorState message={describeError(new Error(candidates.error), 'Alegerea terenului')} onRetry={candidates.reload} />
                ) : list.length === 0 ? (
                  <EmptyState title="Niciun teren potrivit">
                    Nu am găsit terenuri libere de cel puțin {area} mp pentru acest tip. Încearcă o suprafață mai mică sau marchează un teren nou pe
                    hartă.
                  </EmptyState>
                ) : (
                  <ul className="space-y-2" role="radiogroup" aria-label="Terenuri potrivite">
                    {list.map((c) => (
                      <li key={c.space_id}>
                        <PlotOption c={c} selected={c.space_id === chosenId} onSelect={() => setPicked(c.space_id)} />
                      </li>
                    ))}
                  </ul>
                )}
                {list.length > 0 ? <p className="text-xs text-muted-foreground">Date despre terenuri: © OpenStreetMap contributors (ODbL) și lista Primăriei (HCL 20/2019).</p> : null}
                {terenParam && fromTeren && list.length > 0 && !list.some((c) => c.space_id === terenParam) ? (
                  <p className="text-xs text-muted-foreground">„{fromTeren.nume}” nu apare în listă: nu se potrivește cu tipul sau suprafața alese.</p>
                ) : null}
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setStep(1)}>
                    <ArrowLeft /> Înapoi
                  </Button>
                  <Button onClick={() => setStep(3)} disabled={!chosen}>
                    Continuă <ArrowRight />
                  </Button>
                </div>
              </>
            ) : (
              <>
                <dl className="space-y-3 text-sm">
                  <Row label="Teren" value={chosen?.nume ?? '–'} />
                  <Row label="Amenajare" value={tip ? tipLabel(tip) : '–'} />
                  <Row label="Suprafață" value={`${area} mp`} />
                  <Row label="Descriere" value={descriere.trim()} />
                </dl>
                {sending ? (
                  <div className="flex items-start gap-3 rounded-lg bg-muted/60 p-3 text-sm">
                    <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin" />
                    <span>
                      Căutăm proiecte de referință, estimăm costul și scriem dosarul. Poate dura între 10 și 30 de secunde, uneori până la un minut; nu
                      închide pagina.
                    </span>
                  </div>
                ) : null}
                {error ? <p className="text-sm text-destructive">{error}</p> : null}
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setStep(2)} disabled={sending}>
                    <ArrowLeft /> Înapoi
                  </Button>
                  <Button onClick={generate} disabled={sending || !chosen}>
                    {sending ? <Loader2 className="animate-spin" /> : <Landmark />} Generează proiectul
                  </Button>
                </div>
                <Disclaimer />
              </>
            )}
          </CardContent>
        </Card>
      )}
    </section>
  )
}

function PlotOption({ c, selected, onSelect }: { c: TerenPotrivit; selected: boolean; onSelect: () => void }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn('w-full space-y-1.5 rounded-xl border p-3 text-left transition-colors hover:bg-muted/50', selected && 'border-primary bg-accent/40')}
    >
      <div className="flex flex-wrap items-center gap-2">
        {selected ? <Check className="size-4 text-primary" /> : null}
        <span className="font-medium">{c.nume}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Badge variant="outline">{c.suprafata_mp} mp</Badge>
        <Badge variant="outline" className="border-primary/30 bg-accent text-accent-foreground">
          scor {c.scor}/100
        </Badge>
        {c.cartier ? <span className="text-muted-foreground">{c.cartier}</span> : null}
        {c.din_lista_primarie ? (
          <Badge variant="outline" className="border-demo/40 bg-demo-soft text-demo">
            din lista Primăriei – de confirmat
          </Badge>
        ) : null}
        <DemoBadge show={c.is_demo} />
      </div>
      <p className="text-sm text-muted-foreground">{c.motiv}</p>
      {!c.complet ? <p className="text-sm font-medium text-destructive">Amenajarea nu încape în întregime pe acest teren.</p> : null}
      {c.avertisment ? <p className="rounded-lg border border-demo/30 bg-demo-soft p-2 text-xs text-demo">{c.avertisment}</p> : null}
    </button>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[110px_1fr]">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="whitespace-pre-line">{value}</dd>
    </div>
  )
}
