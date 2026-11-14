// Thin fetch wrapper: every request goes through api(). It adds the base URL and X-User-Id.
// Types: ./models.ts (short names over the generated ./schema.d.ts).
import { API_URL } from '@/config'
import { DEFAULT_USER_ID, isDemoUser } from '@/demoUsers'

const USER_KEY = 'loccomun.userId'

export function getUserId(): string {
  try {
    const id = localStorage.getItem(USER_KEY)
    return id && isDemoUser(id) ? id : DEFAULT_USER_ID
  } catch {
    return DEFAULT_USER_ID
  }
}

export function setUserId(id: string): void {
  try {
    localStorage.setItem(USER_KEY, id)
  } catch {
    /* storage unavailable: keep default */
  }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': getUserId(),
      ...init.headers,
    },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

async function failure(res: Response): Promise<ApiError> {
  let detail = res.statusText
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') detail = body.detail
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(res.status, detail)
}

/** GET a file (SVG, PDF, DXF, CSV). A plain link cannot send X-User-Id, so files are fetched and handed on as blobs. */
export async function apiBlob(path: string): Promise<Blob> {
  const res = await fetch(`${API_URL}${path}`, { headers: { 'X-User-Id': getUserId() } })
  if (!res.ok) throw await failure(res)
  return res.blob()
}

/** Save a blob under `filename` (the browser's download). */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}

/** Bare framework answers mean the route does not exist on the server; anything else carries the server's own `detail`. */
const MISSING_ROUTE = new Set(['Not Found', 'Method Not Allowed'])

/** Error text for the screen. */
export function describeError(e: unknown, feature: string): string {
  if (e instanceof ApiError && (e.status === 404 || e.status === 405) && MISSING_ROUTE.has(e.message)) {
    return `${feature} nu este încă disponibilă pe server (endpoint lipsă).`
  }
  return (e as Error).message
}
