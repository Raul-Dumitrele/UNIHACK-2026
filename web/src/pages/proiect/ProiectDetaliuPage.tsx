// One complete project, in four tabs: "Rezumat" (how the idea was understood, what comes next, feasibility, cost,
// plot), "Dosar" (memorandum, specification, stages, risks, questions, references), "Avize și cereri" (documents to
// check, request templates), "Planșe și materiale" (plan 2D/3D, downloads, materials).
// Beside them: support (votes), the one action the current role may take, and the history.
// Printable (Save as PDF) via the print: utilities and @media print in index.css.
import { useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Loader2, Megaphone, Printer, Send, Users } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import type { Act, CerereTip, Fezabilitate, Proiect, ProiectDetaliu, Space, Specificatie } from '@/api/models'
import { DemoBadge } from '@/components/DemoBadge'
import { DocumenteTab } from '@/components/proiect/Documente'
import { ActeBlock, CereriTipBlock, FezabilitateCard, MemoriuBlock, SpecificatieBlock } from '@/components/proiect/Dosar'
import {
  BulletList, CostBlock, Disclaimer, EtapeList, EvenimenteTimeline, ProiectStatusBadge, ReferinteList, Rezumat, VotButon,
} from '@/components/proiect/parts'
import { ErrorState, LoadingCards } from '@/components/StateViews'
import { TerenMap } from '@/components/TerenMap'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { DEMO_USERS } from '@/demoUsers'
import { fmtDate, isFreePlot, tipLabel } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { cn } from '@/lib/utils'
import { useUser } from '@/user'

/** What the reader can expect next, in plain words, for every state of the project. */
const URMEAZA: Record<string, string> = {
  draft: 'Publică proiectul ca vecinii să îl poată susține. La pragul de susținători pleacă automat la Primărie; îl poți trimite și direct.',
  publicat: 'Proiectul adună susținători. Când atinge pragul, pleacă automat la Primărie.',
  trimis: 'Proiectul este la Primărie, care îl înaintează unui verificator.',
  in_verificare: 'Un verificator analizează dosarul și decide: acord de principiu, clarificări sau respingere.',
  clarificari: 'Verificatorul a cerut clarificări. Autorul răspunde și retrimite proiectul.',
  acord_de_principiu: 'Proiectul are acord de principiu (simulat în aplicație). Pașii reali încep cu certificatul de urbanism, vezi „Avize și cereri”.',
  respins: 'Proiectul a fost respins; motivul este în istoric. Poți propune o variantă nouă.',
}
const SURSA_TEREN: Record<string, string> = {
  osm: 'Candidat din OpenStreetMap, neconfirmat.',
  lista_primarie: 'Din lista Primăriei (Legea 15/2003) – de confirmat.',
  marcat_de_utilizator: 'Marcat pe hartă de un locuitor, neverificat.',
  demo: 'Teren demonstrativ (exemplu).',
}

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="break-inside-avoid print:border-0 print:shadow-none">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">{children}</CardContent>
    </Card>
  )
}

