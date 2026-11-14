import { Link } from 'react-router-dom'
import { Users } from 'lucide-react'
import type { Idea } from '@/api/models'
import { Card, CardContent } from '@/components/ui/card'
import { DEMO_USERS } from '@/demoUsers'
import { CATEGORIE, timeAgo } from '@/lib/format'
import { DemoBadge } from './DemoBadge'
import { InterestBar } from './InterestBar'
import { IdeaStatusBadge } from './StatusBadge'

export function IdeaCard({ idea }: { idea: Idea }) {
  const author = DEMO_USERS.find((u) => u.id === idea.author_id)
  return (
    <Link to={`/idei/${idea.id}`} className="group block rounded-xl focus-visible:outline-2">
      <Card className="h-full transition-shadow group-hover:shadow-md">
        <CardContent className="flex h-full flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <IdeaStatusBadge stare={idea.stare} />
            <span className="text-xs text-muted-foreground">{CATEGORIE[idea.structurat.categorie]}</span>
            <DemoBadge show={idea.is_demo} />
          </div>
          <div className="space-y-1">
            <h3 className="font-semibold leading-snug tracking-tight group-hover:text-primary">{idea.titlu}</h3>
            <p className="line-clamp-2 text-sm text-muted-foreground">{idea.descriere}</p>
          </div>
          <div className="mt-auto space-y-2">
            <InterestBar interesati={idea.interesati} prag={idea.prag} />
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Users className="size-3.5" />
              {author?.nume ?? 'Anonim'} · {timeAgo(idea.created_at)}
            </p>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
