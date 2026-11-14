// "Documente" tab: schematic plan, downloads and the materials list. Everything comes from the API (P3's
// plan and materials, served by P1): quantities, prices, the subtotal and the texts are shown as received.
import { useState } from 'react'
import { Download, FileSpreadsheet, FileText, Loader2, Ruler } from 'lucide-react'
import { toast } from 'sonner'
import { apiBlob, ApiError, saveBlob } from '@/api/client'
import type { FisierProiect, LinieMaterial, ListaMateriale, PlanSchematic } from '@/api/models'
import { Disclaimer } from '@/components/proiect/parts'
import { ErrorState, LoadingCards } from '@/components/StateViews'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fmtLei } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { useBlobUrl } from '@/lib/useBlobUrl'

const SEAP_TEXT = 'Prețuri observate în achiziții directe SEAP, date deschise data.gov.ro (CC BY 4.0)'
const TVA_TEXT = 'TVA: neprecizat în setul de date'

const nf = new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 2 })

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
          ) : svg.error ? (
            <ErrorState message={reason(svg.errorStatus, svg.error)} />
          ) : svg.loading || !svg.url ? (
            <LoadingCards count={1} />
          ) : (
            <img src={svg.url} alt="Plan schematic de amplasament" className="mx-auto w-full max-w-xl rounded-xl border bg-white" />
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

const DOWNLOADS: { file: FisierProiect; label: string; hint: string; icon: typeof FileText; name: string }[] = [
  { file: 'dosar.pdf', label: 'Dosar PDF', hint: 'dosarul complet', icon: FileText, name: 'dosar.pdf' },
  { file: 'plan.dxf', label: 'Plan DXF', hint: 'pentru proiectant', icon: Ruler, name: 'plan.dxf' },
  { file: 'materiale.csv', label: 'Listă materiale CSV', hint: 'se deschide în Excel', icon: FileSpreadsheet, name: 'materiale.csv' },
]

function Downloads({ base }: { base: string }) {
  const [busy, setBusy] = useState<FisierProiect | null>(null)

  async function download(file: FisierProiect, name: string) {
    setBusy(file)
    try {
      saveBlob(await apiBlob(`${base}/documente/${file}`), name)
    } catch (e) {
      const status = e instanceof ApiError ? e.status : null
      toast.error(reason(status, (e as Error).message))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex flex-wrap gap-2 print:hidden">
      {DOWNLOADS.map(({ file, label, hint, icon: Icon, name }) => (
        <Button key={file} variant="outline" disabled={busy !== null} onClick={() => download(file, name)} title={hint}>
          {busy === file ? <Loader2 className="animate-spin" /> : <Icon />} {label} <Download className="size-3.5 opacity-60" />
        </Button>
      ))}
    </div>
  )
}

function PlanNotes({ plan }: { plan: PlanSchematic }) {
  return (
    <div className="space-y-3 text-sm">
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
  return (
    <Card className="break-inside-avoid">
      <CardHeader>
        <CardTitle>Lista de materiale</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <LoadingCards count={2} />
        ) : error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : lista ? (
          <>
            <div className="overflow-x-auto rounded-xl border">
              <table className="w-full min-w-[640px] text-sm">
                <thead className="bg-muted/60 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Articol</th>
                    <th className="px-3 py-2 font-medium">Cantitate</th>
                    <th className="px-3 py-2 font-medium">Preț unitar (median)</th>
                    <th className="px-3 py-2 text-right font-medium">Valoare</th>
                  </tr>
                </thead>
                <tbody className="divide-y align-top">
                  {lista.linii.map((l) => (
                    <Linie key={`${l.articol}-${l.nume}`} l={l} />
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-sm font-medium">
              {lista.eticheta_subtotal}
              {priced ? <span className="tabular-nums">: {fmtLei(lista.subtotal_cotat_lei)}</span> : null}
            </p>
            {lista.ipoteze.length ? (
              <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted-foreground">
                {lista.ipoteze.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            ) : null}
            <p className="text-xs text-muted-foreground">
              {SEAP_TEXT}. {TVA_TEXT}.
            </p>
            <p className="rounded-lg border border-demo/30 bg-demo-soft p-3 text-sm text-demo">{lista.disclaimer}</p>
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}

function Linie({ l }: { l: LinieMaterial }) {
  const cotat = l.stare === 'cotat' && l.pret_unitar
  return (
    <tr>
      <td className="px-3 py-2">
        <span className="font-medium">{l.nume}</span>
        {!cotat ? (
          <Badge variant="outline" className="ml-2 border-demo/40 bg-demo-soft text-demo">
            de cotat
          </Badge>
        ) : null}
        {!cotat && l.motiv ? <span className="block text-xs text-muted-foreground">{l.motiv}</span> : null}
      </td>
      <td className="px-3 py-2">
        <span className="whitespace-nowrap tabular-nums">
          {nf.format(l.cantitate)} {l.unitate}
        </span>
        <span className="block text-xs text-muted-foreground">{l.ipoteza}</span>
      </td>
      <td className="px-3 py-2">
        {cotat && l.pret_unitar ? (
          <>
            <span className="whitespace-nowrap tabular-nums">
              {fmtLei(l.pret_unitar.mediana_lei)} / {l.pret_unitar.unitate}
            </span>
            <span className="block text-xs text-muted-foreground tabular-nums">
              {fmtLei(l.pret_unitar.min_lei)}–{fmtLei(l.pret_unitar.max_lei)} · {l.pret_unitar.observatii} observații · {l.pret_unitar.perioada}
            </span>
            {l.pret_unitar.surse.length ? <span className="block text-xs text-muted-foreground">Surse (DA SEAP): {l.pret_unitar.surse.join(', ')}</span> : null}
          </>
        ) : (
          <span className="text-muted-foreground">–</span>
        )}
      </td>
      <td className="px-3 py-2 text-right whitespace-nowrap tabular-nums">{cotat && l.valoare_lei != null ? fmtLei(l.valoare_lei) : '–'}</td>
    </tr>
  )
}