export function ProiectDetaliuPage() {
  const { id = '' } = useParams()
  const { userId } = useUser()
  const pr = useApi<ProiectDetaliu>(`/proiecte/${id}`)
  const spaces = useApi<Space[]>('/spaces')

  if (pr.loading && !pr.data) return <LoadingCards count={3} />
  if (pr.error || !pr.data) return <ErrorState message={pr.error ?? 'Proiectul nu există.'} onRetry={pr.reload} />

  const p = pr.data
  const dosar = p.dosar
  const me = DEMO_USERS.find((u) => u.id === userId)
  const autor = DEMO_USERS.find((u) => u.id === p.autor_id)
  const verificator = DEMO_USERS.find((u) => u.id === p.verificator_id)
  const space = spaces.data?.find((s) => s.id === p.space_id)
  const teren = space && isFreePlot(space.tip) ? space : undefined
  const spec = (p.specificatie as unknown as Specificatie | null) ?? null
  const fez = (p.fezabilitate as unknown as Fezabilitate | null) ?? null
  const memoriu = (dosar.memoriu ?? {}) as Record<string, string>
  const acte = (dosar.acte ?? []) as unknown as Act[]
  const cereri = (dosar.cereri_tip ?? []) as unknown as CerereTip[]

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link to="/proiecte" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" /> Proiecte
        </Link>
        <Button variant="outline" size="sm" onClick={() => window.print()}>
          <Printer /> Tipărește pagina
        </Button>
      </div>

      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <ProiectStatusBadge stare={p.stare} />
          <DemoBadge show={p.is_demo} />
          <span className="text-sm text-muted-foreground">
            {tipLabel(p.tip_amenajare)} · {p.suprafata_mp} mp
          </span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">{dosar.titlu}</h1>
        <p className="text-sm text-muted-foreground">
          Propus de {autor?.nume ?? p.autor_id}
          {space ? (
            <>
              {' · '}
              <Link to={`/teren/${space.id}`} className="underline print:no-underline">
                {space.nume}
              </Link>
            </>
          ) : null}{' '}
          · creat {fmtDate(p.created_at)}
          {verificator ? ` · verificator: ${verificator.nume}` : ''}
        </p>
        <Disclaimer />
      </header>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px] print:block">
        <Tabs defaultValue="rezumat" className="min-w-0">
          <TabsList className="flex-wrap print:hidden">
            <TabsTrigger value="rezumat">Rezumat</TabsTrigger>
            <TabsTrigger value="dosar">Dosar</TabsTrigger>
            <TabsTrigger value="avize">Avize și cereri</TabsTrigger>
            <TabsTrigger value="documente">Planșe și materiale</TabsTrigger>
          </TabsList>

          {/* What the project is, whether it is realistic, what it may cost, what happens next. */}
          <TabsContent value="rezumat" className="mt-4 space-y-6">
            <Card className="border-primary/20 bg-accent/30 print:border-0 print:shadow-none">
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">{fez?.interpretare ?? `Propunere: ${spec?.eticheta ?? tipLabel(p.tip_amenajare)}`}</p>
                <p className="whitespace-pre-line">{dosar.descriere}</p>
                <p className="flex items-start gap-2 rounded-lg bg-background/70 p-3 text-sm">
                  <ArrowRight className="mt-0.5 size-4 shrink-0 text-primary" />
                  <span>
                    <span className="font-medium">Ce urmează: </span>
                    {URMEAZA[p.stare] ?? ''}
                  </span>
                </p>
              </CardContent>
            </Card>
            {fez ? (
              <Block title="Este realist?">
                <FezabilitateCard fez={fez} />
              </Block>
            ) : null}
            <Block title="Cât ar putea costa">
              <CostBlock cost={p.cost} />
              <Disclaimer />
            </Block>
            {teren ? (
              <Block title="Terenul">
                <TerenMap terenuri={[teren]} center={[teren.lat, teren.lng]} zoom={16} compact className="h-56 w-full print:hidden" />
                <p className="text-sm">
                  <Link to={`/teren/${teren.id}`} className="font-medium underline print:no-underline">
                    {teren.nume}
                  </Link>
                  {teren.suprafata_mp ? ` · ${teren.suprafata_mp} mp` : ''}
                  {teren.cartier ? ` · ${teren.cartier}` : ''}
                </p>
                <p className="text-sm text-muted-foreground">
                  {SURSA_TEREN[teren.sursa ?? ''] ?? 'Teren propus.'} Proprietarul, regimul juridic și disponibilitatea terenului se confirmă de Primărie.
                </p>
              </Block>
            ) : null}
          </TabsContent>

          {/* The written dossier: memorandum, specification, stages, risks, questions, references. */}
          <TabsContent value="dosar" className="mt-4 space-y-6">
            {Object.keys(memoriu).length ? (
              <Block title="Memoriu descriptiv">
                <MemoriuBlock memoriu={memoriu} />
              </Block>
            ) : (
              <Block title="Descriere">
                <Rezumat dosar={dosar} />
              </Block>
            )}
            {spec ? (
              <Block title="Ce cuprinde amenajarea">
                <SpecificatieBlock spec={spec} />
              </Block>
            ) : null}
            {dosar.etape.length ? (
              <Block title="Etape">
                <EtapeList etape={dosar.etape} />
              </Block>
            ) : null}
            {dosar.riscuri.length ? (
              <Block title="Riscuri">
                <BulletList items={dosar.riscuri} />
              </Block>
            ) : null}
            {dosar.lista_verificare.length ? (
              <Block title="Întrebări pentru Primărie">
                <BulletList items={dosar.lista_verificare} />
              </Block>
            ) : null}
            <Block title="Proiecte de referință">
              <ReferinteList referinte={p.referinte} />
            </Block>
          </TabsContent>

          {/* Permits to check and ready-made request texts. */}
          <TabsContent value="avize" className="mt-4 space-y-6">
            {acte.length ? (
              <Block title="Documente și avize de verificat">
                <ActeBlock acte={acte} disclaimer={dosar.acte_disclaimer} />
              </Block>
            ) : (
              <Block title="Documente și avize de verificat">
                <p className="text-sm text-muted-foreground">Acest proiect nu are o listă de documente. Lista o stabilește Primăria prin certificatul de urbanism.</p>
              </Block>
            )}
            {cereri.length ? (
              <Block title="Cereri gata de completat">
                <CereriTipBlock cereri={cereri} />
              </Block>
            ) : null}
          </TabsContent>

          <TabsContent value="documente" className="mt-4">
            <DocumenteTab proiectId={p.id} />
          </TabsContent>
        </Tabs>
        <aside className="space-y-6 print:mt-6">
          <Sustinere p={p} onChange={pr.reload} />
          {me ? <Actions p={p} me={me} onChange={pr.reload} /> : null}
          <Card className="print:border-0 print:shadow-none">
            <CardHeader>
              <CardTitle>Istoric</CardTitle>
            </CardHeader>
            <CardContent>
              <EvenimenteTimeline evenimente={p.evenimente} />
            </CardContent>
          </Card>
        </aside>
      </div>
    </section>
  )
}

