// In-memory fake of P1's backend, following the rules in docs/CONTRACT.md, over a snapshot of the REAL API
// (P1's backend + P3's seed): ./data, regenerate with web/scripts/dump_api_mocks.py.
// Framework-agnostic: web wraps it in MSW (./browser.ts); mobile calls it from its api client.
// mobile/src/mocks is a COPY of this folder: edit here, then run `npm run sync:mocks` in mobile/.
//
// Endpoints marked PROVISIONAL are not in docs/CONTRACT.md; ask P1 before relying on them.
// POST /ideas and /owner-message return canned text: the real ones come from P3's AI.
// POST /ideas/{id}/proiect is NOT mocked (references, cost and dossier must come from the API, never the client).

import type {
  Booking, Idea, Impact, Match, Notification, ProiectDetaliu, ProiectEveniment, ProiectStare, Slot, Space, User,
} from '../api/models'
import bookingsData from './data/bookings.json'
import ideasData from './data/ideas.json'
import impactData from './data/impact.json'
import interestsData from './data/interests.json'
import matchesData from './data/matches.json'
import notificationsData from './data/notifications.json'
import proiecteData from './data/proiecte.json'
import spacesData from './data/spaces.json'
import usersData from './data/users.json'

export type MockResult = { status: number; body: unknown }
type Body = Record<string, unknown> | undefined

const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x))
const db = {
  users: clone(usersData) as User[],
  spaces: clone(spacesData) as Space[],
  ideas: clone(ideasData) as Idea[],
  matches: clone(matchesData) as Record<string, Match[]>,
  bookings: clone(bookingsData) as Booking[],
  notifications: clone(notificationsData) as Notification[],
  impact: clone(impactData) as Impact,
  proiecte: clone(proiecteData) as ProiectDetaliu[],
  interests: new Set((interestsData as { user_id: string; idea_id: string }[]).map((i) => `${i.idea_id}:${i.user_id}`)),
}

