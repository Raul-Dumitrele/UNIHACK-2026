// Demo users for the X-User-Id switcher, from the mock data (same ids as the seed: demo-user-N).
// With the real API these match GET /users once P3's seed is loaded.
import type { User } from '@/api/models'
import usersData from '@/mocks/data/users.json'

export const DEMO_USERS = usersData as User[]
export const DEFAULT_USER_ID = DEMO_USERS[0].id
export const isDemoUser = (id: string) => DEMO_USERS.some((u) => u.id === id)
