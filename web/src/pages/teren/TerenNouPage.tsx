// Mark a free plot: click on the map for the position, then name, area and a short description.
// POST /spaces (planned by P1) -> Space with tip teren_liber.
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, MapPinPlus } from 'lucide-react'
import { toast } from 'sonner'
import { api, describeError } from '@/api/client'
import type { Space, TerenNou } from '@/api/models'
import { ErrorState } from '@/components/StateViews'
import { TerenMap } from '@/components/TerenMap'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { DEMO_USERS } from '@/demoUsers'
import { useTerenuri } from '@/lib/useTerenuri'
import { useUser } from '@/user'

export function TerenNouPage() {
  const navigate = useNavigate()
  const { userId } = useUser()
  const { terenuri } = useTerenuri()
  const [pos, setPos] = useState<[number, number] | null>(null)
  const [nume, setNume] = useState('')
  const [suprafata, setSuprafata] = useState('')
  const [descriere, setDescriere] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isCitizen = DEMO_USERS.find((u) => u.id === userId)?.rol === 'cetatean'

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!pos) return
    setSending(true)
    setError(null)
    try {
      const body: TerenNou = {
        nume: nume.trim(),
        lat: Number(pos[0].toFixed(6)),
        lng: Number(pos[1].toFixed(6)),
        suprafata_mp: Number(suprafata),
        descriere: descriere.trim() || null,
      }
      const s = await api<Space>('/spaces', { method: 'POST', body: JSON.stringify(body) })
      toast.success('Terenul a fost marcat')
      navigate(`/teren/${s.id}`)
    } catch (err) {
      setError(describeError(err, 'Marcarea terenurilor'))
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Harta terenurilor
      </Link>
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Marchează un teren</h1>
        <p className="text-muted-foreground">Apasă pe hartă unde se află terenul, apoi completează datele lui.</p>
      </div>

      {!isCitizen ? (
        <ErrorState message="Doar cetățenii pot marca terenuri. Alege un cetățean din selectorul de sus." />
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <TerenMap
            terenuri={terenuri}
            picked={pos}
            onPick={(lat, lng) => setPos([lat, lng])}
            className="h-[45vh] min-h-72 w-full"
          />
          <p className="text-sm text-muted-foreground">
            {pos ? `Poziție aleasă: ${pos[0].toFixed(5)}, ${pos[1].toFixed(5)}` : 'Nicio poziție aleasă încă.'}
          </p>
          <Card>
            <CardContent className="space-y-4">
              <label className="block space-y-1.5">
                <span className="text-sm font-medium">Nume</span>
                <Input value={nume} onChange={(e) => setNume(e.target.value)} placeholder="ex. Terenul de lângă Școala 12" required minLength={3} />
              </label>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium">Suprafață (mp)</span>
                <Input type="number" min={1} value={suprafata} onChange={(e) => setSuprafata(e.target.value)} required />
              </label>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium">Descriere scurtă (opțional)</span>
                <Textarea value={descriere} onChange={(e) => setDescriere(e.target.value)} rows={3} placeholder="Cum arată acum, ce e în jur" />
              </label>
              {error ? <p className="text-sm text-destructive">{error}</p> : null}
              <Button type="submit" disabled={sending || !pos || nume.trim().length < 3 || !Number(suprafata)}>
                {sending ? <Loader2 className="animate-spin" /> : <MapPinPlus />} Marchează terenul
              </Button>
            </CardContent>
          </Card>
        </form>
      )}
    </section>
  )
}
