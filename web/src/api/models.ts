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
export type FisierProiect = 'dosar.pdf' | 'plan.dxf' | 'materiale.csv' | 'plan.svg'

/** POST /proiecte (tip_amenajare is free text) and POST /spaces (mark a plot). */
export type ProiectNou = S['ProiectDirectCreate']
export type TerenNou = S['TerenCreate']
