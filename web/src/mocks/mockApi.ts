// In-memory fake of the backend, built on P3's example payloads (./data, copied from branch p3).
// Framework-agnostic: web wraps it in MSW (./browser.ts); mobile calls it from its api client.
// mobile/src/mocks is a COPY of this folder: edit here, then run `npm run sync:mocks` in mobile/.
//
// Endpoints marked PROVISIONAL are not in docs/CONTRACT.md yet; ask P1 to confirm them.

import type { Booking, Idea, Impact, Match, Notification, Slot, Space, User } from '../api/types'
import bookingsData from './data/bookings.json'
import ideasData from './data/ideas.json'
import impactData from './data/impact.json'
import matchesData from './data/matches.json'
import notificationsData from './data/notifications.json'
import slotsData from './data/slots_sample.json'
import spacesData from './data/spaces_sample.json'
import usersData from './data/users.json'

export type MockResult = { status: number; body: unknown }

const INTEREST_THRESHOLD = 3 // from P3's demo scenario ("a atins pragul: 3 persoane interesate")

const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x))
const db = {
  users: clone(usersData) as User[],
  ideas: clone(ideasData) as Idea[],
  matches: clone(matchesData) as Record<string, Match[]>,
  spaces: clone(spacesData) as Space[],
  slots: clone(slotsData) as Slot[],
  bookings: clone(bookingsData) as Booking[],
  notifications: clone(notificationsData) as Notification[],
  impact: clone(impactData) as Impact,
  interests: new Set<string>(), // `${ideaId}:${userId}`
}

let seq = 1
const newId = (prefix: string) => `mock-${prefix}-${seq++}`
const now = () => new Date().toISOString()
const ok = (body: unknown, status = 200): MockResult => ({ status, body })
const fail = (status: number, detail: string): MockResult => ({ status, body: { detail } })

function notify(n: Omit<Notification, 'id' | 'created_at' | 'read' | 'is_demo'>) {
  db.notifications.unshift({ ...n, id: newId('notif'), created_at: now(), read: false, is_demo: false })
}

type Body = Record<string, unknown> | undefined

