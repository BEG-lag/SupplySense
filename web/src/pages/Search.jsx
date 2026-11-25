import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import CategoryOptions from '../components/CategoryOptions.jsx'
import TenderTable from '../components/TenderTable.jsx'
import { exportCSV } from '../lib/csv.js'
import { loadJson, toRecords } from '../lib/data.js'
import { liveStatus, todayMx } from '../lib/dates.js'
import { buyerName, categoryName, SOURCE_NAMES, useMeta } from '../lib/meta.jsx'
import { useSaved } from '../lib/saved.js'
import { applyFilters, describeFilters, filtersFromParams } from '../lib/search.js'
import { Button, Empty, ErrorNote, Input, Loading, PageHeader, Pagination, Select } from '../ui/index.jsx'

const PAGE = 25

function yearsFor(filters, anio, meta) {
  if (filters.estatus === 'abierta') return []
  const years = meta.anios.filter((y) => y !== '0000')
  if (anio === 'todos') return meta.anios
  if (anio === 'dos') return years.slice(0, 2)
  if (anio) return [anio]
  return years.slice(0, 1)
}

// Archivos del índice para esos años: solo la parte de energía si se filtra ese sector.
function indexFiles(years, sector, meta) {
  const sectors = sector === 'energia' ? ['energia'] : ['energia', 'general']
  const available = new Set(meta.indice_archivos)
  return years.flatMap((y) => sectors.map((sec) => `${y}-${sec}`)).filter((f) => available.has(f))
}

