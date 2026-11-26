import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { loadCompany, useJson } from '../lib/data.js'
import { formatDate, formatMXN, formatMXNShort, formatNumber } from '../lib/format.js'
import { buyerName, categoryName, SOURCE_NAMES, useMeta } from '../lib/meta.jsx'
import { fold } from '../lib/search.js'
import { Card, Empty, ErrorNote, Input, Loading, PageHeader, Pagination, Section, Stat, Tag } from '../ui/index.jsx'
import { displayTitle } from '../lib/text.js'
import FollowButton from '../components/FollowButton.jsx'

const PAGE = 40

export function CompaniesIndex() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') || ''
  const { data: meta } = useMeta()
  const { data, error, loading } = useJson('empresas.json')
  const [page, setPage] = useState(1)
  const rows = useMemo(() => {
    if (!data) return []
    const words = fold(q).split(/\s+/).filter(Boolean)
    return words.length ? data.filter((r) => words.every((w) => fold(r[1]).includes(w))) : data
  }, [data, q])
  useEffect(() => setPage(1), [q])
  return (
    <>
      <PageHeader eyebrow="Empresas" title="Empresas que le venden al sector energía">
        {data && <><span className="num">{formatNumber(data.length)}</span> empresas con adjudicaciones de CFE o del sector en ComprasMX, ordenadas por monto.</>}
      </PageHeader>
      <div className="mb-4 max-w-md">
        <label htmlFor="q-emp" className="sr-only">Buscar empresa</label>
        <Input id="q-emp" value={q} onChange={(e) => setParams(e.target.value ? { q: e.target.value } : {})} placeholder="Nombre de la empresa" />
      </div>
      {loading && <Loading />}
      {error && <ErrorNote error={error} />}
      {data && rows.length === 0 && <Empty title="Sin coincidencias" />}
      {rows.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-xl border border-line" role="region" aria-label="Empresas" tabIndex={0}>
            <table className="w-full text-sm">
              <thead className="bg-subtle text-left text-xs text-ink-3">
                <tr><th className="px-4 py-2 font-medium">Empresa</th><th className="px-4 py-2 font-medium">Categoría principal</th><th className="px-4 py-2 text-right font-medium">Adjudicaciones</th><th className="px-4 py-2 text-right font-medium">Monto</th></tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.slice((page - 1) * PAGE, page * PAGE).map(([id, nombre, n, monto, cat]) => (
                  <tr key={id}>
                    <td className="px-4 py-2.5"><Link to={`/empresa/${id}`} className="font-medium hover:text-accent">{nombre}</Link></td>
                    <td className="px-4 py-2.5 text-ink-2">{categoryName(meta, cat)}</td>
                    <td className="num px-4 py-2.5 text-right">{formatNumber(n)}</td>
                    <td className="num px-4 py-2.5 text-right">{formatMXNShort(monto)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pages={Math.ceil(rows.length / PAGE)} onPage={(p) => { setPage(p); window.scrollTo(0, 0) }} />
        </>
      )}
    </>
  )
}

export function Company() {
  const { id } = useParams()
  const { data: meta } = useMeta()
  const [state, setState] = useState({ rec: undefined })
  useEffect(() => {
    let alive = true
    setState({ rec: undefined })
    loadCompany(id).then((rec) => alive && setState({ rec }), () => alive && setState({ rec: null }))
    return () => { alive = false }
  }, [id])
  if (state.rec === undefined || !meta) return <Loading />
  if (!state.rec) return <Empty title="No encontramos esta empresa"><Link className="text-accent" to="/empresas">Ver empresas</Link></Empty>
  const c = state.rec
  return (
    <>
      <nav className="mb-4 text-[13px] text-ink-3"><Link to="/empresas" className="hover:text-ink">Empresas</Link> / {c.nombre}</nav>
      <PageHeader title={c.nombre} actions={<FollowButton tipo="empresa" id={c.id} nombre={c.nombre} snapshot={{ n: c.n }} />}>
        {c.rfc && <span className="num mr-3">RFC {c.rfc}</span>}
        {c.otros_nombres.length > 0 && <span className="text-ink-3">También aparece como {c.otros_nombres.join(', ')}</span>}
      </PageHeader>
      <Card className="grid grid-cols-1 gap-6 bg-subtle p-6 min-[370px]:grid-cols-2 sm:grid-cols-3">
        <Stat value={formatNumber(c.n)} label="Adjudicaciones" />
        <Stat value={formatMXNShort(c.monto)} label="Monto adjudicado" hint="Compartidas, en partes iguales" />
        <Stat value={c.adjudicaciones[0] ? formatDate(c.adjudicaciones[0].fecha) : 'N/D'} label="Última adjudicación" />
      </Card>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section title="Categorías">
          <div className="flex flex-wrap gap-2">
            {c.categorias.map(([cat, n]) => <Tag key={cat} tone="accent" to={`/precios/${cat}`}>{categoryName(meta, cat)} · {n}</Tag>)}
          </div>
        </Section>
        <Section title="Le vende a">
          <div className="flex flex-wrap gap-2">
            {c.compradores.map(([b, n]) => <Tag key={b} to={`/comprador/${b}`}>{buyerName(meta, b)} · {n}</Tag>)}
          </div>
        </Section>
      </div>
      <Section title="Adjudicaciones">
        <div className="overflow-x-auto rounded-xl border border-line" role="region" aria-label="Adjudicaciones de la empresa" tabIndex={0}>
          <table className="w-full text-sm">
            <thead className="bg-subtle text-left text-xs text-ink-3">
              <tr><th className="px-4 py-2 font-medium">Procedimiento</th><th className="px-4 py-2 font-medium">Fecha</th><th className="px-4 py-2 text-right font-medium">Monto</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {c.adjudicaciones.map((a) => (
                <tr key={a.id} className="align-top">
                  <td className="max-w-xl px-4 py-2.5">
                    <Link to={`/licitacion/${encodeURIComponent(a.procedimiento_id || a.id)}`} className="hover:text-accent">{displayTitle(a.titulo)}</Link>
                    <div className="text-xs text-ink-3">{buyerName(meta, a.comprador_id)} · {SOURCE_NAMES[a.fuente]}{a.compartida ? ' · compartida' : ''}</div>
                  </td>
                  <td className="num whitespace-nowrap px-4 py-2.5 text-ink-2">{formatDate(a.fecha)}</td>
                  <td className="num whitespace-nowrap px-4 py-2.5 text-right">{formatMXN(a.monto_mxn)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {c.n > c.adjudicaciones.length && <p className="mt-2 text-xs text-ink-3">Se muestran las {c.adjudicaciones.length} más recientes de {formatNumber(c.n)}.</p>}
      </Section>
    </>
  )
}
