import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { Bell, BarChart3, CalendarCheck, FlaskConical, Landmark, Lightbulb, Map, Plus } from 'lucide-react'
import { api } from '@/api/client'
import { Toaster } from '@/components/ui/sonner'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { USE_MOCKS } from '@/config'
import { DEMO_USERS } from '@/demoUsers'
import { ROL } from '@/lib/format'
import { useUser } from '@/user'

const NAV = [
  { to: '/', label: 'Idei', icon: Lightbulb },
  { to: '/idei/noua', label: 'Idee nouă', icon: Plus },
  { to: '/harta', label: 'Hartă', icon: Map },
  { to: '/rezervari', label: 'Rezervări', icon: CalendarCheck },
  { to: '/proiecte', label: 'Proiecte', icon: Landmark },
  { to: '/notificari', label: 'Notificări', icon: Bell },
  { to: '/impact', label: 'Impact', icon: BarChart3 },
]

function ApiStatus() {
  const [ok, setOk] = useState<boolean | null>(null)
  useEffect(() => {
    api<{ status: string }>('/health')
      .then((r) => setOk(r.status === 'ok'))
      .catch(() => setOk(false))
  }, [])
  const label = ok === null ? 'se verifică…' : ok ? 'API conectat' : 'API indisponibil'
  return (
    <span className="hidden items-center gap-1.5 text-xs text-muted-foreground sm:flex" title={label}>
      <span
        className={cn(
          'size-2 rounded-full bg-muted-foreground/40',
          ok === true && 'bg-success',
          ok === false && 'bg-destructive',
        )}
      />
      <span className="hidden 2xl:inline">{label}</span>
    </span>
  )
}

export function Layout() {
  const { userId, setUser } = useUser()
  return (
    <div className="min-h-dvh overflow-x-clip">
      <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur print:hidden">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <span className="text-lg font-semibold tracking-tight text-primary">Loc Comun</span>
          <nav className="order-last -mx-1 flex w-full min-w-0 gap-0.5 overflow-x-auto px-1 md:order-none md:mx-0 md:w-auto md:px-0">
            {NAV.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-1.5 whitespace-nowrap rounded-lg px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                    isActive && 'bg-accent font-medium text-accent-foreground',
                  )
                }
              >
                <Icon className="size-4" />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            {USE_MOCKS ? (
              <span className="flex items-center gap-1 rounded-full bg-demo-soft px-2 py-0.5 text-xs font-medium text-demo" title="VITE_USE_MOCKS=true">
                <FlaskConical className="size-3.5" /> date mock
              </span>
            ) : (
              <ApiStatus />
            )}
            <Select value={userId} onValueChange={setUser}>
              <SelectTrigger size="sm" aria-label="Utilizator demo" className="w-52">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DEMO_USERS.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.nume} · {ROL[u.rol]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 print:max-w-none print:p-0">
        <Outlet />
      </main>
      <Toaster position="bottom-center" />
    </div>
  )
}
