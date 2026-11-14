import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import type { Space } from '@/api/models'
import { SpacesMap } from '@/components/SpacesMap'

export function MapPage() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
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
        <p className="flex flex-wrap gap-4 pt-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5"><span className="size-3 rounded-full bg-primary" /> spațiu de închiriat</span>
          <span className="flex items-center gap-1.5"><span className="size-3 rotate-45 rounded-sm bg-demo" /> teren liber</span>
        </p>
      </div>
      <SpacesMap spaces={spaces} className="h-[60vh] min-h-80 w-full" />
    </section>
  )
}
