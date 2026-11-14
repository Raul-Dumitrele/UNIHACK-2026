// Demo users for the X-User-Id switcher, from the mock data (same ids as the seed: demo-user-N).
// Owners ("proprietar") are not offered any more: there are no bookings, only citizens, Primărie and verifier.
import type { User } from '@/api/models'
import usersData from '@/mocks/data/users.json'

export const DEMO_USERS = (usersData as User[]).filter((u) => u.rol !== 'proprietar')
export const DEFAULT_USER_ID = DEMO_USERS[0].id
export const isDemoUser = (id: string) => DEMO_USERS.some((u) => u.id === id)
