// "Documente" tab: schematic plan (2D and 3D), downloads (A3 sheets, DXF, dossier PDF, XLSX/CSV) and the bill of
// quantities grouped by chapter, each line with its price source. Everything comes from the API: quantities,
// prices, the subtotal and the texts are shown as received; nothing is computed here.
import { useState } from 'react'
import { Box, Download, FileSpreadsheet, FileText, Loader2, Ruler } from 'lucide-react'
import { toast } from 'sonner'
import { apiBlob, ApiError, saveBlob } from '@/api/client'
import type { FisierProiect, LinieMaterial, ListaMateriale, PlanSchematic } from '@/api/models'
import { Disclaimer } from '@/components/proiect/parts'
import { Randare3D } from '@/components/proiect/Randare3D'
import { ErrorState, LoadingCards } from '@/components/StateViews'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { fmtLei } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { useBlobUrl } from '@/lib/useBlobUrl'
import { cn } from '@/lib/utils'

const nf = new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 2 })
const SURSA_STYLE: Record<string, string> = {
  seap: 'border-success/30 bg-success/10 text-success',
  plafon: 'border-demo/40 bg-demo-soft text-demo',
  catalog: 'border-primary/30 bg-primary/10 text-primary',
}
const SURSA_LABEL: Record<string, string> = { seap: 'SEAP', plafon: 'plafon de program', catalog: 'catalog' }

/** 403 = no access to the project; a bare "Not Found" = the route is missing; otherwise the server's own `detail`. */
function reason(status: number | null, message: string): string {
  if (status === 403) return 'Nu ai acces la documentele acestui proiect.'
  if ((status === 404 || status === 405) && (message === 'Not Found' || message === 'Method Not Allowed')) return 'Documentele nu sunt încă disponibile pe server (endpoint lipsă).'
  return message
}

export function DocumenteTab({ proiectId }: { proiectId: string }) {
  const base = `/proiecte/${proiectId}`
  const plan = useApi<PlanSchematic>(`${base}/plan`)
  const materiale = useApi<ListaMateriale>(`${base}/materiale`)
  const svg = useBlobUrl(`${base}/documente/plan.svg`)

  return (
    <div className="space-y-6">
      <Downloads base={base} />
      <Card className="break-inside-avoid">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Ruler className="size-5" /> Plan schematic
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {plan.error ? (
            <ErrorState message={reason(plan.errorStatus, plan.error)} onRetry={plan.reload} />
          ) : (
            <Tabs defaultValue="2d">
              <TabsList className="print:hidden">
                <TabsTrigger value="2d">Plan 2D</TabsTrigger>
                <TabsTrigger value="3d">
                  <Box className="size-4" /> Vedere 3D
                </TabsTrigger>
              </TabsList>
              <TabsContent value="2d" className="mt-3">
                {svg.error ? (
                  <ErrorState message={reason(svg.errorStatus, svg.error)} />
                ) : svg.loading || !svg.url ? (
                  <LoadingCards count={1} />
                ) : (
                  <img src={svg.url} alt="Plan schematic de amplasament" className="mx-auto w-full max-w-xl rounded-xl border bg-white" />
                )}
              </TabsContent>
              <TabsContent value="3d" className="mt-3 print:hidden">
                {plan.data ? <Randare3D plan={plan.data} /> : <LoadingCards count={1} />}
              </TabsContent>
            </Tabs>
          )}
          {plan.data ? <PlanNotes plan={plan.data} /> : null}
        </CardContent>
      </Card>
      <Materiale
        lista={materiale.data}
        loading={materiale.loading && !materiale.data}
        error={materiale.error ? reason(materiale.errorStatus, materiale.error) : null}
        reload={materiale.reload}
      />
      <Disclaimer />
    </div>
  )
}

const DOWNLOADS: { file: FisierProiect; label: string; hint: string; icon: typeof FileText }[] = [
  { file: 'dosar.pdf', label: 'Dosar PDF', hint: 'memoriu, specificație, cost, documente necesare, plan și materiale', icon: FileText },
  { file: 'plansa.pdf', label: 'Planșe A3 (PDF)', hint: 'plan de situație și planșă de detaliu, cu cartuș, scară, nord, legendă și bilanț teritorial', icon: Ruler },
  { file: 'plan.dxf', label: 'Plan DXF', hint: 'se deschide în AutoCAD; pentru proiectant', icon: Ruler },
  { file: 'materiale.xlsx', label: 'Listă materiale XLSX', hint: 'Excel cu capitole, formule și surse', icon: FileSpreadsheet },
  { file: 'materiale.csv', label: 'CSV', hint: 'format simplu, compatibil', icon: FileSpreadsheet },
]

