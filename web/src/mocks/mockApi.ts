// In-memory stand-in for the backend, used in demo mode (VITE_USE_MOCKS=true). It answers from ./data, which is
// a SNAPSHOT of the real API (web/scripts/dump_api_mocks.py), and follows the state rules of docs/CONTRACT.md.
// Framework-agnostic: web wraps it in MSW (./browser.ts).
//
// It never produces a figure, a score or a legal text of its own:
//  * analysis (specification, feasibility) and plot choice come from snapshots taken per kind and per plot;
//  * a project created here is a copy of the snapshot project of the same kind (dossier, cost, plan, materials,
//    documents), with the feasibility of the chosen plot; for a kind without a snapshot project it copies the
//    first one, so the plan may not match: this is a limit of the demo mode, not of the app;
//  * the kind typed by the user is matched to a snapshot with a short keyword list (the server has its own rules).
// The old idea and booking routes are not mocked.

import type {
  Analiza, Fezabilitate, Impact, ListaMateriale, Notification, PlanSchematic, ProiectDetaliu, ProiectEveniment, ProiectNou,
  ProiectStare, Space, Specificatie, TerenNou, TerenPotrivit, User, Vot,
} from '../api/models'
import analizaData from './data/analiza.json'
import documenteJson from './data/documente_json.json'
import impactData from './data/impact.json'
import notificationsData from './data/notifications.json'
import proiecteData from './data/proiecte.json'
import spacesData from './data/spaces.json'
import potriviteData from './data/terenuri_potrivite.json'
import usersData from './data/users.json'
import voturiData from './data/voturi.json'

/** `file`: the caller (browser.ts) serves data/documente/<key>; kept out of here so this module stays framework-agnostic. */
export type MockResult = { status: number; body: unknown; file?: { key: string; contentType: string } }
type Body = Record<string, unknown> | undefined

const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x))
const db = {
  users: clone(usersData) as User[],
  spaces: clone(spacesData) as Space[],
  notifications: clone(notificationsData) as Notification[],
  impact: clone(impactData) as Impact,
  proiecte: clone(proiecteData) as unknown as ProiectDetaliu[],
  voturi: new Set((voturiData as { proiect_id: string; user_id: string }[]).map((v) => `${v.proiect_id}:${v.user_id}`)),
  /** project id -> the snapshot project whose plan, materials and documents it shows */
  docsFrom: new Map<string, string>(),
}
const SPEC = (analizaData as unknown as { specificatie: Record<string, Specificatie> }).specificatie
const FEZ = (analizaData as unknown as { fezabilitate: Record<string, Record<string, Fezabilitate>> }).fezabilitate
const POTRIVITE = potriviteData as unknown as Record<string, Record<string, TerenPotrivit[]>>

