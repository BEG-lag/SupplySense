import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { loadCompany, loadDetail, toRecords, useJson } from '../lib/data.js'
import { liveStatus } from '../lib/dates.js'
import { useFollowed } from '../lib/follow.js'
import { formatDate, formatNumber } from '../lib/format.js'
import { buildCalendar, downloadCalendar, siteBase } from '../lib/ics.js'
import { useMeta } from '../lib/meta.jsx'
import { useSaved } from '../lib/saved.js'
import { applyFilters, describeFilters } from '../lib/search.js'
import { displayTitle } from '../lib/text.js'
import { Button, Card, Empty, Loading, PageHeader, Section } from '../ui/index.jsx'

function Fresh({ n, label = 'nuevas' }) {
  if (!n) return null
  return (
    <span className="ml-2 rounded-full px-2 py-0.5 text-xs font-medium" style={{ color: 'var(--open)', background: 'var(--open-bg)' }}>
      {n} {label}
    </span>
  )
}

function Row({ title, subtitle, right, to, onOpen, onRemove }) {
  return (
    <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 [overflow-wrap:anywhere]">
        <div className="font-medium">{title}</div>
        <div className="text-[13px] text-ink-3">{subtitle}</div>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <span className="text-sm">{right}</span>
        <Button as={Link} size="sm" to={to} onClick={onOpen}>Ver</Button>
        <Button variant="ghost" size="sm" onClick={onRemove}>Quitar</Button>
      </div>
    </Card>
  )
}

function CompanyItem({ f, follow }) {
  const [c, setC] = useState(undefined)
  useEffect(() => { loadCompany(f.id).then(setC, () => setC(null)) }, [f.id])
  const fresh = c ? c.adjudicaciones.filter((a) => (a.fecha || '') > f.visto).length : 0
  return (
    <Row
      title={f.nombre}
      subtitle={`Empresa · la sigues desde el ${formatDate(f.desde)} · última visita ${formatDate(f.visto)}`}
      right={c === undefined ? '…' : c ? <><span className="num">{formatNumber(c.n)}</span> adjudicaciones<Fresh n={fresh} /></> : 'Ya no aparece'}
      to={`/empresa/${f.id}`}
      onOpen={() => follow.markSeen('empresa', f.id, c ? { n: c.n } : {})}
      onRemove={() => follow.toggle('empresa', f.id)}
    />
  )
}

function BuyerItem({ f, follow, records }) {
  const open = records.filter((r) => r.comprador_id === f.id)
  const fresh = open.filter((r) => (r.primera_vez || '') > f.visto).length
  return (
    <Row
      title={f.nombre}
      subtitle={`Comprador · lo sigues desde el ${formatDate(f.desde)} · última visita ${formatDate(f.visto)}`}
      right={<><span className="num">{formatNumber(open.length)}</span> abiertas<Fresh n={fresh} /></>}
      to={`/comprador/${f.id}`}
      onOpen={() => follow.markSeen('comprador', f.id)}
      onRemove={() => follow.toggle('comprador', f.id)}
    />
  )
}

function TenderItem({ f, follow, meta }) {
  const [rec, setRec] = useState(undefined)
  useEffect(() => { loadDetail(f.id).then(setRec, () => setRec(null)) }, [f.id])
  const now = rec ? liveStatus(rec.estatus, rec.apertura) : null
  const changed = now && f.estatus && now !== f.estatus
  return (
    <Row
      title={displayTitle(f.nombre)}
      subtitle={`Licitación · la sigues desde el ${formatDate(f.desde)}`}
      right={rec === undefined ? '…' : rec
        ? (changed
          ? <span style={{ color: 'var(--open)' }}>Cambió: {meta.estatus[f.estatus]} → {meta.estatus[now]}</span>
          : <span className="text-ink-2">{meta.estatus[now] || now}</span>)
        : 'Ya no aparece'}
      to={`/licitacion/${encodeURIComponent(f.id)}`}
      onOpen={() => follow.markSeen('licitacion', f.id, now ? { estatus: now } : {})}
      onRemove={() => follow.toggle('licitacion', f.id)}
    />
  )
}

