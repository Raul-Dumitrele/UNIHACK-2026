// Demo users for the X-User-Id switcher. PROVISIONAL: taken from P3's demo data until
// the contract defines users (and maybe GET /users).
import type { User } from '@/api/types'
import usersData from '@/mocks/data/users.json'

export const DEMO_USERS = usersData as User[]
export const DEFAULT_USER_ID = DEMO_USERS[0].id
export const isDemoUser = (id: string) => DEMO_USERS.some((u) => u.id === id)
