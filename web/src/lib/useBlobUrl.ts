import { useEffect, useState } from 'react'
import { apiBlob, ApiError } from '@/api/client'
import { useUser } from '@/user'

type State = { path: string; user: string; url: string | null; status: number | null; error: string | null }

/** Fetch a file with X-User-Id and expose it as an object URL (usable in <img src>). Revoked on unmount. */
export function useBlobUrl(path: string) {
  const { userId } = useUser()
  const [state, setState] = useState<State | null>(null)

  useEffect(() => {
    let alive = true
    let made: string | null = null
    apiBlob(path)
      .then((blob) => {
        made = URL.createObjectURL(blob)
        if (alive) setState({ path, user: userId, url: made, status: null, error: null })
      })
      .catch((e: Error) => {
        if (alive) setState({ path, user: userId, url: null, status: e instanceof ApiError ? e.status : null, error: e.message })
      })
    return () => {
      alive = false
      if (made) URL.revokeObjectURL(made)
    }
  }, [path, userId])

  const current = state && state.path === path && state.user === userId ? state : null
  return { url: current?.url ?? null, error: current?.error ?? null, errorStatus: current?.status ?? null, loading: current === null }
}
