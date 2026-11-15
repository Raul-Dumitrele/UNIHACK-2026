// Short names for the types generated from docs/openapi.json (`npm run gen:types` -> ./schema.d.ts).
// Never edit schema.d.ts by hand; if the contract changes, regenerate and fix what tsc reports.
import type { components } from './schema'

type S = components['schemas']

export type User = S['UserOut']
export type Space = S['SpaceOut']
export type Notification = S['NotificationOut']
export type Impact = S['Impact']

// "Propunere către Primărie"
export type Proiect = S['ProiectOut']
export type ProiectDetaliu = S['ProiectDetaliuOut']
export type ProiectEveniment = S['ProiectEvenimentOut']
export type Etapa = S['Etapa']
export type Referinta = S['Referinta']
export type Cost = S['Cost']
export type Dosar = S['Dosar']

export type UserRole = User['rol']
export type ProiectStare = Proiect['stare']
export type TipAmenajare = Proiect['tip_amenajare']

// ---- Plot choice, plan, materials (P3's work, served by P1) ----
export type TerenPotrivit = S['PlotCandidateOut']
export type PlanSchematic = S['PlanOut']
export type ElementOmis = S['Omis']
export type ListaMateriale = S['ListaMateriale']
export type LinieMaterial = S['LinieMaterial']
export type PretUnitar = S['PretUnitar']
export type FisierProiect = 'dosar.pdf' | 'plansa.pdf' | 'plan.dxf' | 'materiale.xlsx' | 'materiale.csv' | 'plan.svg'
export type Analiza = S['AnalizaOut']
export type AnalizaCerere = S['AnalizaIn']
export type Vot = S['VotOut']

// The specification and the feasibility analysis travel as JSON objects in the contract (dict); these mirror
// backend/ai/proiect/spec/model.py and backend/ai/proiect/fezabilitate.py.
export interface Componenta {
  nume: string
  categorie: string
  cantitate: number
  unitate: string
  latime_m?: number | null
  lungime_m?: number | null
  inaltime_m?: number | null
  rol?: string
  obligatoriu?: boolean
  utilitati?: string[]
  articol?: string | null
}
export interface Specificatie {
  tip_amenajare: string
  eticheta: string
  suprafata_minima_mp: number
  suprafata_recomandata_mp?: number | null
  utilitati_necesare?: string[]
  componente: Componenta[]
  beneficii?: string[]
  riscuri_specifice?: string[]
  ipoteze?: string[]
  surse?: string[]
  sursa_specificatie?: 'model_verificat' | 'llm' | 'generic'
  disclaimer?: string
}
export interface Fezabilitate {
  nivel: 'ok' | 'atentie' | 'nerealist'
  scor: number
  rezumat: string
  motive: string[]
  recomandari: string[]
  beneficii: string[]
  utilitati: { nume: string; stare: string; detaliu?: string }[]
  suprafata_mp?: number | null
  suprafata_minima_mp: number
  suprafata_recomandata_mp?: number | null
  disclaimer?: string
}
export interface Act {
  ordine: number
  nume: string
  emitent: string
  descriere: string
  temei: string
  conditie?: string
  de_confirmat?: boolean
}
export interface CerereTip {
  titlu: string
  catre: string
  text: string
}
export const CAPITOLE_MEMORIU: [string, string][] = [
  ['date_generale', '1. Date generale'],
  ['situatia_existenta', '2. Situația existentă'],
  ['solutia_propusa', '3. Soluția propusă'],
  ['specificatii_tehnice', '4. Specificații tehnice'],
  ['utilitati_energie', '5. Utilități și energie'],
  ['accesibilitate', '6. Accesibilitate și siguranță'],
  ['intretinere', '7. Întreținere și exploatare'],
  ['impact_comunitate', '8. Impact asupra comunității'],
  ['documente_necesare', '9. Documente și avize necesare'],
]

/** POST /proiecte (tip_amenajare is free text) and POST /spaces (mark a plot). */
export type ProiectNou = S['ProiectDirectCreate']
export type TerenNou = S['TerenCreate']
