// Tabla de licitaciones: tabla en escritorio, tarjetas en celular. Recibe registros del índice.
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useJson } from '../lib/data.js'
import { closingLabel, liveStatus, todayMx } from '../lib/dates.js'
import { formatDate, formatMXNShort } from '../lib/format.js'
import { buyerName, categoryName, SOURCE_NAMES, useMeta } from '../lib/meta.jsx'
import { StatusBadge, Tag } from '../ui/index.jsx'
import { displayTitle } from '../lib/text.js'

const href = (id) => `/licitacion/${encodeURIComponent(id)}`

function Status({ rec, meta, today }) {
  const status = liveStatus(rec.estatus, rec.apertura, today)
  return <StatusBadge status={status} label={meta?.estatus?.[status] || status} estimated={rec.estatus_estimado} />
}

function PriceHint({ rec, prices }) {
  const p = prices?.[rec.categoria]
  if (!p || rec.estatus !== 'abierta' || rec.categoria === 'otros') return null
  return (
    <div className="mt-1.5 text-xs text-ink-3">
      Se ha pagado en este giro: <span className="num text-ink-2">{formatMXNShort(p.p25)} a {formatMXNShort(p.p75)}</span>
      <span className="hidden sm:inline"> · mediana <span className="num">{formatMXNShort(p.p50)}</span></span>
    </div>
  )
}

function Closing({ rec, today }) {
  const label = rec.estatus === 'abierta' ? closingLabel(rec.apertura, today) : null
  if (!label) return null
  return <Tag tone="warn">{label}</Tag>
}

export default function TenderTable({ records, showWinner = false, viaGiro, viaSem }) {
  const { data: meta } = useMeta()
  const { data: priceList } = useJson('precios.json')
  const prices = useMemo(() => Object.fromEntries((priceList || []).map((p) => [p.codigo, p])), [priceList])
  const today = todayMx()
  return (
    <>
      <div className="hidden overflow-x-auto rounded-xl border border-line xl:block">
        <table className="w-full text-sm">
          <thead className="bg-subtle text-left text-[12px] text-ink-3">
            <tr>
              <th className="px-4 py-2.5 font-medium">Licitación</th>
              <th className="px-4 py-2.5 font-medium">Comprador</th>
              <th className="px-4 py-2.5 font-medium">Entidad</th>
              <th className="px-4 py-2.5 font-medium whitespace-nowrap">Publicación</th>
              {showWinner ? <th className="px-4 py-2.5 text-right font-medium">Monto</th> : <th className="px-4 py-2.5 font-medium">Apertura</th>}
              <th className="px-4 py-2.5 font-medium">Estatus</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {records.map((rec) => (
              <tr key={rec.id} className="align-top transition-colors hover:bg-subtle/60">
                <td className="max-w-[420px] px-4 py-3">
                  <Link to={href(rec.id)} className="font-medium leading-snug text-ink hover:text-accent">
                    {displayTitle(rec.titulo)}
                  </Link>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-ink-3">
                    <span className="num">{rec.numero}</span>
                    <Tag tone="accent">{categoryName(meta, rec.categoria)}</Tag>
                    {viaGiro?.has(rec.id) && <Tag>Mismo giro</Tag>}
                    {viaSem?.has(rec.id) && <Tag>Por significado</Tag>}
                    <Closing rec={rec} today={today} />
                  </div>
                  {showWinner && rec.ganador && <div className="mt-1 text-xs text-ink-2">Ganó: {rec.ganador}</div>}
                  <PriceHint rec={rec} prices={prices} />
                </td>
                <td className="px-4 py-3 text-ink-2">
                  <Link to={`/comprador/${rec.comprador_id}`} className="hover:text-ink">{buyerName(meta, rec.comprador_id)}</Link>
                  <div className="text-xs text-ink-3">{SOURCE_NAMES[rec.fuente]}</div>
                </td>
                <td className="px-4 py-3 text-ink-2">{rec.entidad || <span className="text-ink-3">N/D</span>}</td>
                <td className="num whitespace-nowrap px-4 py-3 text-ink-2">{formatDate(rec.publicado)}</td>
                {showWinner
                  ? <td className="num whitespace-nowrap px-4 py-3 text-right">{formatMXNShort(rec.monto)}</td>
                  : <td className="num whitespace-nowrap px-4 py-3 text-ink-2">{rec.apertura ? formatDate(rec.apertura) : <span className="text-ink-3">N/D</span>}</td>}
                <td className="px-4 py-3"><Status rec={rec} meta={meta} today={today} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="space-y-3 xl:hidden">
        {records.map((rec) => (
          <li key={rec.id} className="rounded-xl border border-line p-4">
            <div className="flex items-start justify-between gap-3">
              <Link to={href(rec.id)} className="font-medium leading-snug hover:text-accent">{displayTitle(rec.titulo)}</Link>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
              <Status rec={rec} meta={meta} today={today} />
              <Tag tone="accent">{categoryName(meta, rec.categoria)}</Tag>
              {viaGiro?.has(rec.id) && <Tag>Mismo giro</Tag>}
                    {viaSem?.has(rec.id) && <Tag>Por significado</Tag>}
              <Closing rec={rec} today={today} />
            </div>
            <div className="mt-2 text-[13px] text-ink-2">
              {buyerName(meta, rec.comprador_id)}{rec.entidad ? ` · ${rec.entidad}` : ''}
            </div>
            <div className="num mt-1 text-xs text-ink-3">
              {rec.numero} · {formatDate(rec.publicado)}{showWinner && rec.monto ? ` · ${formatMXNShort(rec.monto)}` : ''}
            </div>
            <PriceHint rec={rec} prices={prices} />
          </li>
        ))}
      </ul>
    </>
  )
}
