// Blocks of the extended dossier: feasibility, technical specification, memorandum, documents and request
// templates. Everything is shown as received from the API (no figure or legal claim is produced here).
import { useState } from 'react'
import { AlertTriangle, CheckCircle2, ChevronDown, Copy, FileCheck, Info } from 'lucide-react'
import { toast } from 'sonner'
import type { Act, CerereTip, Fezabilitate, Specificatie } from '@/api/models'
import { CAPITOLE_MEMORIU } from '@/api/models'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const nf = new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 2 })

const NIVEL = {
  ok: { label: 'Propunere realistă', icon: CheckCircle2, cls: 'border-success/30 bg-success/10 text-success' },
  atentie: { label: 'Posibilă, cu aspecte de clarificat', icon: Info, cls: 'border-demo/30 bg-demo-soft text-demo' },
  nerealist: { label: 'Nerealistă pe acest teren', icon: AlertTriangle, cls: 'border-destructive/30 bg-destructive/10 text-destructive' },
} as const

export function FezabilitateCard({ fez, compact = false }: { fez: Fezabilitate; compact?: boolean }) {
  const n = NIVEL[fez.nivel] ?? NIVEL.atentie
  const Icon = n.icon
  return (
    <div className={cn('space-y-3 rounded-xl border p-4', n.cls)}>
      <div className="flex flex-wrap items-center gap-2">
        <Icon className="size-5 shrink-0" />
        <p className="font-semibold">{n.label}</p>
        <Badge variant="outline" className="ml-auto border-current/30 bg-background/60 text-current">
          scor orientativ {fez.scor}/100
        </Badge>
      </div>
      <p className="text-sm">{fez.rezumat}</p>
      {fez.motive.length ? (
        <ul className="list-disc space-y-0.5 pl-5 text-sm">
          {fez.motive.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      ) : null}
      {fez.recomandari.length ? (
        <div className="space-y-1 text-sm">
          <p className="font-medium">Recomandări</p>
          <ul className="list-disc space-y-0.5 pl-5">
            {fez.recomandari.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {!compact && fez.utilitati.length ? (
        <div className="flex flex-wrap gap-2 text-xs">
          {fez.utilitati.map((u) => (
            <Badge key={u.nume} variant="outline" className="border-current/30 bg-background/60 text-current" title={u.detaliu}>
              {u.nume}: {u.stare}
            </Badge>
          ))}
        </div>
      ) : null}
      {!compact && fez.beneficii.length ? (
        <div className="space-y-1 rounded-lg bg-background/60 p-3 text-sm text-foreground">
          <p className="font-medium">Ce aduce comunității</p>
          <ul className="list-disc space-y-0.5 pl-5">
            {fez.beneficii.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {!compact && fez.disclaimer ? <p className="text-xs opacity-80">{fez.disclaimer}</p> : null}
    </div>
  )
}

const CATEGORII: Record<string, string> = {
  echipament: 'Echipamente', instalatie: 'Instalații și utilități', constructie: 'Construcții', terasament: 'Terasamente și platforme',
  finisaj: 'Finisaje și suprafețe', mobilier: 'Mobilier urban', siguranta: 'Siguranță', semnalizare: 'Semnalizare', vegetatie: 'Spații verzi',
  servicii: 'Servicii și sisteme',
}
const SURSA_SPEC: Record<string, string> = {
  model_verificat: 'model tehnic verificat al aplicației',
  llm: 'propusă automat (model de limbaj), validată ca formă',
  generic: 'generică: aplicația nu are un model pentru acest tip',
}

export function SpecificatieBlock({ spec }: { spec: Specificatie }) {
  const groups = Object.keys(CATEGORII).filter((k) => spec.componente.some((c) => c.categorie === k))
  const utils = Array.from(new Set([...(spec.utilitati_necesare ?? []), ...spec.componente.flatMap((c) => c.utilitati ?? [])]))
  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap gap-2 text-xs">
        <Badge variant="outline">suprafață minimă {nf.format(spec.suprafata_minima_mp)} mp</Badge>
        {spec.suprafata_recomandata_mp ? <Badge variant="outline">recomandată {nf.format(spec.suprafata_recomandata_mp)} mp</Badge> : null}
        <Badge variant="outline">utilități: {utils.length ? utils.join(', ') : 'fără racord nou'}</Badge>
        <Badge variant="outline" className={cn(spec.sursa_specificatie !== 'model_verificat' && 'border-demo/40 bg-demo-soft text-demo')}>
          {SURSA_SPEC[spec.sursa_specificatie ?? 'model_verificat']}
        </Badge>
      </div>
      <div className="overflow-x-auto rounded-xl border">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="bg-muted/60 text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">Componentă</th>
              <th className="px-3 py-2 font-medium">Cantitate</th>
              <th className="px-3 py-2 font-medium">Dimensiuni (ipoteză)</th>
              <th className="px-3 py-2 font-medium">Rol</th>
            </tr>
          </thead>
          <tbody className="divide-y align-top">
            {groups.map((g) => (
              <GroupRows key={g} label={CATEGORII[g]} comps={spec.componente.filter((c) => c.categorie === g)} />
            ))}
          </tbody>
        </table>
      </div>
      {spec.ipoteze?.length ? (
        <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted-foreground">
          {spec.ipoteze.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      ) : null}
      {spec.disclaimer ? <p className="rounded-lg border border-demo/30 bg-demo-soft p-3 text-demo">{spec.disclaimer}</p> : null}
    </div>
  )
}

function GroupRows({ label, comps }: { label: string; comps: Specificatie['componente'] }) {
  return (
    <>
      <tr className="bg-muted/30">
        <td colSpan={4} className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </td>
      </tr>
      {comps.map((c) => (
        <tr key={c.nume}>
          <td className="px-3 py-2">
            <span className="font-medium">{c.nume}</span>
            {c.obligatoriu ? <span className="ml-2 text-xs text-primary">obligatoriu</span> : null}
            {c.utilitati?.length ? <span className="block text-xs text-muted-foreground">necesită {c.utilitati.join(', ')}</span> : null}
          </td>
          <td className="whitespace-nowrap px-3 py-2 tabular-nums">
            {nf.format(c.cantitate)} {c.unitate}
          </td>
          <td className="whitespace-nowrap px-3 py-2 tabular-nums text-muted-foreground">
            {c.latime_m && c.lungime_m ? `${nf.format(c.latime_m)} × ${nf.format(c.lungime_m)} m` : '–'}
            {c.inaltime_m ? ` · h ${nf.format(c.inaltime_m)} m` : ''}
          </td>
          <td className="px-3 py-2 text-muted-foreground">{c.rol}</td>
        </tr>
      ))}
    </>
  )
}

export function MemoriuBlock({ memoriu }: { memoriu: Record<string, string> }) {
  const [open, setOpen] = useState<string | null>(CAPITOLE_MEMORIU[0][0])
  const chapters = CAPITOLE_MEMORIU.filter(([k]) => memoriu[k])
  if (!chapters.length) return null
  return (
    <div className="divide-y rounded-xl border">
      {chapters.map(([key, label]) => {
        const isOpen = open === key
        return (
          <div key={key}>
            <button
              type="button"
              onClick={() => setOpen(isOpen ? null : key)}
              className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-semibold hover:bg-muted/50 print:hidden"
              aria-expanded={isOpen}
            >
              {label}
              <ChevronDown className={cn('size-4 shrink-0 transition-transform', isOpen && 'rotate-180')} />
            </button>
            <p className="hidden px-4 pt-3 text-sm font-semibold print:block">{label}</p>
            <div className={cn('px-4 pb-4 text-sm leading-relaxed', !isOpen && 'hidden print:block')}>
              {memoriu[key].split(/\n{2,}/).map((p) => (
                <p key={p} className="mb-2 last:mb-0">
                  {p}
                </p>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function ActeBlock({ acte, disclaimer }: { acte: Act[]; disclaimer?: string }) {
  if (!acte.length) return null
  return (
    <div className="space-y-3 text-sm">
      <ol className="space-y-2">
        {acte.map((a) => (
          <li key={a.ordine} className="flex gap-3 rounded-lg border p-3">
            <span className="grid size-7 shrink-0 place-items-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
              {a.ordine}
            </span>
            <div className="min-w-0 space-y-1">
              <p className="font-medium">
                <FileCheck className="mr-1 inline size-4 text-primary" />
                {a.nume}
              </p>
              <p className="text-xs text-muted-foreground">Emitent: {a.emitent}</p>
              <p className="text-muted-foreground">{a.descriere}</p>
              {a.conditie ? <p className="text-xs text-demo">Când: {a.conditie}</p> : null}
              <p className="text-xs text-muted-foreground">Temei: {a.temei}</p>
            </div>
          </li>
        ))}
      </ol>
      {disclaimer ? <p className="rounded-lg border border-demo/30 bg-demo-soft p-3 text-demo">{disclaimer}</p> : null}
    </div>
  )
}

export function CereriTipBlock({ cereri }: { cereri: CerereTip[] }) {
  if (!cereri.length) return null
  return (
    <div className="space-y-3">
      {cereri.map((c) => (
        <details key={c.titlu} className="rounded-xl border p-3">
          <summary className="cursor-pointer text-sm font-medium">{c.titlu}</summary>
          <p className="mt-2 text-xs text-muted-foreground">Către: {c.catre}</p>
          <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-muted/50 p-3 font-sans text-sm leading-relaxed">{c.text}</pre>
          <Button
            variant="outline"
            size="sm"
            className="mt-2 print:hidden"
            onClick={() => {
              void navigator.clipboard.writeText(`${c.titlu}\nCătre: ${c.catre}\n\n${c.text}`).then(() => toast.success('Textul a fost copiat'))
            }}
          >
            <Copy /> Copiază textul
          </Button>
        </details>
      ))}
    </div>
  )
}
