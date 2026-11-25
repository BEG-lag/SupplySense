import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import PriceRange from '../components/PriceRange.jsx'
import { useJson } from '../lib/data.js'
import { formatDate, formatMXN, formatMXNShort, formatNumber } from '../lib/format.js'
import { buyerName, SOURCE_NAMES, useMeta } from '../lib/meta.jsx'
import { describePercentile, percentileOf } from '../lib/prices.js'
import { Card, ErrorNote, Input, Loading, PageHeader, Section, Stat } from '../ui/index.jsx'
import { displayTitle } from '../lib/text.js'

export function PricesIndex() {
  const { data, error, loading } = useJson('precios.json')
  const rows = useMemo(() => (data ? [...data].sort((a, b) => b.n - a.n) : []), [data])
  const max = rows.reduce((m, r) => Math.max(m, r.p75), 1)
  return (
    <>
      <PageHeader eyebrow="Precios" title="Cuánto se paga en cada categoría">
        Montos adjudicados por procedimiento (CFE) o por contrato (ComprasMX) en los últimos 36
        meses, sin montos atípicos. La caja va del percentil 25 al 75 y la línea marca la mediana.
      </PageHeader>
      {loading && <Loading />}
      {error && <ErrorNote error={error} />}
      <div className="overflow-hidden rounded-xl border border-line">
        <ul className="divide-y divide-line">
          {rows.map((r) => (
            <li key={r.codigo}>
              <Link to={`/precios/${r.codigo}`} className="grid grid-cols-1 gap-2 px-4 py-3.5 hover:bg-subtle sm:grid-cols-[1fr_1.4fr_auto] sm:items-center sm:gap-6">
                <div>
                  <div className="font-medium">{r.nombre}</div>
                  <div className="text-xs text-ink-3"><span className="num">{formatNumber(r.n)}</span> adjudicaciones</div>
                </div>
                <div className="relative h-2.5 rounded-full bg-muted" aria-hidden>
                  <div className="absolute inset-y-0 rounded-full" style={{ left: `${(Math.log10(r.p25) / Math.log10(max)) * 100}%`, width: `${((Math.log10(r.p75) - Math.log10(r.p25)) / Math.log10(max)) * 100}%`, background: 'var(--chart-2)' }} />
                  <div className="absolute -inset-y-1 w-0.5" style={{ left: `${(Math.log10(r.p50) / Math.log10(max)) * 100}%`, background: 'var(--chart-1)' }} />
                </div>
                <div className="num text-sm sm:text-right">
                  <span className="font-medium">{formatMXNShort(r.p50)}</span>
                  <span className="text-ink-3"> mediana</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <p className="mt-4 text-xs text-ink-3">Escala logarítmica. PEMEX no publica montos en datos abiertos, así que no entra en estos cálculos.</p>
    </>
  )
}

function Comparator({ data }) {
  const [raw, setRaw] = useState('')
  const amount = Number(raw.replace(/[^\d.]/g, '')) || null
  const pct = amount ? percentileOf(amount, data.percentiles) : null
  return (
    <Card className="p-5">
      <label htmlFor="monto" className="text-sm font-medium">¿Dónde cae tu monto?</label>
      <p className="mt-1 text-[13px] text-ink-2">Escribe un monto sin IVA, en pesos, para ubicarlo frente a lo adjudicado en la categoría. No es una probabilidad de ganar.</p>
      <div className="mt-3 flex max-w-sm items-center gap-2">
        <span className="text-ink-3">$</span>
        <Input id="monto" inputMode="decimal" value={raw} onChange={(e) => setRaw(e.target.value)} placeholder="1,500,000" />
      </div>
      <PriceRange percentiles={data.percentiles} mark={amount} />
      {pct && (
        <p className="mt-3 text-sm">
          <span className="font-medium">{describePercentile(pct)}</span> de {data.nombre.toLowerCase()} en los últimos 36 meses
          (<span className="num">{formatNumber(data.n)}</span> casos).
        </p>
      )}
    </Card>
  )
}

export function PriceCategory() {
  const { codigo } = useParams()
  const { data: meta } = useMeta()
  const { data, error, loading } = useJson(`precios/${codigo}.json`)
  if (loading || !meta) return <Loading />
  if (error) return <ErrorNote error={error} />
  document.title = `Precios de ${data.nombre.toLowerCase()} · SupplySense`
  const serie = data.anual.filter((y) => y.n >= 5).map((y) => ({ ...y, rango: [y.p25, y.p75] }))
  return (
    <>
      <nav className="mb-4 text-[13px] text-ink-3"><Link to="/precios" className="hover:text-ink">Precios</Link> / {data.nombre}</nav>
      <PageHeader title={data.nombre}>
        <span className="num">{formatNumber(data.n)}</span> adjudicaciones del {formatDate(data.desde)} al {formatDate(data.hasta)}.
      </PageHeader>
      <Card className="grid grid-cols-2 gap-6 bg-subtle p-6 sm:grid-cols-4">
        <Stat value={formatMXNShort(data.percentiles['25'])} label="Percentil 25" />
        <Stat value={formatMXNShort(data.percentiles['50'])} label="Mediana" />
        <Stat value={formatMXNShort(data.percentiles['75'])} label="Percentil 75" />
        <Stat value={formatNumber(data.concentracion_hhi)} label="Concentración (HHI)" hint={data.concentracion_hhi > 2500 ? 'Mercado concentrado' : data.concentracion_hhi > 1500 ? 'Moderadamente concentrado' : 'Mercado disperso'} />
      </Card>

      <Section title="Compara un monto"><Comparator data={data} /></Section>

      {serie.length > 1 && (
        <Section title="Mediana y rango por año">
          <Card className="h-72 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={serie} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
                <CartesianGrid stroke="var(--line)" vertical={false} />
                <XAxis dataKey="anio" tick={{ fill: 'var(--ink-3)', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={formatMXNShort} tick={{ fill: 'var(--ink-3)', fontSize: 12 }} axisLine={false} tickLine={false} width={72} />
                <Tooltip
                  contentStyle={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, fontSize: 12 }}
                  formatter={(v, name) => (Array.isArray(v) ? [`${formatMXNShort(v[0])} a ${formatMXNShort(v[1])}`, 'P25 a P75'] : [formatMXNShort(v), name])}
                  labelFormatter={(l) => `Año ${l}`}
                />
                <Area dataKey="rango" stroke="none" fill="var(--chart-3)" name="P25 a P75" />
                <Line dataKey="p50" stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 3 }} name="Mediana" />
              </ComposedChart>
            </ResponsiveContainer>
          </Card>
        </Section>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {data.por_tipo.length > 0 && (
          <Section title="Por tipo de contratación">
            <Card className="divide-y divide-line">
              {data.por_tipo.map((t) => (
                <div key={t.tipo} className="flex items-center justify-between gap-4 px-4 py-3 text-sm">
                  <span>{t.tipo} <span className="num text-ink-3">({formatNumber(t.n)})</span></span>
                  <span className="num text-ink-2">{formatMXNShort(t.p25)} · <span className="font-medium text-ink">{formatMXNShort(t.p50)}</span> · {formatMXNShort(t.p75)}</span>
                </div>
              ))}
            </Card>
          </Section>
        )}
        <Section title="Quién gana más (36 meses)">
          <Card className="divide-y divide-line">
            {data.ganadores.slice(0, 10).map((g, i) => (
              <Link key={g.id} to={`/empresa/${g.id}`} className="flex items-center justify-between gap-4 px-4 py-3 text-sm hover:bg-subtle">
                <span className="min-w-0 truncate"><span className="num mr-2 text-ink-3">{i + 1}</span>{g.nombre}</span>
                <span className="num shrink-0">{formatMXNShort(g.monto)}</span>
              </Link>
            ))}
          </Card>
        </Section>
      </div>

      <Section title="Adjudicaciones recientes">
        <div className="overflow-x-auto rounded-xl border border-line">
          <table className="w-full text-sm">
            <thead className="bg-subtle text-left text-xs text-ink-3">
              <tr><th className="px-4 py-2 font-medium">Procedimiento</th><th className="px-4 py-2 font-medium">Ganador</th><th className="px-4 py-2 font-medium">Fecha</th><th className="px-4 py-2 text-right font-medium">Monto</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {data.recientes.slice(0, 25).map((a) => (
                <tr key={a.id} className="align-top">
                  <td className="max-w-md px-4 py-2.5">
                    <Link to={`/licitacion/${encodeURIComponent(a.procedimiento_id || a.id)}`} className="hover:text-accent">{displayTitle(a.titulo)}</Link>
                    <div className="text-xs text-ink-3">{buyerName(meta, a.comprador_id)} · {SOURCE_NAMES[a.fuente]}</div>
                  </td>
                  <td className="px-4 py-2.5 text-ink-2">{a.ganadores.slice(0, 2).join(', ')}{a.ganadores.length > 2 ? '…' : ''}</td>
                  <td className="num whitespace-nowrap px-4 py-2.5 text-ink-2">{formatDate(a.fecha)}</td>
                  <td className="num whitespace-nowrap px-4 py-2.5 text-right">{formatMXN(a.monto_mxn)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </>
  )
}
