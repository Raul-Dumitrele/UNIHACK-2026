import type { Space } from '@/api/models'
import { useApi } from '@/lib/useApi'

/** Free plots only: the server filters with ?tip=teren_liber. */
export function useTerenuri() {
  const r = useApi<Space[]>('/spaces?tip=teren_liber')
  return { ...r, terenuri: r.data ?? [] }
}
