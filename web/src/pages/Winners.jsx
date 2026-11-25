import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useJson } from '../lib/data.js'
import { formatDate, formatMXNShort } from '../lib/format.js'
import { buyerName, categoryName, SOURCE_NAMES, useMeta } from '../lib/meta.jsx'
import { Card, ErrorNote, Loading, PageHeader, Pagination, Section, Select, Tag } from '../ui/index.jsx'
import { displayTitle } from '../lib/text.js'

const PAGE = 30

export default function Winners() {
  const { data: meta } = useMeta()
  const { data, error, loading } = useJson('ganadores.json')
  const [categoria, setCategoria] = useState('')
  const [page, setPage] = useState(1)
  const rows = useMemo(
    () => (data ? data.recientes.filter((a) => !categoria || a.categoria === categoria) : []),
    [data, categoria],
  )
  if (loading || !meta) return <Loading />
  if (error) return <ErrorNote error={error} />
  const visible = rows.slice((page - 1) * PAGE, page * PAGE)
  return (
    <>
      <PageHeader eyebrow="Ganadores" title="Quién acaba de ganar en el sector energía">
        Las adjudicaciones más recientes de CFE y del sector energía en ComprasMX, con monto y
        comprador. Cada empresa tiene su historial.
      </PageHeader>
      <div className="grid gap-8 lg:grid-cols-[1fr_300px]">
        <div className="min-w-0">
          <div className="mb-3 flex items-center gap-3">
            <label htmlFor="cat-g" className="text-sm text-ink-3">Categoría</label>
            <Select id="cat-g" className="max-w-xs" value={categoria} onChange={(e) => { setCategoria(e.target.value); setPage(1) }}>
              <option value="">Todas</option>
              {meta.categorias.map((c) => <option key={c.codigo} value={c.codigo}>{c.nombre}</option>)}
            </Select>
          </div>
          <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line">
            {visible.map((a) => (
              <li key={a.id} className="px-4 py-3.5">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
                  <div className="min-w-0">
                    <div className="flex flex-wrap gap-x-2 text-[15px] font-medium">
                      {a.ganadores.slice(0, 3).map((g, i) => (
                        <Link key={g} to={`/empresa/${a.empresas[i]}`} className="hover:text-accent">{g}{i < Math.min(a.ganadores.length, 3) - 1 ? ',' : ''}</Link>
                      ))}
                      {a.ganadores.length > 3 && <span className="text-ink-3">y {a.ganadores.length - 3} más</span>}
                    </div>
                    <Link to={`/licitacion/${encodeURIComponent(a.procedimiento_id || a.id)}`} className="mt-0.5 block text-sm text-ink-2 hover:text-accent">Ganó: {displayTitle(a.titulo)}</Link>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-ink-3">
                      <span>{buyerName(meta, a.comprador_id)}</span>
                      {a.entidad && <span>· {a.entidad}</span>}
                      <span>· {SOURCE_NAMES[a.fuente]}</span>
                      <Tag tone="accent">{categoryName(meta, a.categoria)}</Tag>
                    </div>
                  </div>
                  <div className="shrink-0 text-left sm:text-right">
                    <div className="num font-medium">{formatMXNShort(a.monto_mxn)}</div>
                    <div className="num text-xs text-ink-3">{formatDate(a.fecha)}</div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          <Pagination page={page} pages={Math.ceil(rows.length / PAGE)} onPage={(p) => { setPage(p); window.scrollTo(0, 0) }} />
        </div>
        <aside>
          <Section title="Más adjudicado en 12 meses" className="mt-0">
            <Card className="divide-y divide-line">
              {data.top_anual.slice(0, 15).map((c, i) => (
                <Link key={c.id} to={`/empresa/${c.id}`} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm hover:bg-subtle">
                  <span className="min-w-0 truncate"><span className="num mr-2 text-ink-3">{i + 1}</span>{c.nombre}</span>
                  <span className="num shrink-0 text-ink-2">{formatMXNShort(c.monto)}</span>
                </Link>
              ))}
            </Card>
            <p className="mt-2 text-xs text-ink-3">Cuando varias empresas ganan un mismo procedimiento, el monto se reparte en partes iguales.</p>
          </Section>
        </aside>
      </div>
    </>
  )
}
