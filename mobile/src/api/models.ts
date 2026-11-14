// Short names for the types generated from docs/openapi.json (`npm run gen:types` -> ./schema.d.ts).
// Never edit schema.d.ts by hand; if the contract changes, regenerate and fix what tsc reports.
import type { components } from './schema'

type S = components['schemas']

export type Slot = S['Slot']
export type Structurat = S['Structurat']
export type User = S['UserOut']
export type Space = S['SpaceOut']
export type Idea = S['IdeaOut']
export type IdeaCreate = S['IdeaCreate']
export type Match = S['MatchOut']
export type Booking = S['BookingOut']
export type BookingCreate = S['BookingCreate']
export type Notification = S['NotificationOut']
export type Impact = S['Impact']
export type OwnerMessage = S['OwnerMessageOut']

// "Propunere către Primărie"
export type Proiect = S['ProiectOut']
export type ProiectDetaliu = S['ProiectDetaliuOut']
export type ProiectEveniment = S['ProiectEvenimentOut']
export type ProiectCreate = S['ProiectCreate']
export type Referinta = S['Referinta']
export type Cost = S['Cost']
export type Dosar = S['Dosar']

export type UserRole = User['rol']
export type IdeaStatus = Idea['stare']
export type BookingStatus = Booking['stare']
export type ProiectStare = Proiect['stare']
export type TipAmenajare = Proiect['tip_amenajare']
export type Zi = Slot['zi']
export type Dotare = Structurat['dotari'][number]