const uuid = () =>
  globalThis.crypto?.randomUUID?.() ?? `mock-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
const now = () => new Date().toISOString()
const ok = (body: unknown, status = 200): MockResult => ({ status, body })
const fail = (status: number, detail: string): MockResult => ({ status, body: { detail } })

const inside = (inner: Slot, outer: Slot) =>
  inner.zi === outer.zi && inner.de_la >= outer.de_la && inner.pana_la <= outer.pana_la && inner.de_la < inner.pana_la
const overlaps = (a: Slot, b: Slot) => a.zi === b.zi && a.de_la < b.pana_la && b.de_la < a.pana_la

/** Remove `taken` from the space's free slots, splitting the slot that contains it (contract rule 4). */
function takeSlot(space: Space, taken: Slot) {
  space.sloturi = space.sloturi.flatMap((s) => {
    if (!inside(taken, s)) return [s]
    const rest: Slot[] = []
    if (s.de_la < taken.de_la) rest.push({ zi: s.zi, de_la: s.de_la, pana_la: taken.de_la })
    if (taken.pana_la < s.pana_la) rest.push({ zi: s.zi, de_la: taken.pana_la, pana_la: s.pana_la })
    return rest
  })
}

function notify(user_id: string, idea_id: string, mesaj: string, booking_id: string | null = null, proiect_id: string | null = null) {
  db.notifications.unshift({ id: uuid(), user_id, idea_id, booking_id, proiect_id, mesaj, citita: false, created_at: now() })
}

const withoutEvents = ({ evenimente: _ev, ...p }: ProiectDetaliu) => p
const ofRole = (rol: User['rol']) => db.users.filter((u) => u.rol === rol)

/** Rule 9 (visibility): author, primarie when not draft, the assigned verifier. */
function canSee(p: ProiectDetaliu, me: User) {
  return p.autor_id === me.id || (me.rol === 'primarie' && p.stare !== 'draft') || p.verificator_id === me.id
}

function transition(p: ProiectDetaliu, me: User, stare: ProiectStare, mesaj: string | null) {
  const ev: ProiectEveniment = { id: uuid(), proiect_id: p.id, user_id: me.id, stare_noua: stare, mesaj, created_at: now() }
  p.stare = stare
  p.updated_at = ev.created_at
  p.evenimente.push(ev)
}

const ZI: Record<Slot['zi'], string> = {
  luni: 'luni', marti: 'marți', miercuri: 'miercuri', joi: 'joi', vineri: 'vineri', sambata: 'sâmbătă', duminica: 'duminică',
}
const fmtSlot = (s: Slot) => `${ZI[s.zi]} ${s.de_la}–${s.pana_la}`

/** Returns null when the route is unknown, so the caller can fall through to the real API. */
export function handleMock(method: string, path: string, body: Body, userId: string): MockResult | null {
  const url = new URL(path, 'http://mock')
  const p = url.pathname.replace(/\/+$/, '') || '/'
  const m = method.toUpperCase()
  const me = db.users.find((u) => u.id === userId)
  const needUser = () => (me ? null : fail(401, 'Utilizator necunoscut.'))
  let r: RegExpMatchArray | null

  if (m === 'GET' && p === '/health') return ok({ status: 'ok' })
  if (m === 'GET' && p === '/users') return ok(db.users)

  // GET /spaces?categorie=&dotari=&dotari=&capacitate_min=
  if (m === 'GET' && p === '/spaces') {
    const cap = Number(url.searchParams.get('capacitate_min') ?? 0)
    const need = url.searchParams.getAll('dotari')
    return ok(db.spaces.filter((s) => s.capacitate >= cap && need.every((d) => (s.dotari as string[]).includes(d))))
  }

  // POST /ideas {descriere, titlu?, prag?}  (rule 1; structurat is canned here, real one comes from ai.structure_idea)
  if (m === 'POST' && p === '/ideas') {
    if (!me) return needUser()
    const descriere = String(body?.descriere ?? '').trim()
    if (descriere.length < 3) return fail(422, 'Descrierea trebuie să aibă cel puțin 3 caractere.')
    const rezumat = descriere.split(/[.!?\n]/)[0].trim().slice(0, 80)
    const idea: Idea = {
      id: uuid(),
      author_id: me.id,
      titlu: String(body?.titlu ?? '').trim() || rezumat,
      descriere,
      structurat: { categorie: 'altele', persoane: 10, dotari: [], program: [], zgomot: 'mediu', rezumat },
      prag: Number(body?.prag) || 5,
      interesati: 0,
      stare: 'deschisa',
      is_demo: false,
      created_at: now(),
    }
    db.ideas.unshift(idea)
    db.matches[idea.id] = (db.matches['demo-idea-7'] ?? []).map((x) => ({ ...x, suprapunere: [] }))
    return ok(idea, 201)
  }

  if (m === 'GET' && p === '/ideas') return ok(db.ideas)
  if (m === 'GET' && (r = p.match(/^\/ideas\/([^/]+)$/))) {
    const idea = db.ideas.find((i) => i.id === r![1])
    return idea ? ok(idea) : fail(404, 'Ideea nu există.')
  }

  if (m === 'GET' && (r = p.match(/^\/ideas\/([^/]+)\/matches$/))) {
    if (!db.ideas.some((i) => i.id === r![1])) return fail(404, 'Ideea nu există.')
    const fresh = (db.matches[r[1]] ?? []).map((x) => ({ ...x, space: db.spaces.find((s) => s.id === x.space.id) ?? x.space }))
    return ok([...fresh].sort((a, b) => b.scor - a.scor))
  }

  // POST /ideas/{id}/interest  (rule 2)
  if (m === 'POST' && (r = p.match(/^\/ideas\/([^/]+)\/interest$/))) {
    if (!me) return needUser()
    const idea = db.ideas.find((i) => i.id === r![1])
    if (!idea) return fail(404, 'Ideea nu există.')
    const key = `${idea.id}:${me.id}`
    if (db.interests.has(key)) return fail(409, 'Ți-ai exprimat deja interesul pentru această idee.')
    db.interests.add(key)
    idea.interesati += 1
    if (idea.stare === 'deschisa' && idea.interesati >= idea.prag) {
      idea.stare = 'prag_atins'
      notify(idea.author_id, idea.id, `Ideea „${idea.titlu}” a atins pragul: ${idea.interesati} persoane interesate.`)
    }
    return ok(idea, 201)
  }

  // POST /ideas/{id}/owner-message {space_id, slot} -> {mesaj}  (canned; real text from ai.owner_message)
  if (m === 'POST' && (r = p.match(/^\/ideas\/([^/]+)\/owner-message$/))) {
    if (!me) return needUser()
    const idea = db.ideas.find((i) => i.id === r![1])
    const space = db.spaces.find((s) => s.id === body?.space_id)
    if (!idea || !space) return fail(404, 'Ideea sau spațiul nu există.')
    const slot = body?.slot as Slot
    return ok({
      mesaj:
        `Bună ziua! Suntem un grup de ${idea.interesati} vecini și am vrea să organizăm „${idea.titlu}” ` +
        `la ${space.nume}, ${slot ? fmtSlot(slot) : 'într-un interval liber'}, pentru aproximativ ` +
        `${idea.structurat.persoane} persoane. Vă mulțumim!`,
    })
  }

  // GET /bookings: requests for my ideas + requests for spaces I own, newest first
  if (m === 'GET' && p === '/bookings') {
    if (!me) return needUser()
    const mine = new Set(db.spaces.filter((s) => s.owner_id === me.id).map((s) => s.id))
    const myIdeas = new Set(db.ideas.filter((i) => i.author_id === me.id).map((i) => i.id))
    return ok(
      db.bookings
        .filter((b) => mine.has(b.space_id) || myIdeas.has(b.idea_id))
        .sort((a, b) => b.created_at.localeCompare(a.created_at)),
    )
  }

  // POST /bookings {idea_id, space_id, slot}  (rule 3)
  if (m === 'POST' && p === '/bookings') {
    if (!me) return needUser()
    const idea = db.ideas.find((i) => i.id === body?.idea_id)
    const space = db.spaces.find((s) => s.id === body?.space_id)
    const slot = body?.slot as Slot | undefined
    if (!idea || !space) return fail(404, 'Ideea sau spațiul nu există.')
    if (!slot?.zi || !slot.de_la || !slot.pana_la) return fail(422, 'Alege un interval.')
    if (idea.author_id !== me.id) return fail(403, 'Doar autorul ideii poate cere o rezervare.')
    if (idea.stare !== 'prag_atins') return fail(409, 'Ideea trebuie să fi atins pragul de interes.')
    if (!space.sloturi.some((s) => inside(slot, s))) return fail(409, 'Intervalul nu mai este liber.')
    const mesaj = typeof body?.mesaj === 'string' && body.mesaj.trim() ? body.mesaj.trim() : null
    const booking: Booking = { id: uuid(), idea_id: idea.id, space_id: space.id, slot, stare: 'cerut', created_at: now(), mesaj }
    db.bookings.unshift(booking)
    notify(space.owner_id, idea.id, `Cerere nouă de rezervare la ${space.nume} (${fmtSlot(slot)}) pentru „${idea.titlu}”.`, booking.id)
    return ok(booking, 201)
  }

  // PATCH /bookings/{id} {stare: aprobat|refuzat}  (rule 4)
  if (m === 'PATCH' && (r = p.match(/^\/bookings\/([^/]+)$/))) {
    if (!me) return needUser()
    const booking = db.bookings.find((b) => b.id === r![1])
    if (!booking) return fail(404, 'Rezervarea nu există.')
    const space = db.spaces.find((s) => s.id === booking.space_id)
    const idea = db.ideas.find((i) => i.id === booking.idea_id)
    if (!space || space.owner_id !== me.id) return fail(403, 'Doar proprietarul spațiului poate decide.')
    if (booking.stare !== 'cerut') return fail(409, 'Cererea a fost deja decisă.')
    const stare = body?.stare
    if (stare !== 'aprobat' && stare !== 'refuzat') return fail(422, 'Stare invalidă.')
    booking.stare = stare
    if (stare === 'aprobat') {
      if (idea) idea.stare = 'rezervata'
      takeSlot(space, booking.slot)
      for (const other of db.bookings) {
        if (other !== booking && other.space_id === space.id && other.stare === 'cerut' && overlaps(other.slot, booking.slot)) {
          other.stare = 'refuzat'
          const oi = db.ideas.find((i) => i.id === other.idea_id)
          if (oi) notify(oi.author_id, oi.id, `Cererea pentru ${space.nume} a fost refuzată: intervalul a fost ocupat.`, other.id)
        }
      }
    }
    if (idea) {
      notify(
        idea.author_id,
        idea.id,
        stare === 'aprobat'
          ? `Rezervarea la ${space.nume} (${fmtSlot(booking.slot)}) a fost aprobată.`
          : `Rezervarea la ${space.nume} (${fmtSlot(booking.slot)}) a fost refuzată.`,
        booking.id,
      )
    }
    return ok(booking)
  }

  if (m === 'GET' && p === '/notifications') {
    if (!me) return needUser()
    return ok(db.notifications.filter((n) => n.user_id === me.id))
  }
  if (m === 'PATCH' && (r = p.match(/^\/notifications\/([^/]+)\/read$/))) {
    if (!me) return needUser()
    const n = db.notifications.find((x) => x.id === r![1])
    if (!n) return fail(404, 'Notificarea nu există.')
    if (n.user_id !== me.id) return fail(403, 'Nu este notificarea ta.')
    n.citita = true
    return ok(n)
  }

  if (m === 'GET' && p === '/impact') return ok(db.impact)

  // ---- "Propunere către Primărie" (rules 6-9) ----
  if (m === 'POST' && (r = p.match(/^\/ideas\/([^/]+)\/proiect$/))) {
    return fail(503, 'Generarea dosarului (referințe, cost, text) se face doar de API-ul real. Pornește backend-ul și setează VITE_USE_MOCKS=false.')
  }

  // GET /proiecte (rule 7)
  if (m === 'GET' && p === '/proiecte') {
    if (!me) return needUser()
    const list = db.proiecte.filter((x) =>
      me.rol === 'primarie' ? x.stare !== 'draft' : me.rol === 'verificator' ? x.verificator_id === me.id : x.autor_id === me.id,
    )
    return ok(list.map(withoutEvents))
  }

  if (m === 'GET' && (r = p.match(/^\/proiecte\/([^/]+)$/))) {
    if (!me) return needUser()
    const pr = db.proiecte.find((x) => x.id === r![1])
    if (!pr) return fail(404, 'Proiectul nu există.')
    if (!canSee(pr, me)) return fail(403, 'Nu ai acces la acest proiect.')
    return ok(pr)
  }

  // POST /proiecte/{id}/trimite {mesaj?}: author, draft|clarificari -> trimis, notify every primarie
  if (m === 'POST' && (r = p.match(/^\/proiecte\/([^/]+)\/trimite$/))) {
    if (!me) return needUser()
    const pr = db.proiecte.find((x) => x.id === r![1])
    if (!pr) return fail(404, 'Proiectul nu există.')
    if (pr.autor_id !== me.id) return fail(403, 'Doar autorul poate trimite proiectul.')
    if (pr.stare !== 'draft' && pr.stare !== 'clarificari') return fail(409, 'Proiectul nu poate fi trimis în starea curentă.')
    transition(pr, me, 'trimis', typeof body?.mesaj === 'string' ? body.mesaj : null)
    for (const u of ofRole('primarie')) notify(u.id, pr.idea_id, `Proiect nou trimis: „${pr.dosar.titlu}”.`, null, pr.id)
    return ok(withoutEvents(pr))
  }

  // POST /proiecte/{id}/inainteaza {verificator_id}: primarie, trimis -> in_verificare, notify verifier
  if (m === 'POST' && (r = p.match(/^\/proiecte\/([^/]+)\/inainteaza$/))) {
    if (!me) return needUser()
    const pr = db.proiecte.find((x) => x.id === r![1])
    if (!pr) return fail(404, 'Proiectul nu există.')
    if (me.rol !== 'primarie') return fail(403, 'Doar Primăria poate înainta proiectul.')
    if (pr.stare !== 'trimis') return fail(409, 'Proiectul nu poate fi înaintat în starea curentă.')
    const ver = db.users.find((x) => x.id === body?.verificator_id && x.rol === 'verificator')
    if (!ver) return fail(422, 'Alege un verificator valid.')
    pr.verificator_id = ver.id
    transition(pr, me, 'in_verificare', null)
    notify(ver.id, pr.idea_id, `Ți-a fost desemnat spre verificare proiectul „${pr.dosar.titlu}”.`, null, pr.id)
    return ok(withoutEvents(pr))
  }

  // POST /proiecte/{id}/decizie {stare, mesaj}: assigned verifier, in_verificare -> acord|respins|clarificari
  if (m === 'POST' && (r = p.match(/^\/proiecte\/([^/]+)\/decizie$/))) {
    if (!me) return needUser()
    const pr = db.proiecte.find((x) => x.id === r![1])
    if (!pr) return fail(404, 'Proiectul nu există.')
    if (pr.verificator_id !== me.id) return fail(403, 'Doar verificatorul desemnat poate decide.')
    if (pr.stare !== 'in_verificare') return fail(409, 'Proiectul nu este în verificare.')
    const stare = body?.stare
    if (stare !== 'acord_de_principiu' && stare !== 'respins' && stare !== 'clarificari') return fail(422, 'Decizie invalidă.')
    const mesaj = typeof body?.mesaj === 'string' ? body.mesaj.trim() : ''
    if ((stare === 'respins' || stare === 'clarificari') && !mesaj) return fail(422, 'Mesajul este obligatoriu pentru această decizie.')
    transition(pr, me, stare, mesaj || null)
    const text =
      stare === 'acord_de_principiu'
        ? `Proiectul „${pr.dosar.titlu}” a primit acord de principiu.`
        : stare === 'respins'
          ? `Proiectul „${pr.dosar.titlu}” a fost respins. ${mesaj}`
          : `Pentru proiectul „${pr.dosar.titlu}” se cer clarificări: ${mesaj}`
    for (const id of [pr.autor_id, ...ofRole('primarie').map((x) => x.id)]) notify(id, pr.idea_id, text, null, pr.id)
    return ok(withoutEvents(pr))
  }

  return null
}