function Sustinere({ p, onChange }: { p: ProiectDetaliu; onChange: () => void }) {
  if (p.stare === 'draft') return null
  const voturi = p.voturi ?? 0
  const prag = p.prag_voturi ?? 3
  const pct = Math.min(100, Math.round((100 * voturi) / Math.max(prag, 1)))
  return (
    <Card className="print:border-0 print:shadow-none">
      <CardContent className="space-y-3">
        <p className="flex items-center gap-2 font-semibold">
          <Users className="size-4 text-primary" /> Susținere din comunitate
        </p>
        <p className="text-2xl font-semibold tabular-nums">
          {voturi} <span className="text-sm font-normal text-muted-foreground">/ {prag} susținători pentru a ajunge la Primărie</span>
        </p>
        <span className="block h-2 w-full overflow-hidden rounded-full bg-muted">
          <span className="block h-full bg-primary transition-all" style={{ width: `${pct}%` }} />
        </span>
        <VotButon p={p} onDone={onChange} />
      </CardContent>
    </Card>
  )
}

type Me = (typeof DEMO_USERS)[number]

/** The single action the current user may take now. The server enforces roles and states (403/409/422). */
function Actions({ p, me, onChange }: { p: ProiectDetaliu; me: Me; onChange: () => void }) {
  const isAuthor = p.autor_id === me.id
  if (isAuthor && p.stare === 'draft') return <Publica p={p} onDone={onChange} />
  if (isAuthor && p.stare === 'clarificari') return <Trimite p={p} onDone={onChange} />
  if (me.rol === 'primarie' && p.stare === 'trimis') return <Inainteaza p={p} onDone={onChange} />
  if (me.rol === 'verificator' && p.verificator_id === me.id && p.stare === 'in_verificare') return <Decizie p={p} onDone={onChange} />
  return null
}

function ActionCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="border-primary/30 bg-accent/30 print:hidden">
      <CardContent className="space-y-3">
        <p className="font-semibold">{title}</p>
        {children}
      </CardContent>
    </Card>
  )
}

