import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import type { Space } from '@/api/types'
import { SpacesMap } from '@/components/SpacesMap'

export function MapPage() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // PROVISIONAL endpoint (not in the contract yet); served by the mocks for now.
    api<Space[]>('/spaces')
      .then(setSpaces)
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <section className="space-y-4">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Spații libere</h1>
        <p className="text-muted-foreground">
          {error ? `Nu am putut încărca spațiile: ${error}` : `${spaces.length} spații în Timișoara`}
        </p>
      </div>
      <SpacesMap spaces={spaces} className="h-[60vh] min-h-80 w-full" />
    </section>
  )
}
