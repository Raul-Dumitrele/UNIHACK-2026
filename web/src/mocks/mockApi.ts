// In-memory fake of P1's backend, following the rules in docs/CONTRACT.md, over a snapshot of the REAL API
// (P1's backend + seed): ./data, regenerate with web/scripts/dump_api_mocks.py.
// Framework-agnostic: web wraps it in MSW (./browser.ts); mobile (paused) has a copy (`npm run sync:mocks`).
//
// A project created with POST /proiecte is cloned from a snapshot project of the same kind (the mock never writes costs,
// references or prices of its own) and shows that project's plan, materials and documents. /terenuri/potrivite
// answers from snapshots taken at a few minimum areas. POST /ideas/{id}/proiect and the old idea/booking routes
// are not mocked.

import type {
  Impact, ListaMateriale, Notification, PlanSchematic, ProiectDetaliu, ProiectEveniment, ProiectNou, ProiectStare, Space, TerenNou, TerenPotrivit, User,
} from '../api/models'
import documenteJson from './data/documente_json.json'
import impactData from './data/impact.json'
import notificationsData from './data/notifications.json'
import proiecteData from './data/proiecte.json'
import spacesData from './data/spaces.json'
import potriviteData from './data/terenuri_potrivite.json'
import usersData from './data/users.json'

/** `file`: the caller (browser.ts) serves data/documente/<key>; kept out of here so this module stays framework-agnostic. */
export type MockResult = { status: number; body: unknown; file?: { key: string; contentType: string } }
type Body = Record<string, unknown> | undefined

const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x))
const db = {
  users: clone(usersData) as User[],
  spaces: clone(spacesData) as Space[],
  notifications: clone(notificationsData) as Notification[],
  impact: clone(impactData) as Impact,
  proiecte: clone(proiecteData) as ProiectDetaliu[],
  /** project id -> the snapshot project whose plan, materials and documents it shows */
  docsFrom: new Map<string, string>(),
}

