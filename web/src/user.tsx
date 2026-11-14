import { createContext, useContext, useState, type ReactNode } from 'react'
import { getUserId, setUserId } from '@/api/client'

type Ctx = { userId: string; setUser: (id: string) => void }
const UserContext = createContext<Ctx | null>(null)

export function UserProvider({ children }: { children: ReactNode }) {
  const [userId, setId] = useState(getUserId)
  const setUser = (id: string) => {
    setUserId(id)
    setId(id)
  }
  return <UserContext.Provider value={{ userId, setUser }}>{children}</UserContext.Provider>
}

// eslint-disable-next-line react/only-export-components
export function useUser(): Ctx {
  const ctx = useContext(UserContext)
  if (!ctx) throw new Error('useUser must be used inside UserProvider')
  return ctx
}