/** Returns null when the route is unknown, so the caller can fall through to the real API. */
export function handleMock(method: string, path: string, body: Body, userId: string): MockResult | null {
  const url = new URL(path, 'http://mock')
  const p = url.pathname.replace(/\/+$/, '') || '/'
  const m = method.toUpperCase()
  let r: RegExpMatchArray | null

  if (m === 'GET' && p === '/health') return ok({ status: 'ok' })

  // PROVISIONAL: GET /users
  if (m === 'GET' && p === '/users') return ok(db.users)

  // PROVISIONAL: GET /ideas, GET /ideas/{id}
  if (m === 'GET' && p === '/ideas') return ok(db.ideas)
  if (m === 'GET' && (r = p.match(/^\/ideas\/([^/]+)$/))) {
    const idea = db.ideas.find((i) => i.id === r![1])
    return idea ? ok(idea) : fail(404, 'Ideea nu există.')
  }

  // POST /ideas  (contract: calls ai.structure_idea; here a trivial stand-in dossier)
  if (m === 'POST' && p === '/ideas') {
    const text = String(body?.text ?? '').trim()
    if (text.length < 10) return fail(422, 'Descrie ideea în cel puțin 10 caractere.')
    const title = text.split(/[.!?\n]/)[0].slice(0, 70)
    const idea: Idea = {
      id: newId('idea'),
      author_id: userId,
      created_at: now(),
      text,
      title,
      dossier: {
        title,
        summary: text,
        category: 'altele',
        audience: 'vecinii din cartier',
        expected_participants: 10,
        duration_hours: 2,
        needs: [],
        setting: 'oricare',
        tags: [],
        source: 'mock',
      },
      is_demo: false,
      interest_count: 0,
      status: 'deschisa',
    }
    db.ideas.unshift(idea)
    db.matches[idea.id] = db.matches['demo-idea-1'] ?? []
    return ok(idea, 201)
  }

  // GET /ideas/{id}/matches
  if (m === 'GET' && (r = p.match(/^\/ideas\/([^/]+)\/matches$/))) {
    if (!db.ideas.some((i) => i.id === r![1])) return fail(404, 'Ideea nu există.')
    return ok(db.matches[r[1]] ?? [])
  }

  // POST /ideas/{id}/interest  (one per user; reaching the threshold sets prag_atins)
  if (m === 'POST' && (r = p.match(/^\/ideas\/([^/]+)\/interest$/))) {
    const idea = db.ideas.find((i) => i.id === r![1])
    if (!idea) return fail(404, 'Ideea nu există.')
    const key = `${idea.id}:${userId}`
    if (db.interests.has(key)) return fail(409, 'Ți-ai exprimat deja interesul pentru această idee.')
    db.interests.add(key)
    idea.interest_count += 1
    if (idea.status === 'deschisa' && idea.interest_count >= INTEREST_THRESHOLD) {
      idea.status = 'prag_atins'
      notify({
        user_id: idea.author_id,
        idea_id: idea.id,
        booking_id: null,
        kind: 'prag_atins',
        text: `Ideea „${idea.title}” a atins pragul: ${idea.interest_count} persoane interesate.`,
      })
    }
    return ok(idea)
  }

  // PROVISIONAL: GET /spaces, GET /spaces/{id}/slots
  if (m === 'GET' && p === '/spaces') return ok(db.spaces)
  if (m === 'GET' && (r = p.match(/^\/spaces\/([^/]+)\/slots$/))) {
    return ok(db.slots.filter((s) => s.space_id === r![1] && s.is_free))
  }

  // PROVISIONAL: GET /bookings
  if (m === 'GET' && p === '/bookings') return ok(db.bookings)

  // POST /bookings  { idea_id, space_id, slot_id }
  if (m === 'POST' && p === '/bookings') {
    const { idea_id, space_id, slot_id } = (body ?? {}) as Record<string, string>
    if (!idea_id || !space_id || !slot_id) return fail(422, 'Lipsesc idea_id, space_id sau slot_id.')
    const slot = db.slots.find((s) => s.id === slot_id)
    if (slot && !slot.is_free) return fail(409, 'Intervalul a fost deja rezervat.')
    const booking: Booking = {
      id: newId('booking'),
      idea_id,
      space_id,
      slot_id,
      requester_id: userId,
      status: 'ceruta',
      created_at: now(),
      decided_at: null,
      is_demo: false,
    }
    db.bookings.unshift(booking)
    const owner = db.spaces.find((s) => s.id === space_id)?.owner_id
    if (owner) {
      notify({ user_id: owner, idea_id, booking_id: booking.id, kind: 'cerere_rezervare', text: 'Ai o cerere nouă de rezervare.' })
    }
    return ok(booking, 201)
  }

  // PATCH /bookings/{id}  { status: 'aprobata' | 'refuzata' }  (only the space owner)
  if (m === 'PATCH' && (r = p.match(/^\/bookings\/([^/]+)$/))) {
    const booking = db.bookings.find((b) => b.id === r![1])
    if (!booking) return fail(404, 'Rezervarea nu există.')
    const space = db.spaces.find((s) => s.id === booking.space_id)
    if (space && space.owner_id !== userId) return fail(403, 'Doar proprietarul spațiului poate decide.')
    const status = body?.status
    if (status !== 'aprobata' && status !== 'refuzata') return fail(422, 'Status invalid.')
    booking.status = status
    booking.decided_at = now()
    if (status === 'aprobata') {
      const slot = db.slots.find((s) => s.id === booking.slot_id)
      if (slot) slot.is_free = false
      const idea = db.ideas.find((i) => i.id === booking.idea_id)
      if (idea) idea.status = 'rezervata'
    }
    notify({
      user_id: booking.requester_id,
      idea_id: booking.idea_id,
      booking_id: booking.id,
      kind: status === 'aprobata' ? 'rezervare_aprobata' : 'rezervare_refuzata',
      text: status === 'aprobata' ? 'Rezervarea ta a fost aprobată.' : 'Rezervarea ta a fost refuzată.',
    })
    return ok(booking)
  }

  // PROVISIONAL: GET /notifications  (for the current X-User-Id)
  if (m === 'GET' && p === '/notifications') return ok(db.notifications.filter((n) => n.user_id === userId))

  // GET /impact
  if (m === 'GET' && p === '/impact') return ok(db.impact)

  return null
}
