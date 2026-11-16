// Building blocks for "Propunere către Primărie". Everything shown comes from the API: no cost or text is
// computed here (contract rule 10 + P3's notes).
import { useState } from 'react'
import { ExternalLink, Info, Loader2, ThumbsUp } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import type { Cost, Dosar, Etapa, Proiect, ProiectDetaliu, ProiectEveniment, ProiectStare, Referinta, Vot } from '@/api/models'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DEMO_USERS } from '@/demoUsers'
import { DISCLAIMER, fmtDate, fmtLei, PROIECT_STARE, tipLabel } from '@/lib/format'
import { cn } from '@/lib/utils'

const STARE_STYLE: Record<ProiectStare, string> = {
  draft: 'border-border bg-muted text-muted-foreground',
  publicat: 'border-primary/40 bg-primary/10 text-primary',
  trimis: 'border-primary/30 bg-accent text-accent-foreground',
  in_verificare: 'border-demo/30 bg-demo-soft text-demo',
  clarificari: 'border-demo/40 bg-demo-soft text-demo',
  acord_de_principiu: 'border-success/30 bg-success/10 text-success',
  respins: 'border-destructive/30 bg-destructive/10 text-destructive',
}

export function ProiectStatusBadge({ stare }: { stare: ProiectStare }) {
  return (
    <Badge variant="outline" className={cn(STARE_STYLE[stare])}>
      {PROIECT_STARE[stare] ?? stare}
    </Badge>
  )
}

/** The mandatory text (contract rule 10). Always shown next to the dossier and the cost. */
export function Disclaimer({ className = '' }: { className?: string }) {
  return (
    <p className={cn('flex gap-2 rounded-lg border border-demo/30 bg-demo-soft p-3 text-sm text-demo', className)}>
      <Info className="mt-0.5 size-4 shrink-0" />
      {DISCLAIMER}
    </p>
  )
}

const SURSA_PRET: Record<string, string> = { seap: 'achiziții publice (SEAP)', plafon: 'plafon de program oficial', catalog: 'preț de catalog verificat' }

/**
 * The headline is the reference interval, or the plain statement that the total cannot be estimated (cost.titlu).
 * The sum of the priced lines is partial by construction: it sits in a secondary block, under its own label
 * (cost.eticheta_suma), with the lines that still have no price. It is never the headline and never called the cost.
 */
