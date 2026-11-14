import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '@/api/client'
import { useUser } from '@/user'

/** GET `path` and keep loading/error state. Refetches when the demo user changes. Pass null to skip. */
export function useApi<T>(path: string | null) {
  const { userId } = useUser()
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [errorStatus, setErrorStatus] = useState<number | null>(null)
  const [loading, setLoading] = useState(path !== null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (path === null) return
    let alive = true
    setLoading(true)
    setError(null)
    setErrorStatus(null)
    api<T>(path)
      .then((d) => alive && setData(d))
      .catch((e: Error) => {
        if (!alive) return
        setError(e.message)
        setErrorStatus(e instanceof ApiError ? e.status : null)
      })
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [path, userId, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, error, errorStatus, loading, reload, setData }
}