const uuid = () =>
  globalThis.crypto?.randomUUID?.() ?? `mock-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
const now = () => new Date().toISOString()
const ok = (body: unknown, status = 200): MockResult => ({ status, body })
const fail = (status: number, detail: string): MockResult => ({ status, body: { detail } })
const FILES: Record<string, string> = {
  'plan.svg': 'image/svg+xml', 'plan.dxf': 'application/dxf', 'plansa.pdf': 'application/pdf', 'dosar.pdf': 'application/pdf',
  'materiale.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'materiale.csv': 'text/csv; charset=utf-8',
}

const plain = (t: string) => t.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, ' ').trim()
/** Keywords -> snapshot key. Only for the demo mode; the server resolves kinds with its own rules. */
const KEYWORDS: [RegExp, string][] = [
  [/skate/, 'skatepark'], [/joac/, 'loc_de_joaca'], [/caini|caine|canin/, 'parc_caini'], [/bicicl/, 'pista_biciclete'],
  [/gradin/, 'gradina_comunitara'], [/sport|baschet|fotbal|tenis/, 'teren_sport'], [/foisor/, 'foisor'],
  [/acvatic|aqua|piscin|strand/, 'aquapark'],
]
function kindKey(tip: string): string {
  const t = plain(tip)
  const direct = t.replace(/ /g, '_')
  if (SPEC[direct]) return direct
  return KEYWORDS.find(([re]) => re.test(t))?.[1] ?? '_generic'
}
/** The generic snapshot was taken for the word "altceva": put the user's own words in its place. */
function withLabel<T>(value: T, key: string, tip: string): T {
  if (key !== '_generic') return clone(value)
  const label = tip.trim().replace(/_/g, ' ')
  return JSON.parse(JSON.stringify(value).replaceAll('altceva', label.replace(/["\\]/g, '')))
}
function analysis(tip: string, spaceId: string | null): Analiza | null {
  const key = kindKey(tip)
  const fez = FEZ[key]?.[spaceId ?? '_']
  if (!fez) return null
  const spec = withLabel(SPEC[key], key, tip)
  const f = withLabel(fez, key, tip)
  f.interpretare_diferita = ![plain(spec.eticheta), plain(spec.tip_amenajare)].includes(plain(tip))
  return { tip_amenajare: spec.tip_amenajare, eticheta: spec.eticheta, specificatie: spec, fezabilitate: f, plan_complet: null, omise: [] } as unknown as Analiza
}

function notify(user_id: string, idea_id: string, mesaj: string, proiect_id: string | null = null) {
  db.notifications.unshift({ id: uuid(), user_id, idea_id, booking_id: null, proiect_id, mesaj, citita: false, created_at: now() })
}

const withoutEvents = ({ evenimente: _ev, ...p }: ProiectDetaliu) => p
const ofRole = (rol: User['rol']) => db.users.filter((u) => u.rol === rol)
/** A draft is visible only to its author; any other project is public. */
const canSee = (p: ProiectDetaliu, me: User | undefined) => p.stare !== 'draft' || p.autor_id === me?.id

function transition(p: ProiectDetaliu, me: User, stare: ProiectStare, mesaj: string | null) {
  const ev: ProiectEveniment = { id: uuid(), proiect_id: p.id, user_id: me.id, stare_noua: stare, mesaj, created_at: now() }
  p.stare = stare
  p.updated_at = ev.created_at
  p.evenimente.push(ev)
}
function sendToCityHall(p: ProiectDetaliu, me: User, mesaj: string | null) {
  transition(p, me, 'trimis', mesaj)
  for (const u of ofRole('primarie')) notify(u.id, p.idea_id, `Proiect nou trimis: „${p.dosar.titlu}”.`, p.id)
}

/** Returns null when the route is unknown, so the caller can fall through to the real API. */
export function handleMock(method: string, path: string, body: Body, userId: string): MockResult | null {
  const url = new URL(path, 'http://mock')
  const p = url.pathname.replace(/\/+$/, '') || '/'
  const m = method.toUpperCase()
  const me = db.users.find((u) => u.id === userId)
  const needUser = () => fail(401, 'Utilizator necunoscut.')
  let r: RegExpMatchArray | null

  if (m === 'GET' && p === '/health') return ok({ status: 'ok' })
  if (m === 'GET' && p === '/users') return ok(db.users)
  if (m === 'GET' && p === '/impact') return ok(db.impact)

  // GET /spaces?tip=
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
    const list = db.proiecte.filter((x) => x.space_id === r![1] && canSee(x, me))
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

  // GET /terenuri/potrivite?tip_amenajare=&suprafata_minima=&cartier=&limit= (snapshots at a few minimum areas:
  // the closest one below the request, then the plots that are big enough; `cartier` is not applied)
  if (m === 'GET' && p === '/terenuri/potrivite') {
    const tip = url.searchParams.get('tip_amenajare') ?? ''
    if (!tip) return fail(422, 'Alege tipul amenajării.')
    const table = POTRIVITE[kindKey(tip)] ?? {}
    const min = Number(url.searchParams.get('suprafata_minima') ?? 0)
    const limit = Number(url.searchParams.get('limit') ?? 10)
    const buckets = Object.keys(table).map(Number).sort((a, b) => a - b)
    const bucket = [...buckets].reverse().find((x) => x <= min) ?? buckets[0]
    return ok((table[String(bucket)] ?? []).filter((x) => x.suprafata_mp >= min).slice(0, limit))
  }

  // POST /proiecte/analiza {tip_amenajare, descriere?, suprafata_mp?, space_id?} -> specification + feasibility (rule 16)
  if (m === 'POST' && p === '/proiecte/analiza') {
    if (!me) return needUser()
    const tip = String(body?.tip_amenajare ?? '').trim()
    if (tip.length < 2) return fail(422, 'Alege tipul amenajării.')
    const spaceId = typeof body?.space_id === 'string' ? body.space_id : null
    if (spaceId && !db.spaces.some((x) => x.id === spaceId)) return fail(404, 'Spațiul nu există.')
    const a = analysis(tip, spaceId) ?? analysis(tip, null)
    return a ? ok(a) : fail(422, 'Tip de amenajare necunoscut.')
  }

  // GET /proiecte/publice: every project that is not a draft
  if (m === 'GET' && p === '/proiecte/publice') return ok(db.proiecte.filter((x) => x.stare !== 'draft').map(withoutEvents))

  // POST /proiecte {space_id, tip_amenajare, descriere, suprafata_mp?} -> draft (201)
  if (m === 'POST' && p === '/proiecte') {
    if (!me) return needUser()
    if (me.rol !== 'cetatean') return fail(403, 'Doar cetățenii pot propune proiecte.')
    const b = (body ?? {}) as Partial<ProiectNou>
    const space = db.spaces.find((x) => x.id === b.space_id)
    if (!space) return fail(404, 'Terenul nu există.')
    const tipText = String(b.tip_amenajare ?? '').trim()
    if (!tipText) return fail(422, 'Alege tipul amenajării.')
    if (String(b.descriere ?? '').trim().length < 3) return fail(422, 'Descrierea trebuie să aibă cel puțin 3 caractere.')
    const mp = Number(b.suprafata_mp ?? space.suprafata_mp)
    if (!mp || mp < 1) return fail(422, 'Suprafața trebuie să fie de cel puțin 1 mp.')
    const a = analysis(tipText, space.id) ?? analysis(tipText, null)
    const tip = (a?.tip_amenajare ?? tipText) as ProiectDetaliu['tip_amenajare']
    const example = db.proiecte.find((x) => x.tip_amenajare === tip) ?? db.proiecte[0]
    const created = now()
    const pr: ProiectDetaliu = {
      ...clone(example),
      id: uuid(), space_id: space.id, autor_id: me.id, tip_amenajare: tip, suprafata_mp: Math.round(mp),
      stare: 'draft', verificator_id: null, is_demo: false, created_at: created, updated_at: created, voturi: 0,
      evenimente: [{ id: uuid(), proiect_id: '', user_id: me.id, stare_noua: 'draft', mesaj: null, created_at: created }],
    }
    pr.evenimente[0].proiect_id = pr.id
    pr.dosar.titlu = `Amenajare: ${a?.eticheta ?? tipText} – ${space.nume}`
    pr.dosar.descriere = `${String(b.descriere).trim()}\n\n${pr.dosar.descriere}`
    if (a) Object.assign(pr, { specificatie: a.specificatie, fezabilitate: a.fezabilitate })
    db.docsFrom.set(pr.id, db.docsFrom.get(example.id) ?? example.id)
    db.proiecte.unshift(pr)
    return ok({ ...pr, votat_de_mine: false }, 201)
  }

  // GET /proiecte/{id}/plan | /materiale | /documente/{file}: same visibility as the project
  if (m === 'GET' && (r = p.match(/^\/proiecte\/([^/]+)\/(plan|materiale|documente\/([a-z.]+))$/))) {
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

  // GET /proiecte (rule 7): author -> own; primarie -> everything but drafts; verifier -> assigned
  if (m === 'GET' && p === '/proiecte') {
    if (!me) return needUser()
    const list = db.proiecte.filter((x) =>
      me.rol === 'primarie' ? x.stare !== 'draft' : me.rol === 'verificator' ? x.verificator_id === me.id : x.autor_id === me.id,
    )
    return ok(list.map(withoutEvents))
  }

  if (m === 'GET' && (r = p.match(/^\/proiecte\/([^/]+)$/))) {
    const pr = db.proiecte.find((x) => x.id === r![1])
    if (!pr) return fail(404, 'Proiectul nu există.')
    if (!canSee(pr, me)) return fail(403, 'Nu ai acces la acest proiect.')
    return ok({ ...pr, votat_de_mine: me ? db.voturi.has(`${pr.id}:${me.id}`) : false })
  }

  // POST /proiecte/{id}/publica: author, draft -> publicat (rule 17)
  if (m === 'POST' && (r = p.match(/^\/proiecte\/([^/]+)\/publica$/))) {
    if (!me) return needUser()
    const pr = db.proiecte.find((x) => x.id === r![1])
    if (!pr) return fail(404, 'Proiectul nu există.')
    if (pr.autor_id !== me.id) return fail(403, 'Doar autorul proiectului îl poate publica.')
    if (pr.stare !== 'draft') return fail(409, 'Doar o ciornă poate fi publicată.')
    transition(pr, me, 'publicat', null)
    return ok(withoutEvents(pr))
  }

  // POST /proiecte/{id}/vot: one vote per user; at the threshold the project is sent to the city hall (rule 17)
  if (m === 'POST' && (r = p.match(/^\/proiecte\/([^/]+)\/vot$/))) {
    if (!me) return needUser()
    const pr = db.proiecte.find((x) => x.id === r![1])
    if (!pr) return fail(404, 'Proiectul nu există.')
    if (pr.stare === 'draft') return fail(409, 'Proiectul nu este publicat încă.')
    if (pr.stare === 'acord_de_principiu' || pr.stare === 'respins') return fail(409, 'Proiectul are deja o decizie; votul s-a încheiat.')
    const key = `${pr.id}:${me.id}`
    if (db.voturi.has(key)) return fail(409, 'Ai votat deja acest proiect.')
    db.voturi.add(key)
    pr.voturi = (pr.voturi ?? 0) + 1
    const prag = pr.prag_voturi ?? 3
    if (pr.stare === 'publicat' && pr.voturi >= prag) {
      sendToCityHall(pr, me, `Pragul de ${prag} susținători a fost atins.`)
      notify(pr.autor_id, pr.idea_id, `Proiectul „${pr.dosar.titlu}” a strâns ${pr.voturi} susținători și a fost trimis la Primărie.`, pr.id)
    }
    const out: Vot = { proiect_id: pr.id, voturi: pr.voturi, prag_voturi: prag, stare: pr.stare, votat_de_mine: true }
    return ok(out, 201)
  }

  // POST /proiecte/{id}/trimite {mesaj?}: author; draft | publicat | clarificari -> trimis
  if (m === 'POST' && (r = p.match(/^\/proiecte\/([^/]+)\/trimite$/))) {
    if (!me) return needUser()
    const pr = db.proiecte.find((x) => x.id === r![1])
    if (!pr) return fail(404, 'Proiectul nu există.')
    if (pr.autor_id !== me.id) return fail(403, 'Doar autorul poate trimite proiectul.')
    if (!['draft', 'publicat', 'clarificari'].includes(pr.stare)) return fail(409, 'Proiectul nu poate fi trimis în starea curentă.')
    sendToCityHall(pr, me, typeof body?.mesaj === 'string' ? body.mesaj : null)
    return ok(withoutEvents(pr))
  }

  // POST /proiecte/{id}/inainteaza {verificator_id}: primarie, trimis -> in_verificare, notify the verifier
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

  // POST /proiecte/{id}/decizie {stare, mesaj}: assigned verifier, in_verificare -> acord | respins | clarificari
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
        ? `Proiectul „${pr.dosar.titlu}” a primit acord de principiu (simulat).`
        : stare === 'respins'
          ? `Proiectul „${pr.dosar.titlu}” a fost respins. ${mesaj}`
          : `Pentru proiectul „${pr.dosar.titlu}” se cer clarificări: ${mesaj}`
    for (const id of [pr.autor_id, ...ofRole('primarie').map((x) => x.id)]) notify(id, pr.idea_id, text, pr.id)
    return ok(withoutEvents(pr))
  }

  return null
}