function useAction(onDone: () => void) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  async function run(path: string, body: unknown, ok: string) {
    setBusy(true)
    setError(null)
    try {
      await api<Proiect>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
      toast.success(ok)
      onDone()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return { busy, error, run }
}

function Publica({ p, onDone }: { p: ProiectDetaliu; onDone: () => void }) {
  const { busy, error, run } = useAction(onDone)
  const [mesaj, setMesaj] = useState('')
  return (
    <ActionCard title="Publică proiectul pentru vot">
      <p className="text-sm text-muted-foreground">
        Vecinii îl văd în „Comunitate” și îl pot susține. La {p.prag_voturi ?? 3} susținători ajunge automat la Primărie.
      </p>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button disabled={busy} onClick={() => run(`/proiecte/${p.id}/publica`, undefined, 'Proiectul a fost publicat')}>
        {busy ? <Loader2 className="animate-spin" /> : <Megaphone />} Publică pentru vot
      </Button>
      <details className="text-sm">
        <summary className="cursor-pointer text-muted-foreground">Sau trimite direct la Primărie, fără vot</summary>
        <div className="mt-2 space-y-2">
          <Textarea value={mesaj} onChange={(e) => setMesaj(e.target.value)} rows={2} placeholder="Mesaj pentru Primărie (opțional)" />
          <Button variant="outline" disabled={busy} onClick={() => run(`/proiecte/${p.id}/trimite`, { mesaj: mesaj.trim() || null }, 'Propunerea a fost trimisă')}>
            <Send /> Trimite direct
          </Button>
        </div>
      </details>
    </ActionCard>
  )
}

function Trimite({ p, onDone }: { p: ProiectDetaliu; onDone: () => void }) {
  const [mesaj, setMesaj] = useState('')
  const { busy, error, run } = useAction(onDone)
  return (
    <ActionCard title="Primăria a cerut clarificări">
      <Textarea value={mesaj} onChange={(e) => setMesaj(e.target.value)} rows={3} placeholder="Răspunsul tău la clarificările cerute" />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button disabled={busy || !mesaj.trim()} onClick={() => run(`/proiecte/${p.id}/trimite`, { mesaj: mesaj.trim() || null }, 'Propunerea a fost retrimisă')}>
        {busy ? <Loader2 className="animate-spin" /> : <Send />} Retrimite
      </Button>
    </ActionCard>
  )
}

function Inainteaza({ p, onDone }: { p: ProiectDetaliu; onDone: () => void }) {
  const verificatori = DEMO_USERS.filter((u) => u.rol === 'verificator')
  const [ver, setVer] = useState(verificatori[0]?.id ?? '')
  const { busy, error, run } = useAction(onDone)
  return (
    <ActionCard title="Înaintează la verificator">
      <Select value={ver} onValueChange={setVer}>
        <SelectTrigger className="w-full sm:w-80">
          <SelectValue placeholder="Alege verificatorul" />
        </SelectTrigger>
        <SelectContent>
          {verificatori.map((u) => (
            <SelectItem key={u.id} value={u.id}>
              {u.nume}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button disabled={busy || !ver} onClick={() => run(`/proiecte/${p.id}/inainteaza`, { verificator_id: ver }, 'Proiectul a fost înaintat')}>
        {busy ? <Loader2 className="animate-spin" /> : <Send />} Înaintează
      </Button>
    </ActionCard>
  )
}

const DECIZII = [
  { stare: 'acord_de_principiu', label: 'Acord de principiu', needsMsg: false },
  { stare: 'clarificari', label: 'Cere clarificări', needsMsg: true },
  { stare: 'respins', label: 'Respinge', needsMsg: true },
] as const

function Decizie({ p, onDone }: { p: ProiectDetaliu; onDone: () => void }) {
  const [stare, setStare] = useState<(typeof DECIZII)[number]['stare']>('acord_de_principiu')
  const [mesaj, setMesaj] = useState('')
  const { busy, error, run } = useAction(onDone)
  const needsMsg = DECIZII.find((d) => d.stare === stare)!.needsMsg
  return (
    <ActionCard title="Decizia ta">
      <div className="flex flex-wrap gap-2">
        {DECIZII.map((d) => (
          <button
            key={d.stare}
            type="button"
            onClick={() => setStare(d.stare)}
            className={cn(
              'rounded-full border px-3 py-1 text-sm transition-colors',
              stare === d.stare ? 'border-primary bg-primary text-primary-foreground' : 'bg-card hover:bg-muted',
            )}
          >
            {d.label}
          </button>
        ))}
      </div>
      <Textarea value={mesaj} onChange={(e) => setMesaj(e.target.value)} rows={3} placeholder={needsMsg ? 'Motivul (obligatoriu)' : 'Mesaj (opțional)'} />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button disabled={busy || (needsMsg && !mesaj.trim())} onClick={() => run(`/proiecte/${p.id}/decizie`, { stare, mesaj: mesaj.trim() || null }, 'Decizia a fost înregistrată')}>
        {busy ? <Loader2 className="animate-spin" /> : <Send />} Trimite decizia
      </Button>
    </ActionCard>
  )
}
