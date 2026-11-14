// PROVISIONAL types, copied from P3's example payloads (backend/seed/data/examples on branch p3).
// docs/CONTRACT.md is still TBD. Once P1 publishes docs/openapi.json, replace these with
// the generated types in ./schema.d.ts (`npm run gen:types`) and fix whatever tsc reports.

export type IdeaStatus = 'deschisa' | 'prag_atins' | 'rezervata'
export type BookingStatus = 'ceruta' | 'aprobata' | 'refuzata'
export type NotificationKind = 'prag_atins' | 'cerere_rezervare' | 'rezervare_aprobata' | 'rezervare_refuzata'

export type User = {
  id: string
  name: string
  role: 'locuitor' | 'proprietar'
  neighborhood: string
  is_demo: boolean
}

export type Dossier = {
  title: string
  summary: string
  category: string
  audience: string
  expected_participants: number
  duration_hours: number
  needs: string[]
  setting: string
  tags: string[]
  source: string
}

export type Idea = {
  id: string
  author_id: string
  created_at: string
  text: string
  title: string
  dossier: Dossier
  is_demo: boolean
  interest_count: number
  status: IdeaStatus
}

export type Match = {
  space_id: string
  space_name: string
  score: number
  reason: string
  distance_km: number
  neighborhood: string
  missing_needs: string[]
}

export type Space = {
  id: string
  name: string
  kind: string
  kind_label: string
  lat: number
  lon: number
  address: string | null
  neighborhood: string
  capacity: number
  amenities: string[]
  setting: string
  owner_id: string
  source: string
  is_demo: boolean
}

export type Slot = {
  id: string
  space_id: string
  starts_at: string
  ends_at: string
  is_demo: boolean
  is_free: boolean
}

export type Booking = {
  id: string
  idea_id: string
  space_id: string
  slot_id: string
  requester_id: string
  status: BookingStatus
  created_at: string
  decided_at: string | null
  is_demo: boolean
}

export type Notification = {
  id: string
  user_id: string
  idea_id: string | null
  booking_id: string | null
  kind: NotificationKind
  created_at: string
  text: string
  read: boolean
  is_demo: boolean
}

export type Impact = {
  idei_realizate: number
  spatii_activate: number
  rezervari_aprobate: number
  ore_folosite: number
  participanti: number
  km_economisiti: number
  km_economisiti_estimare: boolean
  ipoteze: { km_per_participant: number; metoda: string }
  pe_cartiere: Record<string, number>
  pe_tip_spatiu: Record<string, number>
  pe_saptamani: { saptamana: string; rezervari: number; ore: number; participanti: number }[]
}