export function CostBlock({ cost }: { cost: Cost }) {
  const sum = cost.suma_cotata_lei
  const titlu = cost.titlu || (cost.suficient ? 'Cost estimat din proiecte de referință' : 'Cost total: nu poate fi estimat din datele disponibile')
  return (
    <div className="space-y-4">
      <div className="space-y-3 rounded-xl border p-4">
        <p className="text-lg font-semibold">{titlu}</p>
        {cost.suficient ? (
          <div className="grid gap-3 sm:grid-cols-3">
            <Figure label="Minim" value={cost.min_lei} />
            <Figure label="Mediană" value={cost.mediana_lei} strong />
            <Figure label="Maxim" value={cost.max_lei} />
          </div>
        ) : cost.motiv ? (
          <p className="text-sm text-muted-foreground">{cost.motiv}</p>
        ) : null}
        {cost.ipoteze.length ? (
          <details className="text-sm text-muted-foreground">
            <summary className="cursor-pointer font-medium text-foreground">Cum am calculat</summary>
            <ul className="mt-2 list-disc space-y-0.5 pl-5">
              {cost.ipoteze.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </details>
        ) : null}
      </div>
      {sum != null && cost.articole_cotate ? (
        <div className="space-y-2 rounded-xl border border-dashed p-4 text-sm" data-testid="suma-partiala">
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Informație parțială</p>
          <p className="flex flex-wrap items-baseline justify-between gap-2">
            <span className="font-medium">{cost.eticheta_suma}</span>
            <span className="tabular-nums">{fmtLei(sum)}</span>
          </p>
          {cost.nota_suma ? <p className="font-medium text-destructive">{cost.nota_suma}</p> : null}
          {cost.articole_necotate?.length ? (
            <div className="space-y-1">
              <p className="text-muted-foreground">Încă de cotat (fără sursă de preț):</p>
              <ul className="flex flex-wrap gap-1.5">
                {cost.articole_necotate.map((x) => (
                  <li key={x} className="rounded-full border px-2 py-0.5 text-xs">
                    {x}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {cost.pe_surse && Object.keys(cost.pe_surse).length ? (
            <p className="text-xs text-muted-foreground">
              Prețuri din: {Object.entries(cost.pe_surse).map(([k, v]) => `${SURSA_PRET[k] ?? k} – ${v} ${v === 1 ? 'articol' : 'articole'}`).join('; ')}.
            </p>
          ) : null}
        </div>
      ) : sum != null && cost.articole_necotate?.length ? (
        <p className="rounded-xl border border-dashed p-4 text-sm text-muted-foreground">Niciun articol din lista de materiale nu are încă o sursă de preț.</p>
      ) : null}
    </div>
  )
}

/** One vote per user per project; the server answers 409 on a second vote and sends the project on at the threshold. */
export function VotButon({ p, onDone }: { p: Proiect | ProiectDetaliu; onDone: () => void }) {
  const [busy, setBusy] = useState(false)
  const voted = 'votat_de_mine' in p ? Boolean(p.votat_de_mine) : false
  const open = p.stare === 'publicat' || p.stare === 'trimis' || p.stare === 'in_verificare' || p.stare === 'clarificari'
  if (!open) return null
  async function vote() {
    setBusy(true)
    try {
      const r = await api<Vot>(`/proiecte/${p.id}/vot`, { method: 'POST' })
      toast.success(r.stare === 'trimis' && p.stare === 'publicat' ? 'Pragul a fost atins: proiectul a plecat la Primărie' : 'Votul tău a fost înregistrat')
      onDone()
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Button size="sm" variant={voted ? 'outline' : 'default'} disabled={busy || voted} onClick={vote} className="print:hidden">
      {busy ? <Loader2 className="animate-spin" /> : <ThumbsUp />} {voted ? 'Ai susținut' : 'Susțin proiectul'}
    </Button>
  )
}

function Figure({ label, value, strong = false }: { label: string; value?: number | null; strong?: boolean }) {
  return (
    <div className={cn('rounded-lg p-3', strong ? 'bg-accent' : 'bg-muted/60')}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn('font-semibold tabular-nums', strong ? 'text-xl text-accent-foreground' : 'text-lg')}>
        {value != null ? fmtLei(value) : '–'}
      </p>
    </div>
  )
}

export function ReferinteList({ referinte }: { referinte: Referinta[] }) {
  if (!referinte.length) return <p className="text-sm text-muted-foreground">Nu am găsit proiecte de referință pentru acest tip.</p>
  return (
    <ul className="divide-y rounded-xl border">
      {referinte.map((r) => (
        <li key={r.id} className="flex flex-wrap items-start justify-between gap-3 p-3 text-sm">
          <div className="min-w-0 space-y-0.5">
            <a href={r.sursa_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium hover:text-primary hover:underline">
              {tipLabel(r.tip_amenajare)} · {r.oras}, {r.an} <ExternalLink className="size-3.5 print:hidden" />
            </a>
            <p className="text-xs text-muted-foreground">
              Sursă: {r.sursa_tip} · accesată {r.data_accesarii}
              <span className="hidden print:inline"> · {r.sursa_url}</span>
            </p>
          </div>
          <div className="text-right text-xs text-muted-foreground tabular-nums">
            {r.cost_total_lei != null ? <p className="font-medium text-foreground">{fmtLei(r.cost_total_lei)}</p> : null}
            {r.suprafata_mp != null ? <p>{r.suprafata_mp} mp</p> : null}
          </div>
        </li>
      ))}
    </ul>
  )
}

export function Rezumat({ dosar }: { dosar: Dosar }) {
  return (
    <div className="space-y-4 text-sm leading-relaxed">
      <div className="space-y-1.5">
        <h3 className="font-semibold">Descriere</h3>
        <Paragraphs text={dosar.descriere} />
      </div>
      <div className="space-y-1.5">
        <h3 className="font-semibold">Justificare</h3>
        <Paragraphs text={dosar.justificare} />
      </div>
      {dosar.componente.length ? (
        <div className="space-y-1.5">
          <h3 className="font-semibold">Componente</h3>
          <ul className="list-disc space-y-0.5 pl-5">
            {dosar.componente.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

export function EtapeList({ etape }: { etape: Etapa[] }) {
  return (
    <ol className="space-y-1 text-sm">
      {etape.map((e, i) => (
        <li key={e.nume} className="flex justify-between gap-3 rounded-lg bg-muted/50 px-3 py-2">
          <span>
            {i + 1}. {e.nume}
          </span>
          <span className="shrink-0 text-muted-foreground tabular-nums">
            {e.durata_luni} {e.durata_luni === 1 ? 'lună' : 'luni'}
          </span>
        </li>
      ))}
    </ol>
  )
}

export function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-0.5 pl-5 text-sm">
      {items.map((x) => (
        <li key={x}>{x}</li>
      ))}
    </ul>
  )
}

function Paragraphs({ text }: { text: string }) {
  return (
    <>
      {text.split(/\n{2,}/).map((p) => (
        <p key={p} className="mb-2 last:mb-0">
          {p}
        </p>
      ))}
    </>
  )
}

export function EvenimenteTimeline({ evenimente }: { evenimente: ProiectEveniment[] }) {
  const list = [...evenimente].sort((a, b) => a.created_at.localeCompare(b.created_at))
  return (
    <ol className="space-y-3">
      {list.map((ev) => {
        const who = DEMO_USERS.find((u) => u.id === ev.user_id)
        return (
          <li key={ev.id} className="relative flex gap-3 pl-1">
            <span className="mt-1.5 size-2.5 shrink-0 rounded-full bg-primary" />
            <div className="min-w-0 space-y-0.5">
              <p className="text-sm">
                <span className="font-medium">{PROIECT_STARE[ev.stare_noua] ?? ev.stare_noua}</span>
                <span className="text-muted-foreground"> · {who?.nume ?? ev.user_id} · {fmtDate(ev.created_at)}</span>
              </p>
              {ev.mesaj ? <p className="text-sm text-muted-foreground">„{ev.mesaj}”</p> : null}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
