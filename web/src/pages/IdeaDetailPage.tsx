import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Clock, Heart, Landmark, Loader2, MapPin, Users, Volume2 } from 'lucide-react'
import { toast } from 'sonner'
import { api, ApiError } from '@/api/client'
import type { Idea, Match } from '@/api/models'
import { BookingDialog } from '@/components/BookingDialog'
import { DemoBadge } from '@/components/DemoBadge'
import { InterestBar } from '@/components/InterestBar'
import { EmptyState, ErrorState, LoadingCards } from '@/components/StateViews'
import { IdeaStatusBadge } from '@/components/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { DEMO_USERS } from '@/demoUsers'
import { CATEGORIE, DOTARE, fmtSlot, slotKey, timeAgo, ZGOMOT } from '@/lib/format'
import { useApi } from '@/lib/useApi'
import { useUser } from '@/user'

export function IdeaDetailPage() {
  const { id = '' } = useParams()
  const { userId } = useUser()
  const idea = useApi<Idea>(`/ideas/${id}`)
  const matches = useApi<Match[]>(`/ideas/${id}/matches`)
  const [sending, setSending] = useState(false)
  const [showAll, setShowAll] = useState(false)

  if (idea.loading && !idea.data) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-9 w-2/3" />
        <LoadingCards count={3} />
      </div>
    )
  }
  if (idea.error || !idea.data) return <ErrorState message={idea.error ?? 'Ideea nu există.'} onRetry={idea.reload} />

  const i = idea.data
  const author = DEMO_USERS.find((u) => u.id === i.author_id)
  const isAuthor = i.author_id === userId
  const s = i.structurat

  async function interest() {
    setSending(true)
    try {
      const updated = await api<Idea>(`/ideas/${i.id}/interest`, { method: 'POST' })
      idea.setData(updated)
      toast.success(updated.stare === 'prag_atins' && i.stare === 'deschisa' ? 'Pragul a fost atins!' : 'Interes înregistrat')
    } catch (e) {
      const err = e as ApiError
      if (err.status === 409) toast.info(err.message)
      else toast.error(err.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Toate ideile
      </Link>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <IdeaStatusBadge stare={i.stare} />
          <Badge variant="secondary">{CATEGORIE[s.categorie]}</Badge>
          <DemoBadge show={i.is_demo} />
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">{i.titlu}</h1>
        <p className="text-sm text-muted-foreground">
          Propusă de {author?.nume ?? 'Anonim'}
          {isAuthor ? ' (tu)' : ''} · {timeAgo(i.created_at)}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Descriere</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="leading-relaxed">{i.descriere}</p>
              <div className="grid gap-3 text-sm sm:grid-cols-3">
                <Fact icon={Users} label="Persoane" value={String(s.persoane)} />
                <Fact icon={Volume2} label="Zgomot" value={ZGOMOT[s.zgomot]} />
                <Fact icon={Clock} label="Program" value={s.program.length ? s.program.map(fmtSlot).join(', ') : 'flexibil'} />
              </div>
              {s.dotari.length ? (
                <div className="flex flex-wrap gap-1.5">
                  {s.dotari.map((d) => (
                    <Badge key={d} variant="outline">
                      {DOTARE[d]}
                    </Badge>
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <div className="space-y-3">
            <h2 className="text-xl font-semibold tracking-tight">Spații potrivite</h2>
            {matches.loading && !matches.data ? (
              <LoadingCards count={2} />
            ) : matches.error ? (
              <ErrorState message={matches.error} onRetry={matches.reload} />
            ) : !matches.data?.length ? (
              <EmptyState title="Nu am găsit spații potrivite" />
            ) : (
              <div className="space-y-3">
                {(showAll ? matches.data : matches.data.slice(0, 5)).map((m) => (
                  <MatchCard
                    key={m.space.id}
                    match={m}
                    canBook={isAuthor && i.stare === 'prag_atins'}
                    idea={i}
                    onBooked={matches.reload}
                  />
                ))}
                {matches.data.length > 5 ? (
                  <Button variant="ghost" size="sm" onClick={() => setShowAll((v) => !v)}>
                    {showAll ? 'Arată doar primele 5' : `Arată toate cele ${matches.data.length} spații`}
                  </Button>
                ) : null}
                <p className="text-xs text-muted-foreground">Date spații: © OpenStreetMap contributors (ODbL)</p>
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-4">
          <Card>
            <CardContent className="space-y-4">
              <InterestBar interesati={i.interesati} prag={i.prag} />
              {isAuthor ? (
                <p className="text-sm text-muted-foreground">
                  {i.stare === 'deschisa'
                    ? 'Ideea ta strânge susținători. La prag, poți cere o rezervare.'
                    : i.stare === 'prag_atins'
                      ? 'Pragul e atins: alege un spațiu și cere rezervarea.'
                      : 'Ideea are deja o rezervare aprobată.'}
                </p>
              ) : null}
              {isAuthor && (i.stare === 'prag_atins' || i.stare === 'rezervata') ? (
                <Button asChild variant="outline" className="w-full">
                  <Link to={`/proiecte/nou?idea=${i.id}`}>
                    <Landmark /> Propune ca proiect către Primărie
                  </Link>
                </Button>
              ) : null}
              {isAuthor ? null : (
                <Button className="w-full" onClick={interest} disabled={sending}>
                  {sending ? <Loader2 className="animate-spin" /> : <Heart />} Mă interesează
                </Button>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>
    </section>
  )
}

function Fact({ icon: Icon, label, value }: { icon: typeof Users; label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted/60 p-3">
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon className="size-3.5" /> {label}
      </p>
      <p className="mt-0.5 font-medium">{value}</p>
    </div>
  )
}

function MatchCard({ match, idea, canBook, onBooked }: { match: Match; idea: Idea; canBook: boolean; onBooked: () => void }) {
  const sp = match.space
  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-0.5">
            <p className="flex flex-wrap items-center gap-2 font-semibold">
              {sp.nume} <DemoBadge show={sp.is_demo} />
            </p>
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <MapPin className="size-3.5" /> {sp.tip} · {sp.capacitate} locuri
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-semibold tabular-nums text-primary">{match.scor}</p>
            <p className="text-xs text-muted-foreground">scor potrivire</p>
          </div>
        </div>
        <p className="text-sm">{match.motiv}</p>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1.5">
            {(match.suprapunere.length ? match.suprapunere : sp.sloturi.slice(0, 3)).map((s) => (
              <Badge key={slotKey(s)} variant="outline" className={match.suprapunere.length ? 'border-primary/40 text-primary' : ''}>
                {fmtSlot(s)}
              </Badge>
            ))}
            {!match.suprapunere.length && sp.sloturi.length ? (
              <span className="text-xs text-muted-foreground">intervale libere (fără suprapunere cu programul)</span>
            ) : null}
          </div>
          {canBook ? <BookingDialog idea={idea} match={match} onBooked={onBooked} /> : null}
        </div>
      </CardContent>
    </Card>
  )
}