const uuid = () =>
  globalThis.crypto?.randomUUID?.() ?? `mock-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
const now = () => new Date().toISOString()
const ok = (body: unknown, status = 200): MockResult => ({ status, body })
const FILES: Record<string, string> = {
  'plan.svg': 'image/svg+xml', 'plan.dxf': 'application/dxf', 'dosar.pdf': 'application/pdf', 'materiale.csv': 'text/csv; charset=utf-8',
}
const MINIME = [100, 250, 400, 600]
const fail = (status: number, detail: string): MockResult => ({ status, body: { detail } })

function notify(user_id: string, idea_id: string, mesaj: string, proiect_id: string | null = null) {
  db.notifications.unshift({ id: uuid(), user_id, idea_id, booking_id: null, proiect_id, mesaj, citita: false, created_at: now() })
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

  // GET /spaces?tip= (the other filters of the real route are not used by the web UI)
  if (m === 'GET' && p === '/spaces') {
    const tip = url.searchParams.get('tip')
    return ok(tip ? db.spaces.filter((x) => x.tip === tip) : db.spaces)
  }

  // POST /spaces {nume, lat, lng, suprafata_mp, descriere?} -> Space teren_liber, unverified (rule 14)
  if (m === 'POST' && p === '/spaces') {
    if (!me) return needUser()
    const b = (body ?? {}) as Partial<TerenNou>
    const nume = String(b.nume ?? '').trim()
    if (nume.length < 3) return fail(422, 'Numele trebuie să aibă cel puțin 3 caractere.')
    if (typeof b.lat !== 'number' || typeof b.lng !== 'number' || b.lat < 45.6 || b.lat > 45.9 || b.lng < 21.0 || b.lng > 21.45)
      return fail(422, 'Terenul trebuie să fie în zona Timișoarei.')
    if (!Number(b.suprafata_mp) || Number(b.suprafata_mp) < 1) return fail(422, 'Suprafața trebuie să fie de cel puțin 1 mp.')
    const space: Space = {
      id: uuid(), nume, tip: 'teren_liber', lat: b.lat, lng: b.lng, capacitate: 0, dotari: [], sloturi: [], owner_id: me.id,
      is_demo: false, suprafata_mp: Math.round(Number(b.suprafata_mp)), descriere: b.descriere ?? null, sursa: 'marcat_de_utilizator',
      status_verificare: 'neverificat',
    }
    db.spaces.push(space)
    return ok(space, 201)
  }

  // GET /spaces/{id}/proiecte: public; every submitted project on the plot plus the caller's own drafts
  if (m === 'GET' && (r = p.match(/^\/spaces\/([^/]+)\/proiecte$/))) {
    if (!db.spaces.some((x) => x.id === r![1])) return fail(404, 'Spațiul nu există.')
    const list = db.proiecte.filter((x) => x.space_id === r![1] && (x.stare !== 'draft' || x.autor_id === me?.id))
    return ok(list.sort((a, b) => b.updated_at.localeCompare(a.updated_at)).map(withoutEvents))
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

  // POST /proiecte {space_id, tip_amenajare, descriere, suprafata_mp?} -> draft (201)
  if (m === 'POST' && p === '/proiecte') {
    if (!me) return needUser()
    if (me.rol !== 'cetatean') return fail(403, 'Doar cetățenii pot propune proiecte.')
    const b = (body ?? {}) as Partial<ProiectNou>
    const space = db.spaces.find((x) => x.id === b.space_id)
    if (!space) return fail(404, 'Terenul nu există.')
    if (!String(b.tip_amenajare ?? '').trim()) return fail(422, 'Alege tipul amenajării.')
    if (String(b.descriere ?? '').trim().length < 3) return fail(422, 'Descrierea trebuie să aibă cel puțin 3 caractere.')
    const mp = Number(b.suprafata_mp ?? space.suprafata_mp)
    if (!mp || mp < 1) return fail(422, 'Suprafața trebuie să fie de cel puțin 1 mp.')
    const tip = String(b.tip_amenajare).trim() as ProiectDetaliu['tip_amenajare']
    const example = db.proiecte.find((x) => x.tip_amenajare === tip && x.cost.suficient) ?? db.proiecte.find((x) => x.tip_amenajare === tip) ?? db.proiecte[0]
    const created = now()
    const pr: ProiectDetaliu = {
      ...clone(example),
      id: uuid(), space_id: space.id, autor_id: me.id, tip_amenajare: tip, suprafata_mp: Math.round(mp),
      stare: 'draft', verificator_id: null, is_demo: false, created_at: created, updated_at: created,
      evenimente: [{ id: uuid(), proiect_id: '', user_id: me.id, stare_noua: 'draft', mesaj: null, created_at: created }],
    }
    pr.evenimente[0].proiect_id = pr.id
    pr.dosar.titlu = `Amenajare: ${tip.replace(/_/g, ' ')} – ${space.nume}`
    pr.dosar.descriere = `${String(b.descriere).trim()}\n\n${pr.dosar.descriere}`
    db.docsFrom.set(pr.id, example.id)
    db.proiecte.unshift(pr)
    return ok(pr, 201)
  }

  // GET /terenuri/potrivite?tip_amenajare=&suprafata_minima=&cartier=&limit= (snapshots at a few minimum areas:
  // we take the closest one below the request and keep the plots that are big enough; `cartier` is not applied)
  if (m === 'GET' && p === '/terenuri/potrivite') {
    const tip = url.searchParams.get('tip_amenajare') ?? ''
    if (!tip) return fail(422, 'Alege tipul amenajării.')
    const tables = potriviteData as Record<string, Record<string, TerenPotrivit[]>>
    const table = tables[tip] ?? tables.foisor // any other kind: the generic plan (a snapshot of "foisor")
    const min = Number(url.searchParams.get('suprafata_minima') ?? 0)
    const limit = Number(url.searchParams.get('limit') ?? 10)
    const bucket = String([...MINIME].reverse().find((x) => x <= min) ?? MINIME[0])
    return ok(table[bucket].filter((x) => x.suprafata_mp >= min).slice(0, limit))
  }

  // GET /proiecte/{id}/plan | /materiale | /documente/{file}: same visibility as GET /proiecte/{id} (PROVISIONAL)
  if (m === 'GET' && (r = p.match(/^\/proiecte\/([^/]+)\/(plan|materiale|documente\/([a-z.]+))$/))) {
    if (!me) return needUser()
    const pr = db.proiecte.find((x) => x.id === r![1])
    if (!pr) return fail(404, 'Proiectul nu există.')
    if (!canSee(pr, me)) return fail(403, 'Nu ai acces la acest proiect.')
    const src = db.docsFrom.get(pr.id) ?? pr.id
    const docs = (documenteJson as unknown as Record<string, { plan: PlanSchematic; materiale: ListaMateriale }>)[src]
    if (r[2] === 'plan') return ok(docs.plan)
    if (r[2] === 'materiale') return ok(docs.materiale)
    const name = r[3]
    if (!(name in FILES)) return fail(404, 'Documentul nu există.')
    return { status: 200, body: null, file: { key: `${src}/${name}`, contentType: FILES[name] } }
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
    for (const u of ofRole('primarie')) notify(u.id, pr.idea_id, `Proiect nou trimis: „${pr.dosar.titlu}”.`, pr.id)
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
    notify(ver.id, pr.idea_id, `Ți-a fost desemnat spre verificare proiectul „${pr.dosar.titlu}”.`, pr.id)
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
    for (const id of [pr.autor_id, ...ofRole('primarie').map((x) => x.id)]) notify(id, pr.idea_id, text, pr.id)
    return ok(withoutEvents(pr))
  }

  return null
}
