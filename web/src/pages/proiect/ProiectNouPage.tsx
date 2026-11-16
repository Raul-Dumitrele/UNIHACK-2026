// Wizard in 4 steps: 1) the idea; 2) how the app understood it (the user confirms or corrects); 3) the plot
// (GET /terenuri/potrivite); 4) feasibility on that plot and "Generează proiectul". Interpretation, scores,
// reasons, dossier and cost come from the API, never from the client. A proposal that is too vague is not
// turned into a project unless the user asks for a generic sketch on purpose.
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, CircleHelp, Landmark, Lightbulb, Loader2, PencilLine } from 'lucide-react'
import { toast } from 'sonner'
import { api, describeError } from '@/api/client'
import type { Analiza, Fezabilitate, ProiectDetaliu, ProiectNou, Specificatie, TerenPotrivit } from '@/api/models'
import { FezabilitateCard } from '@/components/proiect/Dosar'
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
const STEPS = ['Ideea ta', 'Cum am înțeles', 'Terenul', 'Proiectul']
const nf = new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 0 })

export function ProiectNouPage() {
  const [params] = useSearchParams()
  const terenParam = params.get('teren') ?? ''
  const navigate = useNavigate()
  const { userId } = useUser()
  const terenuri = useTerenuri()

  const [step, setStep] = useState<1 | 2 | 3 | 4>(1)
  const [tipSel, setTipSel] = useState('')
  const [tipLiber, setTipLiber] = useState('')
  const [descriere, setDescriere] = useState('')
  const [suprafata, setSuprafata] = useState('')
  const [cartier, setCartier] = useState('')
  const [picked, setPicked] = useState<string | null>(null)
  const [busy, setBusy] = useState<'intelegere' | 'teren' | 'generare' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [intelegere, setIntelegere] = useState<Analiza | null>(null) // step 2: the proposal alone
  const [peTeren, setPeTeren] = useState<Analiza | null>(null) // step 4: the proposal on the chosen plot
  const [force, setForce] = useState(false)

  // One of the suggested kinds, or the user's own words ("Altceva").
  const tip = tipSel === ALT ? tipLiber.trim() : tipSel
  const tipText = tipSel === ALT ? tipLiber.trim() : tipSel ? tipLabel(tipSel) : ''
  const fromTeren = terenuri.terenuri.find((s) => s.id === terenParam)
  const spec = intelegere?.specificatie as unknown as Specificatie | undefined
  const fez = intelegere?.fezabilitate as unknown as Fezabilitate | undefined
  const generic = spec?.sursa_specificatie === 'generic'
  // The plot must hold at least what the user asked for, or the minimum the app assumes for this kind.
  const minim = Number(suprafata) > 0 ? Number(suprafata) : (spec?.suprafata_minima_mp ?? 0)

  const query = new URLSearchParams({ tip_amenajare: tip, suprafata_minima: String(minim || ''), limit: '20' })
  if (cartier.trim()) query.set('cartier', cartier.trim())
  const candidates = useApi<TerenPotrivit[]>(step >= 3 && tip && minim > 0 ? `/terenuri/potrivite?${query}` : null)
  const list = candidates.data ?? []
  // The best plot is preselected (or the plot the user came from, if it suits); the user can change it.
  const chosenId = picked && list.some((c) => c.space_id === picked) ? picked : list.some((c) => c.space_id === terenParam) ? terenParam : list[0]?.space_id
  const chosen = list.find((c) => c.space_id === chosenId)

  const isCitizen = DEMO_USERS.find((u) => u.id === userId)?.rol === 'cetatean'
  const step1Ok = tip.length >= 2 && descriere.trim().length >= 10
  const fezTeren = peTeren?.fezabilitate as unknown as Fezabilitate | undefined
  const unrealistic = fezTeren?.nivel === 'nerealist'

  async function understand() {
    setBusy('intelegere')
    setError(null)
    setIntelegere(null)
    try {
      const body = { tip_amenajare: tip, descriere: descriere.trim(), suprafata_mp: Number(suprafata) || null }
      setIntelegere(await api<Analiza>('/proiecte/analiza', { method: 'POST', body: JSON.stringify(body) }))
      setStep(2)
    } catch (err) {
      setError(describeError(err, 'Analiza propunerii'))
    } finally {
      setBusy(null)
    }
  }

  async function analyseOnPlot() {
    if (!chosen) return
    setStep(4)
    setBusy('teren')
    setError(null)
    setPeTeren(null)
    setForce(false)
    try {
      const body = { tip_amenajare: tip, descriere: descriere.trim(), suprafata_mp: null, space_id: chosen.space_id }
      setPeTeren(await api<Analiza>('/proiecte/analiza', { method: 'POST', body: JSON.stringify(body) }))
    } catch (err) {
      setError(describeError(err, 'Analiza pe terenul ales'))
    } finally {
      setBusy(null)
    }
  }

  async function generate() {
    if (!chosen) return
    setBusy('generare')
    setError(null)
    try {
      const body: ProiectNou = { space_id: chosen.space_id, tip_amenajare: tip, descriere: descriere.trim(), suprafata_mp: null }
      const p = await api<ProiectDetaliu>('/proiecte', { method: 'POST', body: JSON.stringify(body) })
      toast.success('Proiectul a fost generat')
      navigate(`/proiecte/${p.id}`)
    } catch (err) {
      setError(describeError(err, 'Generarea proiectului'))
    } finally {
      setBusy(null)
    }
  }

  return (
    <section className="mx-auto max-w-2xl space-y-6">
      <Link to={terenParam ? `/teren/${terenParam}` : '/'} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> {fromTeren ? fromTeren.nume : 'Harta terenurilor'}
      </Link>
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Propune o amenajare</h1>
        <p className="text-muted-foreground">Spune ce ai vrea în cartier. Îți arătăm cum am înțeles ideea, unde ar încăpea și ce presupune.</p>
      </div>

      <ol className="grid grid-cols-4 gap-2 text-xs sm:text-sm" aria-label="Pașii propunerii">
        {STEPS.map((label, i) => {
          const n = i + 1
          const done = step > n
          return (
            <li key={label} aria-current={step === n ? 'step' : undefined} className="space-y-1.5">
              <span className={cn('block h-1.5 rounded-full bg-muted', (done || step === n) && 'bg-primary')} />
              <span className={cn('flex items-center gap-1.5 text-muted-foreground', step === n && 'font-medium text-foreground')}>
                <span
                  className={cn(
                    'grid size-5 shrink-0 place-items-center rounded-full border text-[11px]',
                    done && 'border-primary bg-primary text-primary-foreground',
                    step === n && 'border-primary text-primary',
                  )}
                >
                  {done ? <Check className="size-3" /> : n}
                </span>
                <span className="truncate">{label}</span>
              </span>
            </li>
          )
        })}
      </ol>

      {!isCitizen ? (
        <ErrorState message="Propunerile le fac locuitorii. Alege un locuitor din lista „Văd aplicația ca” din dreapta sus." />
      ) : (
        <Card>
          <CardContent className="space-y-5">
            {step === 1 ? (
              <>
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium">Ce fel de amenajare?</span>
                  <Select value={tipSel} onValueChange={setTipSel}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Alege din listă" />
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
                    <span className="text-sm font-medium">Scrie cu cuvintele tale</span>
                    <Input value={tipLiber} onChange={(e) => setTipLiber(e.target.value)} placeholder="ex. foișor, parc acvatic, fântână cu apă de băut" />
                  </label>
                ) : null}
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium">Ce vă doriți și pentru cine?</span>
                  <Textarea
                    value={descriere}
                    onChange={(e) => setDescriere(e.target.value)}
                    rows={4}
                    placeholder="ex. Un loc de joacă pentru copiii de la blocuri, cu leagăne, tobogan și bănci pentru părinți."
                  />
                  <span className="text-xs text-muted-foreground">Câteva cuvinte sunt de ajuns (minimum 10 caractere).</span>
                </label>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block space-y-1.5">
                    <span className="text-sm font-medium">
                      Cartier <span className="font-normal text-muted-foreground">(opțional)</span>
                    </span>
                    <Input value={cartier} onChange={(e) => setCartier(e.target.value)} placeholder="ex. Mehala" />
                  </label>
                  <label className="block space-y-1.5">
                    <span className="text-sm font-medium">
                      Suprafață dorită, mp <span className="font-normal text-muted-foreground">(opțional)</span>
                    </span>
                    <Input type="number" min={1} value={suprafata} onChange={(e) => setSuprafata(e.target.value)} placeholder="o propunem noi" />
                  </label>
                </div>
                {error ? <p className="text-sm text-destructive">{error}</p> : null}
                <Button size="lg" onClick={understand} disabled={!step1Ok || busy !== null}>
                  {busy === 'intelegere' ? <Loader2 className="animate-spin" /> : <Lightbulb />} Analizează ideea
                </Button>
              </>
            ) : step === 2 && spec && fez ? (
              <>
                <div className={cn('space-y-2 rounded-xl border p-4', generic || fez.interpretare_diferita ? 'border-demo/30 bg-demo-soft' : 'border-primary/20 bg-accent/40')}>
                  <p className="flex items-center gap-2 text-sm text-muted-foreground">
                    <CircleHelp className="size-4" /> Ai scris: „{tipText}”
                  </p>
                  <p className="text-lg font-semibold">{fez.interpretare ?? `Am interpretat propunerea ca: ${spec.eticheta}`}</p>
                  {generic ? (
                    <p className="text-sm">{fez.motive[0]}.</p>
                  ) : fez.interpretare_diferita ? (
                    <p className="text-sm">Nu e exact ce ai scris. Dacă nu asta voiai, întoarce-te și descrie altfel.</p>
                  ) : null}
                </div>

                {generic ? null : (
                  <div className="space-y-3 text-sm">
                    <p className="font-medium">Ce presupune, pe scurt</p>
                    <div className="flex flex-wrap gap-2 text-xs">
                      <Badge variant="outline">cel puțin {nf.format(spec.suprafata_minima_mp)} mp</Badge>
                      {spec.suprafata_recomandata_mp ? <Badge variant="outline">recomandat {nf.format(spec.suprafata_recomandata_mp)} mp</Badge> : null}
                      {(spec.utilitati_necesare ?? []).map((u) => (
                        <Badge key={u} variant="outline">
                          {u}
                        </Badge>
                      ))}
                    </div>
                    <ul className="list-disc space-y-0.5 pl-5 text-muted-foreground">
                      {spec.componente
                        .filter((c) => c.obligatoriu)
                        .slice(0, 6)
                        .map((c) => (
                          <li key={c.nume}>{c.nume}</li>
                        ))}
                    </ul>
                    <p className="text-xs text-muted-foreground">Suprafețele și componentele sunt ipoteze orientative ale aplicației; proiectantul le stabilește.</p>
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button variant={generic ? 'default' : 'outline'} size={generic ? 'lg' : 'default'} onClick={() => setStep(1)}>
                    <PencilLine /> {generic ? 'Înapoi la pasul 1: descrie mai concret' : 'Nu, modific propunerea'}
                  </Button>
                  {generic ? (
                    <Button variant="ghost" onClick={() => setStep(3)}>
                      Continuă doar cu o schiță generică
                    </Button>
                  ) : (
                    <Button size="lg" onClick={() => setStep(3)}>
                      Da, caută terenuri <ArrowRight />
                    </Button>
                  )}
                </div>
              </>
            ) : step === 3 ? (
              <>
                <p className="text-sm text-muted-foreground">
                  Terenuri de cel puțin {nf.format(minim)} mp pentru {spec?.eticheta ?? tipText}, de la cel mai potrivit. Primul e ales deja; poți alege
                  altul.
                </p>
                {candidates.loading && !candidates.data ? (
                  <LoadingCards count={2} />
                ) : candidates.error ? (
                  <ErrorState message={describeError(new Error(candidates.error), 'Alegerea terenului')} onRetry={candidates.reload} />
                ) : list.length === 0 ? (
                  <EmptyState title="Niciun teren potrivit">
                    Nu am găsit terenuri de cel puțin {nf.format(minim)} mp. Încearcă o suprafață mai mică sau marchează pe hartă un teren pe care îl
                    știi.
                  </EmptyState>
                ) : (
                  <ul className="max-h-[26rem] space-y-2 overflow-y-auto pr-1" role="radiogroup" aria-label="Terenuri potrivite">
                    {list.map((c) => (
                      <li key={c.space_id}>
                        <PlotOption c={c} selected={c.space_id === chosenId} onSelect={() => setPicked(c.space_id)} />
                      </li>
                    ))}
                  </ul>
                )}
                {list.length > 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Terenurile sunt candidați, nu terenuri confirmate ca libere. Surse: © OpenStreetMap contributors (ODbL) și lista Primăriei (HCL
                    20/2019).
                  </p>
                ) : null}
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setStep(2)}>
                    <ArrowLeft /> Înapoi
                  </Button>
                  <Button size="lg" onClick={analyseOnPlot} disabled={!chosen}>
                    Verifică pe acest teren <ArrowRight />
                  </Button>
                </div>
              </>
            ) : (
              <>
                <dl className="space-y-2 text-sm">
                  <Row label="Amenajare" value={spec?.eticheta ?? tipText} />
                  <Row label="Teren" value={chosen ? `${chosen.nume} · ${nf.format(chosen.suprafata_mp)} mp` : '–'} />
                  <Row label="Ideea ta" value={descriere.trim()} />
                </dl>
                {busy === 'teren' ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="size-4 animate-spin" /> Verificăm dacă amenajarea încape și ce ar trebui clarificat…
                  </div>
                ) : fezTeren ? (
                  <FezabilitateCard fez={fezTeren} compact />
                ) : null}
                {unrealistic ? (
                  <label className="flex items-start gap-2 text-sm">
                    <input type="checkbox" className="mt-1" checked={force} onChange={(e) => setForce(e.target.checked)} />
                    <span>Am citit motivele și vreau totuși dosarul. Va purta avertismentul „nerealistă pe acest teren”.</span>
                  </label>
                ) : null}
                {busy === 'generare' ? (
                  <div className="flex items-start gap-3 rounded-lg bg-muted/60 p-3 text-sm">
                    <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin" />
                    <span>Pregătim dosarul, planul și lista de materiale. Durează de obicei câteva secunde, uneori până la un minut; nu închide pagina.</span>
                  </div>
                ) : null}
                {error ? <p className="text-sm text-destructive">{error}</p> : null}
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" onClick={() => setStep(3)} disabled={busy !== null}>
                    <ArrowLeft /> Alt teren
                  </Button>
                  <Button size="lg" onClick={generate} disabled={busy !== null || !chosen || !fezTeren || (unrealistic && !force)}>
                    {busy === 'generare' ? <Loader2 className="animate-spin" /> : <Landmark />} Generează proiectul
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
      <div className="flex items-start gap-2">
        <span className={cn('mt-0.5 grid size-4 shrink-0 place-items-center rounded-full border', selected && 'border-primary bg-primary text-primary-foreground')}>
          {selected ? <Check className="size-3" /> : null}
        </span>
        <span className="min-w-0 flex-1 font-medium">{c.nume}</span>
        <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs font-medium tabular-nums" title="Scor de potrivire, orientativ">
          {c.scor}/100
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2 pl-6 text-xs">
        <Badge variant="outline">{nf.format(c.suprafata_mp)} mp</Badge>
        {c.cartier ? <span className="text-muted-foreground">{c.cartier}</span> : null}
        {c.din_lista_primarie ? (
          <Badge variant="outline" className="border-demo/40 bg-demo-soft text-demo">
            din lista Primăriei – de confirmat
          </Badge>
        ) : null}
        <DemoBadge show={c.is_demo} />
      </div>
      <p className="pl-6 text-sm text-muted-foreground">{c.motiv}</p>
      {!c.complet ? <p className="pl-6 text-sm font-medium text-destructive">Amenajarea nu încape în întregime pe acest teren.</p> : null}
      {c.avertisment ? <p className="ml-6 rounded-lg border border-demo/30 bg-demo-soft p-2 text-xs text-demo">{c.avertisment}</p> : null}
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