export default function Search() {
  const [params, setParams] = useSearchParams()
  const { data: meta, error: metaError } = useMeta()
  const filters = filtersFromParams(params)
  const anio = params.get('anio') || ''
  const page = Math.max(1, Number(params.get('pagina') || 1))
  const [q, setQ] = useState(filters.q || '')
  const [state, setState] = useState({ records: null, error: null })
  const { save } = useSaved()
  const [savedMsg, setSavedMsg] = useState('')
  const [saveName, setSaveName] = useState(null)

  useEffect(() => setQ(filters.q || ''), [filters.q])

  const years = meta ? yearsFor(filters, anio, meta) : null
  const filesKey = meta && years ? (years.length ? indexFiles(years, filters.sector, meta).join(',') : 'abiertas') : null
  useEffect(() => {
    if (!meta || filesKey == null) return undefined
    let alive = true
    setState({ records: null, error: null })
    const files = filesKey === 'abiertas' ? ['abiertas.json'] : filesKey.split(',').filter(Boolean).map((f) => `indice/${f}.json`)
    Promise.all(files.map(loadJson)).then(
      (chunks) => {
        if (!alive) return
        const records = toRecords(chunks.flat(), meta.indice_campos)
        records.sort((a, b) => (b.publicado || '').localeCompare(a.publicado || '') || (a.id < b.id ? 1 : -1))
        setState({ records, error: null })
      },
      (error) => alive && setState({ records: null, error }),
    )
    return () => { alive = false }
  }, [meta, filesKey])

  const today = todayMx()
  const results = useMemo(
    () => (state.records ? applyFilters(state.records, filters, { buyers: meta?.compradores, today }) : []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [state.records, params.toString()],
  )

  const update = (changes) => {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) {
      if (v) next.set(k, v)
      else next.delete(k)
    }
    if (!('pagina' in changes)) next.delete('pagina')
    setParams(next)
  }

  if (metaError) return <ErrorNote error={metaError} />
  if (!meta) return <Loading />

  const pages = Math.ceil(results.length / PAGE)
  const visible = results.slice((page - 1) * PAGE, page * PAGE)
  const buyersSorted = Object.entries(meta.compradores).sort((a, b) => a[1].localeCompare(b[1], 'es'))

  const doExport = () => exportCSV(results, [
    { label: 'Número', value: (r) => r.numero },
    { label: 'Título', value: (r) => r.titulo },
    { label: 'Fuente', value: (r) => SOURCE_NAMES[r.fuente] },
    { label: 'Comprador', value: (r) => buyerName(meta, r.comprador_id) },
    { label: 'Entidad', value: (r) => r.entidad },
    { label: 'Categoría', value: (r) => categoryName(meta, r.categoria) },
    { label: 'Estatus', value: (r) => meta.estatus[liveStatus(r.estatus, r.apertura, today)] },
    { label: 'Publicación', value: (r) => r.publicado },
    { label: 'Apertura', value: (r) => r.apertura },
    { label: 'Monto adjudicado (MXN)', value: (r) => r.monto },
    { label: 'Ganador', value: (r) => r.ganador },
    { label: 'Liga', value: (r) => `https://beg-lag.github.io/SupplySense/licitacion/${encodeURIComponent(r.id)}` },
  ], `supplysense-${today}`)

  const doSave = (e) => {
    e.preventDefault()
    const nombre = (saveName ?? '').trim() || describeFilters(filters, meta)
    save(nombre, filters)
    setSaveName(null)
    setSavedMsg('Guardada en este navegador. La encuentras en Guardadas.')
    setTimeout(() => setSavedMsg(''), 4000)
  }

  return (
    <>
      <PageHeader eyebrow="Buscar" title={describeFilters(filters, meta)}>
        {state.records ? (
          <span><span className="num">{results.length.toLocaleString('es-MX')}</span> {results.length === 1 ? 'resultado' : 'resultados'}{filters.estatus === 'abierta' ? '' : ` en ${years.length > 2 ? 'todos los años' : years.join(' y ')}`}.</span>
        ) : 'Cargando…'}
      </PageHeader>

      <form
        className="mb-4 flex gap-2"
        role="search"
        onSubmit={(e) => { e.preventDefault(); update({ q }) }}
      >
        <label htmlFor="q-buscar" className="sr-only">Palabras</label>
        <Input id="q-buscar" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Palabras, número de procedimiento, empresa…" />
        <Button type="submit">Buscar</Button>
      </form>

      <div className="grid gap-6 lg:grid-cols-[230px_1fr]">
        <aside className="grid grid-cols-2 content-start gap-3 sm:grid-cols-3 lg:grid-cols-1" aria-label="Filtros">
          <Filter label="Sector" value={filters.sector} onChange={(v) => update({ sector: v })}>
            <option value="">Todos los giros</option>
            <option value="energia">Energía y O&amp;G</option>
          </Filter>
          <Filter label="Estatus" value={filters.estatus} onChange={(v) => update({ estatus: v })}>
            <option value="">Todos</option>
            {['abierta', 'en_evaluacion', 'adjudicada', 'desierta', 'cancelada', 'aviso'].map((s) => <option key={s} value={s}>{meta.estatus[s]}</option>)}
          </Filter>
          <Filter label="Fuente" value={filters.fuente} onChange={(v) => update({ fuente: v })}>
            <option value="">Todas</option>
            {Object.entries(SOURCE_NAMES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Filter>
          <Filter label="Categoría" value={filters.categoria} onChange={(v) => update({ categoria: v })}>
            <option value="">Todas</option>
            <CategoryOptions meta={meta} />
          </Filter>
          <Filter label="Comprador" value={filters.comprador} onChange={(v) => update({ comprador: v })}>
            <option value="">Todos</option>
            {buyersSorted.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </Filter>
          <Filter label="Entidad" value={filters.entidad} onChange={(v) => update({ entidad: v })}>
            <option value="">Todas</option>
            {meta.entidades.map((e) => <option key={e} value={e}>{e}</option>)}
          </Filter>
          {filters.estatus !== 'abierta' && (
            <Filter label="Año de publicación" value={anio} onChange={(v) => update({ anio: v })}>
              <option value="">Año en curso</option>
              <option value="dos">Últimos dos</option>
              {meta.anios.filter((y) => y !== '0000').map((y) => <option key={y} value={y}>{y}</option>)}
              <option value="todos">Todos (más lento)</option>
            </Filter>
          )}
          <div className="col-span-full flex flex-wrap gap-2 pt-1 lg:flex-col">
            <Button variant="secondary" size="sm" onClick={() => setSaveName(describeFilters(filters, meta))}>Guardar búsqueda</Button>
            <Button variant="secondary" size="sm" onClick={doExport} disabled={!results.length}>Exportar CSV</Button>
            {Object.keys(filters).length > 0 && <Button variant="ghost" size="sm" onClick={() => setParams(new URLSearchParams())}>Limpiar filtros</Button>}
          </div>
          {saveName != null && (
            <form onSubmit={doSave} className="col-span-full flex flex-col gap-2 rounded-lg border border-line p-3">
              <label htmlFor="nombre-guardada" className="text-xs text-ink-3">Nombre de la búsqueda</label>
              <Input id="nombre-guardada" autoFocus value={saveName} onChange={(e) => setSaveName(e.target.value)} />
              <div className="flex gap-2">
                <Button type="submit" size="sm">Guardar</Button>
                <Button type="button" variant="ghost" size="sm" onClick={() => setSaveName(null)}>Cancelar</Button>
              </div>
            </form>
          )}
          {savedMsg && <p className="col-span-full text-xs text-accent" role="status">{savedMsg}</p>}
        </aside>

        <div className="min-w-0">
          {state.error && <ErrorNote error={state.error} />}
          {!state.records && !state.error && <Loading />}
          {state.records && results.length === 0 && (
            <Empty title="Sin resultados">Prueba con otras palabras o quita algún filtro.</Empty>
          )}
          {results.length > 0 && (
            <>
              <TenderTable records={visible} showWinner={filters.estatus === 'adjudicada'} />
              <Pagination page={page} pages={pages} onPage={(p) => { update({ pagina: String(p) }); window.scrollTo(0, 0) }} />
            </>
          )}
        </div>
      </div>
    </>
  )
}

function Filter({ label, value, onChange, children }) {
  const id = `f-${label}`
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs text-ink-3">{label}</label>
      <Select id={id} value={value || ''} onChange={(e) => onChange(e.target.value)}>{children}</Select>
    </div>
  )
}
