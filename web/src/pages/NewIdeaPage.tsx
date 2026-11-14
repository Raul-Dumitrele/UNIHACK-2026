import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import type { Idea, IdeaCreate } from '@/api/models'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

const EXAMPLE = 'Vreau să organizez un atelier de reparat biciclete pentru vecini, sâmbăta dimineața, cam 15 oameni, 3 ore. Avem nevoie de mese și o priză.'

export function NewIdeaPage() {
  const navigate = useNavigate()
  const [descriere, setDescriere] = useState('')
  const [titlu, setTitlu] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setSending(true)
    setError(null)
    try {
      const body: IdeaCreate = { descriere: descriere.trim(), titlu: titlu.trim() || null }
      const idea = await api<Idea>('/ideas', { method: 'POST', body: JSON.stringify(body) })
      toast.success('Ideea a fost publicată')
      navigate(`/idei/${idea.id}`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Propune o idee</h1>
        <p className="text-muted-foreground">
          Descrie ideea în câteva fraze: ce, pentru cine, câți oameni, când. AI-ul o transformă într-un dosar structurat.
        </p>
      </div>
      <Card>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <label className="block space-y-1.5">
              <span className="text-sm font-medium">Descriere</span>
              <Textarea
                value={descriere}
                onChange={(e) => setDescriere(e.target.value)}
                placeholder={EXAMPLE}
                rows={5}
                required
                minLength={3}
              />
            </label>
            <label className="block space-y-1.5">
              <span className="text-sm font-medium">
                Titlu <span className="font-normal text-muted-foreground">(opțional, altfel îl alege AI-ul)</span>
              </span>
              <Input value={titlu} onChange={(e) => setTitlu(e.target.value)} maxLength={80} />
            </label>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" disabled={sending || descriere.trim().length < 3}>
                {sending ? <Loader2 className="animate-spin" /> : <Sparkles />}
                {sending ? 'Se structurează…' : 'Publică ideea'}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setDescriere(EXAMPLE)}>
                Completează un exemplu
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </section>
  )
}
