// Thin fetch wrapper: every request goes through api(). It adds the base URL and X-User-Id.
// Body types: ./types.ts for now (provisional), later ./schema.d.ts (`npm run gen:types`).
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
