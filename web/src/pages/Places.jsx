// Páginas por estado y por giro: convocatorias abiertas, compradores y precios del grupo.
import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import PriceRange from '../components/PriceRange.jsx'
import TenderTable from '../components/TenderTable.jsx'
import { toRecords, useJson } from '../lib/data.js'
import { formatMXNShort, formatNumber } from '../lib/format.js'
import { buyerName, categoryName, STATES_WITH_PORTAL, useMeta } from '../lib/meta.jsx'
import { fold } from '../lib/search.js'
import { Button, Card, Empty, Loading, PageHeader, Section, Stat, Tag } from '../ui/index.jsx'

export const slugify = (text) => fold(text).replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
const LIMIT = 40

function useOpen() {
  const { data: meta } = useMeta()
  const { data: rows } = useJson('abiertas.json')
  const records = useMemo(() => (rows && meta ? toRecords(rows, meta.indice_campos) : null), [rows, meta])
  return { meta, records }
}

function top(records, key, n = 8) {
  const counts = new Map()
  for (const r of records) if (r[key]) counts.set(r[key], (counts.get(r[key]) || 0) + 1)
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, n)
}

export function StatesIndex() {
  const { meta, records } = useOpen()
  if (!records) return <Loading />
  const counts = new Map(top(records, 'entidad', 40))
  return (
    <>
      <PageHeader eyebrow="Por estado" title="Convocatorias abiertas por estado">
        Las de ComprasMX y CFE traen la entidad; PEMEX no la publica.
      </PageHeader>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {meta.entidades.map((e) => (
          <Link key={e} to={`/estado/${slugify(e)}`} className="flex items-center justify-between rounded-xl border border-line px-4 py-3 text-sm hover:border-accent hover:text-accent">
            <span>{e}</span>
            <span className="num text-ink-3">{formatNumber(counts.get(e) || 0)}</span>
          </Link>
        ))}
      </div>
    </>
  )
}

export function StatePage() {
  const { slug } = useParams()
  const { meta, records } = useOpen()
  if (!records) return <Loading />
  const name = meta.entidades.find((e) => slugify(e) === slug)
  if (!name) return <Empty title="No encontramos ese estado"><Link className="text-accent" to="/estados">Ver estados</Link></Empty>
  document.title = `Licitaciones abiertas en ${name} · SupplySense`
  const open = records.filter((r) => r.entidad === name)
  const energy = open.filter((r) => r.sector === 'energia').length
  return (
    <>
      <nav className="mb-4 text-[13px] text-ink-3"><Link to="/estados" className="hover:text-ink">Por estado</Link> / {name}</nav>
      <PageHeader title={`Licitaciones abiertas en ${name}`} actions={<Button as={Link} size="sm" variant="secondary" to={`/buscar?estatus=abierta&entidad=${encodeURIComponent(name)}`}>Filtrar en Buscar</Button>}>
        Convocatorias de dependencias federales, de compras estatales y municipales con dinero
        federal y de CFE en {name}
        {STATES_WITH_PORTAL.includes(name) ? ', más las compras con recursos propios que publica el portal del estado.' : '. Las compras con recursos propios de este estado aún no están integradas.'}
      </PageHeader>
      <Card className="grid grid-cols-2 gap-6 p-6 sm:grid-cols-3">
        <Stat value={formatNumber(open.length)} label="Abiertas hoy" />
        <Stat value={formatNumber(energy)} label="De energía y O&G" />
        <Stat value={formatNumber(top(open, 'comprador_id', 1000).length)} label="Compradores con convocatorias" />
      </Card>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section title="Giros con más convocatorias">
          <div className="flex flex-wrap gap-2">
            {top(open, 'categoria').map(([c, n]) => <Tag key={c} to={`/giro/${c}`}>{categoryName(meta, c)} · {n}</Tag>)}
          </div>
        </Section>
        <Section title="Quién está comprando">
          <div className="flex flex-wrap gap-2">
            {top(open, 'comprador_id').map(([b, n]) => <Tag key={b} to={`/comprador/${b}`}>{buyerName(meta, b)} · {n}</Tag>)}
          </div>
        </Section>
      </div>
      <Section title="Convocatorias" aside={open.length > LIMIT ? <Link className="text-sm text-accent hover:underline" to={`/buscar?estatus=abierta&entidad=${encodeURIComponent(name)}`}>Ver las {formatNumber(open.length)}</Link> : null}>
        {open.length ? <TenderTable records={open.slice(0, LIMIT)} /> : <Empty title="Sin convocatorias abiertas hoy" />}
      </Section>
    </>
  )
}

export function CategoryPage() {
  const { codigo } = useParams()
  const { meta, records } = useOpen()
  const { data: prices } = useJson(codigo ? `precios/${codigo}.json` : null)
  if (!records) return <Loading />
  const info = meta.categorias.find((c) => c.codigo === codigo)
  if (!info) return <Empty title="No encontramos ese giro"><Link className="text-accent" to="/precios">Ver giros</Link></Empty>
  document.title = `Licitaciones de ${info.nombre.toLowerCase()} · SupplySense`
  const open = records.filter((r) => r.categoria === codigo)
  return (
    <>
      <nav className="mb-4 text-[13px] text-ink-3"><Link to="/precios" className="hover:text-ink">Giros</Link> / {info.nombre}</nav>
      <PageHeader title={`Licitaciones de ${info.nombre.toLowerCase()}`} actions={(
        <>
          <Button as={Link} size="sm" variant="secondary" to={`/buscar?estatus=abierta&categoria=${codigo}`}>Filtrar en Buscar</Button>
          <Button as={Link} size="sm" variant="secondary" to={`/precios/${codigo}`}>Precios del giro</Button>
        </>
      )}>
        Convocatorias abiertas hoy y lo que se ha pagado en este giro.
      </PageHeader>
      <Card className="grid grid-cols-2 gap-6 p-6 sm:grid-cols-4">
        <Stat value={formatNumber(open.length)} label="Abiertas hoy" />
        <Stat value={prices?.percentiles ? formatMXNShort(prices.percentiles['50']) : 'N/D'} label="Mediana adjudicada" hint="36 meses" />
        <Stat value={prices?.n ? formatNumber(prices.n) : 'N/D'} label="Adjudicaciones de referencia" />
        <Stat value={formatNumber(top(open, 'comprador_id', 1000).length)} label="Compradores con convocatorias" />
      </Card>
      {prices?.percentiles && (
        <Section title="Rango de precios">
          <Card className="p-5"><PriceRange percentiles={prices.percentiles} /></Card>
        </Section>
      )}
      <Section title="Convocatorias abiertas" aside={open.length > LIMIT ? <Link className="text-sm text-accent hover:underline" to={`/buscar?estatus=abierta&categoria=${codigo}`}>Ver las {formatNumber(open.length)}</Link> : null}>
        {open.length ? <TenderTable records={open.slice(0, LIMIT)} /> : <Empty title="Sin convocatorias abiertas hoy" />}
      </Section>
      {prices?.ganadores?.length > 0 && (
        <Section title="Quién gana más en este giro">
          <div className="flex flex-wrap gap-2">
            {prices.ganadores.slice(0, 10).map((g) => <Tag key={g.id} to={`/empresa/${g.id}`}>{g.nombre} · {formatMXNShort(g.monto)}</Tag>)}
          </div>
        </Section>
      )}
    </>
  )
}
