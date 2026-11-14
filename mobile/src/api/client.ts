// Thin fetch wrapper: every request goes through api(). It adds the base URL and X-User-Id.
// With EXPO_PUBLIC_USE_MOCKS=true it answers from src/mocks (P3 example data) instead of the network.
// Body types: ./types.ts for now (provisional), later ./schema.d.ts (`npm run gen:types`).
import { API_URL, USE_MOCKS } from '../config'
import { handleMock } from '../mocks/mockApi'
import type { User } from './models'
import usersData from '../mocks/data/users.json'

// PROVISIONAL demo users (P3's demo data) until the contract defines users.
export const DEMO_USERS = usersData as User[]

let currentUserId = DEMO_USERS[0].id

export function getUserId(): string {
  return currentUserId
}

export function setUserId(id: string): void {
  currentUserId = id
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (USE_MOCKS) {
    const body = typeof init.body === 'string' ? JSON.parse(init.body) : undefined
    const res = handleMock(init.method ?? 'GET', path, body, currentUserId)
    if (res) {
      await new Promise((r) => setTimeout(r, 150)) // feel like a network call
      if (res.status >= 400) throw new ApiError(res.status, (res.body as { detail: string }).detail)
      return res.body as T
    }
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': currentUserId,
      ...(init.headers as Record<string, string> | undefined),
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
