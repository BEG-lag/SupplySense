import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import TenderTable from '../components/TenderTable.jsx'
import { toRecords, useJson } from '../lib/data.js'
import { formatMXNShort, formatNumber } from '../lib/format.js'
import { categoryName, useMeta } from '../lib/meta.jsx'
import { Button, Card, Empty, ErrorNote, Input, Loading, PageHeader, Section, Select, Stat, Tag } from '../ui/index.jsx'
import { fold } from '../lib/search.js'
import FollowButton from '../components/FollowButton.jsx'

export function BuyersIndex() {
  const { data, error, loading } = useJson('compradores.json')
  const [sector, setSector] = useState('')
  const [q, setQ] = useState('')
  const rows = useMemo(() => {
    if (!data) return []
    const words = fold(q).split(/\s+/).filter(Boolean)
    return data.filter((b) => (!sector || b.sector === sector) && words.every((w) => fold(b.nombre).includes(w)))
  }, [data, sector, q])
  return (
    <>
      <PageHeader eyebrow="Compradores" title="Quién compra">
        Dependencias y entidades federales en ComprasMX, empresas de CFE y segmentos de PEMEX.
      </PageHeader>
      <div className="mb-4 flex flex-wrap gap-3">
        <label htmlFor="q-comp" className="sr-only">Buscar comprador</label>
        <Input id="q-comp" className="max-w-sm" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nombre o siglas" />
        <label htmlFor="sec-comp" className="sr-only">Sector</label>
        <Select id="sec-comp" className="max-w-[200px]" value={sector} onChange={(e) => setSector(e.target.value)}>
          <option value="">Todos los giros</option>
          <option value="energia">Energía y O&amp;G</option>
        </Select>
      </div>
      {loading && <Loading />}
      {error && <ErrorNote error={error} />}
      {data && (
        <div className="overflow-x-auto rounded-xl border border-line" role="region" aria-label="Compradores" tabIndex={0}>
          <table className="w-full text-sm">
            <thead className="bg-subtle text-left text-xs text-ink-3">
              <tr><th className="px-4 py-2 font-medium">Comprador</th><th className="px-4 py-2 text-right font-medium">Abiertas</th><th className="px-4 py-2 text-right font-medium">Procedimientos</th><th className="px-4 py-2 text-right font-medium">Adjudicado</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.slice(0, 200).map((b) => (
                <tr key={b.id}>
                  <td className="px-4 py-2.5"><Link to={`/comprador/${b.id}`} className="font-medium hover:text-accent">{b.nombre}</Link></td>
                  <td className="num px-4 py-2.5 text-right">{b.abiertas ? formatNumber(b.abiertas) : <span className="text-ink-3">0</span>}</td>
                  <td className="num px-4 py-2.5 text-right text-ink-2">{formatNumber(b.procedimientos)}</td>
                  <td className="num px-4 py-2.5 text-right text-ink-2">{b.adjudicado ? formatMXNShort(b.adjudicado) : 'N/D'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {rows.length > 200 && <p className="eyebrow mt-3">Se muestran 200 de {formatNumber(rows.length)}: busca por nombre o siglas para ver el resto.</p>}
    </>
  )
}

export function Buyer() {
  const { id } = useParams()
  const { data: meta } = useMeta()
  const { data: buyers, error } = useJson('compradores.json')
  const { data: open } = useJson('abiertas.json')
  const b = buyers?.find((x) => x.id === id)
  const openRecs = useMemo(
    () => (open && meta ? toRecords(open, meta.indice_campos).filter((r) => r.comprador_id === id) : []),
    [open, meta, id],
  )
  if (error) return <ErrorNote error={error} />
  if (!buyers || !meta) return <Loading />
  if (!b) return <Empty title="No encontramos este comprador"><Link className="text-accent" to="/compradores">Ver compradores</Link></Empty>
  return (
    <>
      <nav className="mb-4 text-[13px] text-ink-3"><Link to="/compradores" className="hover:text-ink">Compradores</Link> / {b.nombre}</nav>
      <PageHeader
        title={b.nombre}
        actions={(
          <>
            <FollowButton tipo="comprador" id={b.id} nombre={b.nombre} />
            <Button as={Link} size="sm" variant="secondary" to={`/buscar?comprador=${b.id}`}>Buscar en su historial</Button>
          </>
        )}
      />
      <Card className="grid grid-cols-1 gap-6 bg-subtle p-6 min-[370px]:grid-cols-2 sm:grid-cols-3">
        <Stat value={formatNumber(b.abiertas)} label="Convocatorias abiertas" />
        <Stat value={formatNumber(b.procedimientos)} label="Procedimientos registrados" />
        <Stat value={b.adjudicado ? formatMXNShort(b.adjudicado) : 'N/D'} label="Adjudicado" hint={b.id.startsWith('pemex') ? 'PEMEX no publica montos' : undefined} />
      </Card>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section title="Qué compra">
          <div className="flex flex-wrap gap-2">
            {b.categorias.map(([cat, n]) => <Tag key={cat} tone="accent" to={`/buscar?comprador=${b.id}&categoria=${cat}`}>{categoryName(meta, cat)} · {formatNumber(n)}</Tag>)}
          </div>
          {b.entidades.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {b.entidades.map(([e, n]) => <Tag key={e}>{e} · {formatNumber(n)}</Tag>)}
            </div>
          )}
        </Section>
        <Section title="A quién le compra más">
          {b.proveedores.length === 0 ? <p className="text-sm text-ink-3">Sin adjudicaciones con proveedor publicado.</p> : (
            <Card className="divide-y divide-line">
              {b.proveedores.map(([key, name, n]) => (
                <Link key={key} to={`/empresa/${key}`} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm hover:bg-subtle">
                  <span className="min-w-0 [overflow-wrap:anywhere] sm:truncate" title={name}>{name}</span>
                  <span className="num shrink-0 text-ink-3">{formatNumber(n)}</span>
                </Link>
              ))}
            </Card>
          )}
        </Section>
      </div>
      <Section title="Convocatorias abiertas">
        {openRecs.length ? <TenderTable records={openRecs} /> : <Empty title="Sin convocatorias abiertas hoy" />}
      </Section>
    </>
  )
}
