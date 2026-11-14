// Author asks a space owner for a slot: pick a free slot, get the AI-written message, send the request.
import { useState } from 'react'
import { CalendarPlus, Loader2, Send } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import type { Booking, BookingCreate, Idea, Match, OwnerMessage, Slot } from '@/api/models'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { fmtSlot, slotKey } from '@/lib/format'
import { cn } from '@/lib/utils'

export function BookingDialog({ idea, match, onBooked }: { idea: Idea; match: Match; onBooked: () => void }) {
  const [open, setOpen] = useState(false)
  // Prefer the overlap with the idea's schedule; otherwise any free slot of the space.
  const options: Slot[] = match.suprapunere.length ? match.suprapunere : match.space.sloturi
  const [slot, setSlot] = useState<Slot | null>(options[0] ?? null)
  const [mesaj, setMesaj] = useState<string | null>(null)
  const [busy, setBusy] = useState<'mesaj' | 'trimit' | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadMessage(s: Slot) {
    setBusy('mesaj')
    setError(null)
    try {
      const r = await api<OwnerMessage>(`/ideas/${idea.id}/owner-message`, {
        method: 'POST',
        body: JSON.stringify({ space_id: match.space.id, slot: s }),
      })
      setMesaj(r.mesaj)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  async function send() {
    if (!slot) return
    setBusy('trimit')
    setError(null)
    try {
      const body: BookingCreate = { idea_id: idea.id, space_id: match.space.id, slot, mesaj }
      await api<Booking>('/bookings', { method: 'POST', body: JSON.stringify(body) })
      toast.success('Cererea a fost trimisă proprietarului')
      setOpen(false)
      onBooked()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        if (o && slot && !mesaj) loadMessage(slot)
      }}
    >
      <DialogTrigger asChild>
        <Button size="sm">
          <CalendarPlus /> Cere rezervare
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Rezervare la {match.space.nume}</DialogTitle>
          <DialogDescription>Alege un interval liber. Proprietarul primește cererea și decide.</DialogDescription>
        </DialogHeader>

        {options.length === 0 ? (
          <p className="text-sm text-muted-foreground">Spațiul nu mai are intervale libere.</p>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {options.map((s) => {
                const active = slot && slotKey(s) === slotKey(slot)
                return (
                  <button
                    key={slotKey(s)}
                    type="button"
                    onClick={() => {
                      setSlot(s)
                      loadMessage(s)
                    }}
                    className={cn(
                      'rounded-full border px-3 py-1 text-sm transition-colors',
                      active ? 'border-primary bg-primary text-primary-foreground' : 'hover:bg-muted',
                    )}
                  >
                    {fmtSlot(s)}
                  </button>
                )
              })}
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Mesaj către proprietar</p>
              <div className="min-h-20 rounded-lg border bg-muted/40 p-3 text-sm">
                {busy === 'mesaj' ? (
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="size-4 animate-spin" /> Se scrie mesajul…
                  </span>
                ) : (
                  (mesaj ?? <span className="text-muted-foreground">Alege un interval.</span>)
                )}
              </div>
            </div>
          </div>
        )}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Renunță
          </Button>
          <Button onClick={send} disabled={!slot || busy !== null}>
            {busy === 'trimit' ? <Loader2 className="animate-spin" /> : <Send />} Trimite cererea
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