function Downloads({ base }: { base: string }) {
  const [busy, setBusy] = useState<FisierProiect | null>(null)

  async function download(file: FisierProiect) {
    setBusy(file)
    try {
      saveBlob(await apiBlob(`${base}/documente/${file}`), file)
    } catch (e) {
      const status = e instanceof ApiError ? e.status : null
      toast.error(reason(status, (e as Error).message))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex flex-wrap gap-2 print:hidden">
      {DOWNLOADS.map(({ file, label, hint, icon: Icon }) => (
        <Button key={file} variant="outline" disabled={busy !== null} onClick={() => download(file)} title={hint}>
          {busy === file ? <Loader2 className="animate-spin" /> : <Icon />} {label} <Download className="size-3.5 opacity-60" />
        </Button>
      ))}
    </div>
  )
}

function PlanNotes({ plan }: { plan: PlanSchematic }) {
  const bilant = plan.bilant ?? []
  return (
    <div className="space-y-3 text-sm">
      {bilant.length ? (
        <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr>
                <th className="py-1 font-medium">Bilanț teritorial (orientativ)</th>
                <th className="py-1 text-right font-medium">mp</th>
                <th className="py-1 text-right font-medium">%</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {bilant.map((b) => (
                <tr key={String(b.zona)} className={cn(String(b.zona).startsWith('Total') && 'font-medium')}>
                  <td className="py-1">{String(b.zona)}</td>
                  <td className="py-1 text-right tabular-nums">{nf.format(Number(b.mp))}</td>
                  <td className="py-1 text-right tabular-nums">{nf.format(Number(b.procent))}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="space-y-1 rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground sm:w-44">
            <p>
              <span className="font-medium text-foreground">POT propus</span> ≈ {nf.format(plan.pot_procent ?? 0)} %
            </p>
            <p>
              <span className="font-medium text-foreground">CUT propus</span> ≈ {nf.format(plan.cut ?? 0)}
            </p>
            <p>Valori orientative; cele reglementate sunt în PUG/PUZ și în certificatul de urbanism.</p>
          </div>
        </div>
      ) : null}
      {plan.omise.length ? (
        <div className="space-y-1">
          <p className="font-medium">Nu încape pe teren</p>
          <ul className="list-disc space-y-0.5 pl-5 text-muted-foreground">
            {plan.omise.map((o) => (
              <li key={o.nume}>
                {o.nume}
                {o.bucati > 1 ? ` (${o.bucati} buc.)` : ''}
                {o.obligatoriu ? ' · obligatoriu' : ''}: {o.motiv}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="rounded-lg border border-demo/30 bg-demo-soft p-3 text-demo">{plan.disclaimer}</p>
    </div>
  )
}

function Materiale({
  lista, loading, error, reload,
}: { lista: ListaMateriale | null; loading: boolean; error: string | null; reload: () => void }) {
  const priced = lista?.linii.some((l) => l.stare === 'cotat') ?? false
  const capitole = lista?.capitole?.length ? lista.capitole : Array.from(new Set((lista?.linii ?? []).map((l) => l.capitol ?? 'Articole')))
  return (
    <Card className="break-inside-avoid">
      <CardHeader>
        <CardTitle>Lista de materiale (cantități și prețuri cu sursă)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <LoadingCards count={2} />
        ) : error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : lista ? (
          <>
            <div className="flex flex-wrap gap-2 text-xs">
              {Object.entries(lista.surse ?? {}).map(([k, v]) => (
                <Badge key={k} variant="outline" className={SURSA_STYLE[k]}>
                  {SURSA_LABEL[k] ?? k}: {v}
                  {lista.pe_surse?.[k] ? ` · ${lista.pe_surse[k]} articole` : ''}
                </Badge>
              ))}
              <Badge variant="outline" className="border-demo/40 bg-demo-soft text-demo">
                de cotat: fără sursă de preț verificată · {lista.linii_de_cotat} articole
              </Badge>
            </div>
            <div className="overflow-x-auto rounded-xl border">
              <table className="w-full min-w-[680px] text-sm">
                <thead className="bg-muted/60 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Articol</th>
                    <th className="px-3 py-2 font-medium">Cantitate</th>
                    <th className="px-3 py-2 font-medium">Preț unitar (median) și sursă</th>
                    <th className="px-3 py-2 text-right font-medium">Valoare</th>
                  </tr>
                </thead>
                <tbody className="divide-y align-top">
                  {capitole.map((cap) => (
                    <Capitol key={cap} nume={cap} linii={lista.linii.filter((l) => (l.capitol ?? 'Articole') === cap)} />
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-sm font-medium">
              {lista.eticheta_subtotal}
              {priced ? <span className="tabular-nums">: {fmtLei(lista.subtotal_cotat_lei)}</span> : null}
            </p>
            {lista.articole_necotate?.length ? (
              <p className="text-xs text-muted-foreground">De cotat: {lista.articole_necotate.join('; ')}.</p>
            ) : null}
            {lista.ipoteze.length ? (
              <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted-foreground">
                {lista.ipoteze.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            ) : null}
            <p className="text-xs text-muted-foreground">
              {lista.sursa_preturi}. {lista.tva}.
            </p>
            <p className="rounded-lg border border-demo/30 bg-demo-soft p-3 text-sm text-demo">{lista.disclaimer}</p>
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}

function Capitol({ nume, linii }: { nume: string; linii: LinieMaterial[] }) {
  if (!linii.length) return null
  return (
    <>
      <tr className="bg-muted/30">
        <td colSpan={4} className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {nume}
        </td>
      </tr>
      {linii.map((l) => (
        <Linie key={`${l.articol}-${l.nume}`} l={l} />
      ))}
    </>
  )
}

function Linie({ l }: { l: LinieMaterial }) {
  const p = l.stare === 'cotat' ? l.pret_unitar : null
  const tip = p?.tip_sursa ?? 'seap'
  return (
    <tr>
      <td className="px-3 py-2">
        <span className="font-medium">{l.nume}</span>
        {!p ? (
          <Badge variant="outline" className="ml-2 border-demo/40 bg-demo-soft text-demo">
            de cotat
          </Badge>
        ) : null}
        {!p && l.motiv ? <span className="block text-xs text-muted-foreground">{l.motiv}</span> : null}
      </td>
      <td className="px-3 py-2">
        <span className="whitespace-nowrap tabular-nums">
          {nf.format(l.cantitate)} {l.unitate}
        </span>
        <span className="block text-xs text-muted-foreground">{l.ipoteza}</span>
      </td>
      <td className="px-3 py-2">
        {p ? (
          <>
            <span className="whitespace-nowrap tabular-nums">
              {fmtLei(p.mediana_lei)} / {p.unitate}
            </span>
            <Badge variant="outline" className={cn('ml-2', SURSA_STYLE[tip])}>
              {SURSA_LABEL[tip] ?? tip}
            </Badge>
            <span className="block text-xs text-muted-foreground tabular-nums">
              {fmtLei(p.min_lei)}–{fmtLei(p.max_lei)} · {p.observatii} observații{p.perioada ? ` · ${p.perioada}` : ''}
            </span>
            {p.nota ? <span className="block text-xs text-muted-foreground">{p.nota}</span> : null}
            {p.sursa_url ? (
              <a href={p.sursa_url} target="_blank" rel="noreferrer" className="block truncate text-xs text-primary underline">
                sursa{p.data_accesarii ? ` (accesată ${p.data_accesarii})` : ''}
              </a>
            ) : p.surse.length ? (
              <span className="block text-xs text-muted-foreground">Surse (DA SEAP): {p.surse.join(', ')}</span>
            ) : null}
          </>
        ) : (
          <span className="text-muted-foreground">–</span>
        )}
      </td>
      <td className="px-3 py-2 text-right whitespace-nowrap tabular-nums">{p && l.valoare_lei != null ? fmtLei(l.valoare_lei) : '–'}</td>
    </tr>
  )
}