// Un solo .ics con las fechas que faltan de todas las licitaciones que sigues.
function CalendarButton({ ids }) {
  const [state, setState] = useState('idle')
  if (!ids.length) return null
  const run = async () => {
    setState('loading')
    const recs = (await Promise.all(ids.map((id) => loadDetail(id).catch(() => null)))).filter(Boolean)
    const ics = buildCalendar(recs, { siteBase: siteBase() })
    if (!ics) return setState('empty')
    downloadCalendar(ics, 'supplysense-siguiendo.ics')
    setState('idle')
  }
  return (
    <span className="flex items-center gap-3">
      {state === 'empty' && <span className="text-[12.5px] text-ink-3">No quedan fechas por venir.</span>}
      <Button size="sm" variant="secondary" onClick={run} disabled={state === 'loading'}>
        {state === 'loading' ? 'Preparando…' : 'Fechas a mi calendario (.ics)'}
      </Button>
    </span>
  )
}

export default function Saved() {
  const { data: meta } = useMeta()
  const { data: open } = useJson('abiertas.json')
  const { list, remove, markSeen } = useSaved()
  const follow = useFollowed()
  const records = useMemo(() => (open && meta ? toRecords(open, meta.indice_campos) : null), [open, meta])

  return (
    <>
      <PageHeader eyebrow="Guardadas" title="Tus búsquedas y seguimientos">
        Se guardan solo en este navegador, sin cuenta ni correo. Cada vez que vuelvas verás qué es
        nuevo o qué cambió desde tu última visita.
      </PageHeader>
      {!records && <Loading />}

      {records && (
        <Section title="Búsquedas" className="mt-0">
          {list.length === 0 ? (
            <Empty title="Aún no guardas búsquedas">
              En <Link className="text-accent" to="/buscar?estatus=abierta">Buscar</Link>, filtra por lo que vendes y usa “Guardar búsqueda”.
            </Empty>
          ) : (
            <div className="grid gap-3">
              {list.map((s) => {
                const filters = { ...s.filters, estatus: 'abierta' }
                const matches = applyFilters(records, filters, { buyers: meta.compradores })
                const fresh = matches.filter((r) => (r.primera_vez || '') > s.visto).length
                const params = new URLSearchParams(filters)
                return (
                  <Row
                    key={s.id}
                    title={s.nombre}
                    subtitle={`${describeFilters(s.filters, meta)} · última visita ${formatDate(s.visto)}`}
                    right={<><span className="num">{formatNumber(matches.length)}</span> abiertas<Fresh n={fresh} /></>}
                    to={`/buscar?${params}`}
                    onOpen={() => markSeen(s.id)}
                    onRemove={() => remove(s.id)}
                  />
                )
              })}
            </div>
          )}
        </Section>
      )}

      {records && (
        <Section
          title="Siguiendo"
          aside={<CalendarButton ids={follow.list.filter((f) => f.tipo === 'licitacion').map((f) => f.id)} />}
        >
          {follow.list.length === 0 ? (
            <Empty title="Aún no sigues a nadie">
              Usa “Seguir” en la página de una empresa, un comprador o una licitación.
            </Empty>
          ) : (
            <div className="grid gap-3">
              {follow.list.map((f) => {
                const key = `${f.tipo}:${f.id}`
                if (f.tipo === 'empresa') return <CompanyItem key={key} f={f} follow={follow} />
                if (f.tipo === 'comprador') return <BuyerItem key={key} f={f} follow={follow} records={records} />
                return <TenderItem key={key} f={f} follow={follow} meta={meta} />
              })}
            </div>
          )}
        </Section>
      )}
    </>
  )
}
