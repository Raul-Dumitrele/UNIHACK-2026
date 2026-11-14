// Progress towards the idea's interest threshold (values come from the API; nothing is computed beyond the ratio).
export function InterestBar({ interesati, prag }: { interesati: number; prag: number }) {
  const pct = Math.min(100, Math.round((interesati / Math.max(1, prag)) * 100))
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="font-medium">{interesati} interesați</span>
        <span className="text-muted-foreground">prag {prag}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={interesati} aria-valuemax={prag}>
        <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
