// Barra de rango P5 a P95 con la caja P25 a P75, la mediana y, opcionalmente, un monto marcado.
import { formatMXNShort } from '../lib/format.js'

const pos = (v, lo, hi) => {
  const a = Math.log10(Math.max(lo, 1))
  const b = Math.log10(Math.max(hi, 1))
  const x = Math.log10(Math.max(v, 1))
  return Math.min(100, Math.max(0, ((x - a) / (b - a || 1)) * 100))
}

export default function PriceRange({ percentiles, mark, markLabel = 'Tu monto' }) {
  if (!percentiles) return null
  const lo = percentiles['5']
  const hi = percentiles['95']
  const p25 = pos(percentiles['25'], lo, hi)
  const p50 = pos(percentiles['50'], lo, hi)
  const p75 = pos(percentiles['75'], lo, hi)
  const m = mark != null ? pos(mark, lo, hi) : null
  return (
    <div className="pt-6">
      <div className="relative h-3 rounded-full bg-muted">
        <div className="absolute inset-y-0 rounded-full" style={{ left: `${p25}%`, width: `${p75 - p25}%`, background: 'var(--chart-2)' }} />
        <div className="absolute -inset-y-1 w-0.5 rounded" style={{ left: `${p50}%`, background: 'var(--chart-1)' }} />
        {m != null && (
          <div className="absolute -top-6 -translate-x-1/2 text-center" style={{ left: `${m}%` }}>
            <div className="whitespace-nowrap rounded-full bg-papel px-2 py-0.5 text-[11px] font-semibold text-tinta">{markLabel}</div>
            <div className="mx-auto h-5 w-0.5 bg-papel" />
          </div>
        )}
      </div>
      <div className="num mt-2 grid grid-cols-5 text-[11px] text-ink-3">
        <span>P5 {formatMXNShort(lo)}</span>
        <span className="text-center">P25 {formatMXNShort(percentiles['25'])}</span>
        <span className="text-center font-medium text-accent">Mediana {formatMXNShort(percentiles['50'])}</span>
        <span className="text-center">P75 {formatMXNShort(percentiles['75'])}</span>
        <span className="text-right">P95 {formatMXNShort(hi)}</span>
      </div>
    </div>
  )
}
