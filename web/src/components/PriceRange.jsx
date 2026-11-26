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
          // En celular la etiqueta se recorre hacia adentro cerca de los extremos (se desplaza el
          // m % de su ancho en vez del 50 %) para no salirse de la pantalla; la línea sigue en el monto.
          <div className="absolute -top-6 translate-x-(--recorre) text-center sm:-translate-x-1/2" style={{ left: `${m}%`, '--recorre': `${-m}%`, '--punto': `${m}%` }}>
            <div className="whitespace-nowrap rounded-full bg-papel px-2 py-0.5 text-[11px] font-semibold text-tinta">{markLabel}</div>
            <div className="ml-(--punto) h-5 w-0.5 -translate-x-1/2 bg-papel sm:mx-auto sm:translate-x-0" />
          </div>
        )}
      </div>
      {/* En celular los cinco valores fluyen en renglones; desde sm, cinco columnas. */}
      <div className="num mt-2 flex flex-wrap justify-between gap-x-3 gap-y-1 text-[11px] text-ink-3 sm:grid sm:grid-cols-5 sm:gap-0">
        <span>P5 {formatMXNShort(lo)}</span>
        <span className="text-center">P25 {formatMXNShort(percentiles['25'])}</span>
        <span className="text-center font-medium text-accent">Mediana {formatMXNShort(percentiles['50'])}</span>
        <span className="text-center">P75 {formatMXNShort(percentiles['75'])}</span>
        <span className="text-right">P95 {formatMXNShort(hi)}</span>
      </div>
    </div>
  )
}
