import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import TenderTable from '../components/TenderTable.jsx'
import { toRecords, useJson } from '../lib/data.js'
import { formatMXNShort, formatNumber } from '../lib/format.js'
import { categoryName, useMeta } from '../lib/meta.jsx'
import { Card, Empty, ErrorNote, Loading, PageHeader, Section, Stat, Tag } from '../ui/index.jsx'

export function BuyersIndex() {
  const { data, error, loading } = useJson('compradores.json')
  return (
    <>
      <PageHeader eyebrow="Compradores" title="Quién compra en el sector energía">
        Empresas de CFE, segmentos de PEMEX y dependencias del sector en ComprasMX.
      </PageHeader>
      {loading && <Loading />}
      {error && <ErrorNote error={error} />}
      {data && (
        <div className="overflow-x-auto rounded-xl border border-line">
          <table className="w-full text-sm">
            <thead className="bg-subtle text-left text-xs text-ink-3">
              <tr><th className="px-4 py-2 font-medium">Comprador</th><th className="px-4 py-2 text-right font-medium">Abiertas</th><th className="px-4 py-2 text-right font-medium">Procedimientos</th><th className="px-4 py-2 text-right font-medium">Adjudicado</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {data.map((b) => (
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
      <PageHeader title={b.nombre} actions={<Link to={`/buscar?comprador=${b.id}`} className="text-sm text-accent hover:underline">Buscar en su historial</Link>} />
      <Card className="grid grid-cols-2 gap-6 bg-subtle p-6 sm:grid-cols-3">
        <Stat value={formatNumber(b.abiertas)} label="Convocatorias abiertas" />
        <Stat value={formatNumber(b.procedimientos)} label="Procedimientos registrados" />
        <Stat value={b.adjudicado ? formatMXNShort(b.adjudicado) : 'N/D'} label="Adjudicado" hint={b.id.startsWith('pemex') ? 'PEMEX no publica montos' : undefined} />
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
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
                  <span className="min-w-0 truncate">{name}</span>
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
