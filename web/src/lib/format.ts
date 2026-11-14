// Romanian labels for contract enums and small display helpers. No business logic here.
import type { ProiectStare, UserRole } from '@/api/models'

export const ROL: Record<UserRole, string> = { cetatean: 'cetățean', proprietar: 'proprietar', primarie: 'Primărie', verificator: 'verificator' }

const dateFmt = new Intl.DateTimeFormat('ro-RO', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
export const fmtDate = (iso: string) => dateFmt.format(new Date(iso))

export function timeAgo(iso: string): string {
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (min < 1) return 'acum'
  if (min < 60) return `acum ${min} min`
  const h = Math.round(min / 60)
  if (h < 24) return `acum ${h} h`
  const d = Math.round(h / 24)
  return d < 30 ? `acum ${d} ${d === 1 ? 'zi' : 'zile'}` : fmtDate(iso)
}

// Space.tip is free text: the seed writes "teren liber", the contract says teren_liber. Match any spelling.
export const isFreePlot = (tip: string) => tip.trim().toLowerCase().replace(/[\s_-]+/g, '_') === 'teren_liber'

// ---- "Propunere către Primărie" ----

export const TIP_AMENAJARE: Record<string, string> = {
  skatepark: 'Skatepark',
  loc_de_joaca: 'Loc de joacă',
  parc_caini: 'Parc pentru câini',
  pista_biciclete: 'Pistă de biciclete',
  gradina_comunitara: 'Grădină comunitară',
  teren_sport: 'Teren de sport',
}
/** Unknown values (tip_amenajare may become free text) are shown as they are. */
export const tipLabel = (tip: string) => TIP_AMENAJARE[tip] ?? tip.replace(/_/g, ' ')

export const PROIECT_STARE: Record<ProiectStare, string> = {
  draft: 'Ciornă',
  trimis: 'Trimis la Primărie',
  in_verificare: 'În verificare',
  clarificari: 'Clarificări cerute',
  acord_de_principiu: 'Acord de principiu',
  respins: 'Respins',
}

const lei = new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 0 })
export const fmtLei = (n: number) => `${lei.format(n)} lei`

export const DISCLAIMER =
  'Estimare orientativă, bazată pe proiecte de referință. Nu reprezintă o autorizație; acordul din aplicație este un acord de principiu simulat.'
