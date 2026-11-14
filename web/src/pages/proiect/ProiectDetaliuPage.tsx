// One complete project. Tab "Dosar": summary, plot, cost, stages, risks, questions for the city hall, references;
// tab "Documente": plan, downloads, materials. Beside them: history and the one action the current role may take.
// Printable (Save as PDF) via the print: utilities and @media print in index.css.
import { useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Loader2, Printer, Send } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import type { Proiect, ProiectDetaliu, Space } from '@/api/models'
import { DemoBadge } from '@/components/DemoBadge'
import { DocumenteTab } from '@/components/proiect/Documente'
import {
  BulletList, CostBlock, Disclaimer, EtapeList, EvenimenteTimeline, ProiectStatusBadge, ReferinteList, Rezumat,
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

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link to="/proiecte" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" /> Proiecte
        </Link>
        <Button variant="outline" size="sm" onClick={() => window.print()}>
          <Printer /> Tipărește / salvează PDF
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
        <Tabs defaultValue="dosar" className="min-w-0">
          <TabsList className="print:hidden">
            <TabsTrigger value="dosar">Dosar</TabsTrigger>
            <TabsTrigger value="documente">Documente</TabsTrigger>
          </TabsList>
          <TabsContent value="dosar" className="mt-4 space-y-6">
            <Block title="1. Rezumat">
              <Rezumat dosar={dosar} />
            </Block>
            {teren ? (
              <Block title="2. Terenul">
                <TerenMap terenuri={[teren]} center={[teren.lat, teren.lng]} zoom={16} compact className="h-56 w-full print:hidden" />
                <p className="text-sm text-muted-foreground">
                  {teren.nume} · {teren.suprafata_mp ? `${teren.suprafata_mp} mp · ` : ''}
                  {teren.lat.toFixed(5)}, {teren.lng.toFixed(5)}
                </p>
              </Block>
            ) : null}
            <Block title="3. Cost estimat">
              <CostBlock cost={p.cost} />
              <Disclaimer />
            </Block>
            {dosar.etape.length ? (
              <Block title="4. Etape">
                <EtapeList etape={dosar.etape} />
              </Block>
            ) : null}
            {dosar.riscuri.length ? (
              <Block title="5. Riscuri">
                <BulletList items={dosar.riscuri} />
              </Block>
            ) : null}
            {dosar.lista_verificare.length ? (
              <Block title="6. Întrebări pentru Primărie">
                <BulletList items={dosar.lista_verificare} />
              </Block>
            ) : null}
            <Block title="7. Proiecte de referință">
              <ReferinteList referinte={p.referinte} />
            </Block>
          </TabsContent>
          <TabsContent value="documente" className="mt-4">
            <DocumenteTab proiectId={p.id} />
          </TabsContent>
        </Tabs>
        <aside className="space-y-6 print:mt-6">
          {me ? <Actions p={p} me={me} onChange={pr.reload} /> : null}
          <Card className="print:border-0 print:shadow-none">
            <CardHeader>
              <CardTitle>8. Istoric</CardTitle>
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

type Me = (typeof DEMO_USERS)[number]

/** The single action the current user may take now. The server enforces roles and states (403/409/422). */
function Actions({ p, me, onChange }: { p: ProiectDetaliu; me: Me; onChange: () => void }) {
  const isAuthor = p.autor_id === me.id
  if (isAuthor && (p.stare === 'draft' || p.stare === 'clarificari')) return <Trimite p={p} onDone={onChange} />
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
      await api<Proiect>(path, { method: 'POST', body: JSON.stringify(body) })
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

function Trimite({ p, onDone }: { p: ProiectDetaliu; onDone: () => void }) {
  const again = p.stare === 'clarificari'
  const [mesaj, setMesaj] = useState('')
  const { busy, error, run } = useAction(onDone)
  return (
    <ActionCard title={again ? 'Primăria a cerut clarificări' : 'Trimite propunerea la Primărie'}>
      <Textarea
        value={mesaj}
        onChange={(e) => setMesaj(e.target.value)}
        rows={3}
        placeholder={again ? 'Răspunsul tău la clarificările cerute' : 'Mesaj pentru Primărie (opțional)'}
      />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button
        disabled={busy || (again && !mesaj.trim())}
        onClick={() => run(`/proiecte/${p.id}/trimite`, { mesaj: mesaj.trim() || null }, again ? 'Propunerea a fost retrimisă' : 'Propunerea a fost trimisă')}
      >
        {busy ? <Loader2 className="animate-spin" /> : <Send />} {again ? 'Retrimite' : 'Trimite la Primărie'}
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
      <Textarea
        value={mesaj}
        onChange={(e) => setMesaj(e.target.value)}
        rows={3}
        placeholder={needsMsg ? 'Motivul (obligatoriu)' : 'Mesaj (opțional)'}
      />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button
        disabled={busy || (needsMsg && !mesaj.trim())}
        onClick={() => run(`/proiecte/${p.id}/decizie`, { stare, mesaj: mesaj.trim() || null }, 'Decizia a fost înregistrată')}
      >
        {busy ? <Loader2 className="animate-spin" /> : <Send />} Trimite decizia
      </Button>
    </ActionCard>
  )
}
