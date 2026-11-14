import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import type { Idea, IdeaStatus } from '@/api/models'
import { IdeaCard } from '@/components/IdeaCard'
import { EmptyState, ErrorState, LoadingCards } from '@/components/StateViews'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useApi } from '@/lib/useApi'

type Filter = 'toate' | IdeaStatus

export function IdeasPage() {
  const { data, error, loading, reload } = useApi<Idea[]>('/ideas')
  const [filter, setFilter] = useState<Filter>('toate')
  const ideas = (data ?? []).filter((i) => filter === 'toate' || i.stare === filter)

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">Idei din comunitate</h1>
          <p className="text-muted-foreground">Susține ideile vecinilor. Când strâng destui interesați, își caută un spațiu.</p>
        </div>
        <Button asChild>
          <Link to="/idei/noua">
            <Plus /> Propune o idee
          </Link>
        </Button>
      </div>

      <Tabs value={filter} onValueChange={(v) => setFilter(v as Filter)}>
        <TabsList>
          <TabsTrigger value="toate">Toate</TabsTrigger>
          <TabsTrigger value="deschisa">Deschise</TabsTrigger>
          <TabsTrigger value="prag_atins">Prag atins</TabsTrigger>
          <TabsTrigger value="rezervata">Rezervate</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading && !data ? (
        <LoadingCards count={6} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : ideas.length === 0 ? (
        <EmptyState
          title={filter === 'toate' ? 'Încă nu sunt idei' : 'Nicio idee în această categorie'}
          action={
            <Button asChild variant="outline" size="sm">
              <Link to="/idei/noua">Propune prima idee</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ideas.map((idea) => (
            <IdeaCard key={idea.id} idea={idea} />
          ))}
        </div>
      )}
    </section>
  )
}
