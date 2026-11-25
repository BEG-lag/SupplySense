import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import TenderTable from '../components/TenderTable.jsx'
import { toRecords, useJson } from '../lib/data.js'
import { formatDate, formatMXNShort, formatNumber } from '../lib/format.js'
import { useMeta } from '../lib/meta.jsx'
import { Button, Card, ErrorNote, Loading, Section, Stat } from '../ui/index.jsx'

const EXAMPLES = ['medicamentos', 'limpieza', 'vehículos', 'válvulas', 'transformadores', 'construcción', 'equipo de cómputo']

function SearchHero({ meta }) {
  const [q, setQ] = useState('')
  const navigate = useNavigate()
  const go = (text) => {
    const params = new URLSearchParams({ estatus: 'abierta' })
    if (text.trim()) params.set('q', text.trim())
    navigate(`/buscar?${params}`)
  }
  return (
    <div className="mx-auto max-w-3xl py-6 text-center sm:py-10">
      {meta && (
        <p className="eyebrow mx-auto mb-7 inline-flex items-center gap-2.5 rounded-full border border-line px-3.5 py-1.5">
          <span className="live" aria-hidden />
          <span className="text-accent">{formatNumber(meta.totales.abiertas)}</span> convocatorias abiertas · ComprasMX, CFE, PEMEX y 3 estados
        </p>
      )}
      <h1 className="text-[38px] leading-[1] tracking-[-0.05em] sm:text-[60px]">
        Licitaciones del gobierno, con <em>lo que ya se pagó</em> por lo mismo
      </h1>
      <p className="mx-auto mt-4 max-w-2xl text-[16px] leading-relaxed text-ink-2 sm:text-[17px]">
        Cada mañana reunimos las convocatorias abiertas de todo el gobierno federal en ComprasMX,
        más CFE, PEMEX y los portales de Jalisco, CDMX y Campeche, y las cruzamos con más de 300
        mil adjudicaciones: quién ganó, a qué precio y para qué comprador.
      </p>
      <form
        className="mx-auto mt-7 flex max-w-xl gap-2"
        onSubmit={(e) => { e.preventDefault(); go(q) }}
        role="search"
      >
        <label htmlFor="q-home" className="sr-only">¿Qué vendes o qué buscas?</label>
        <input
          id="q-home"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="¿Qué vendes? Ej. material de curación"
          className="h-12 min-w-0 flex-1 rounded-full border border-line-strong bg-subtle px-5 text-[15px] text-ink placeholder:text-ink-3 focus:border-accent focus:outline-none"
        />
        <Button type="submit" size="lg">Buscar</Button>
      </form>
      <div className="mt-4 flex flex-wrap items-center justify-center gap-1.5 text-[13px] text-ink-3">
        <span className="eyebrow">Prueba</span>
        {EXAMPLES.map((ex) => (
          <button key={ex} type="button" onClick={() => go(ex)} className="rounded-full border border-line px-2.5 py-0.5 text-ink-2 hover:border-accent hover:text-accent">
            {ex}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function Home() {
  const { data: meta, error: metaError } = useMeta()
  const { data: rows, error, loading } = useJson('abiertas.json')
  const recent = useMemo(
    () => (rows && meta ? toRecords(rows.slice(0, 10), meta.indice_campos) : []),
    [rows, meta],
  )
  const topCats = useMemo(
    () => (meta ? [...meta.categorias].filter((c) => c.abiertas > 0 && c.codigo !== 'otros')
      .sort((a, b) => b.abiertas - a.abiertas).slice(0, 8) : []),
    [meta],
  )
  if (metaError) return <ErrorNote error={metaError} />

  return (
    <>
      <SearchHero meta={meta} />

      {meta && (
        <Card className="grid grid-cols-2 gap-6 bg-subtle p-6 sm:grid-cols-4">
          <Stat value={formatNumber(meta.totales.abiertas)} label="Convocatorias abiertas" />
          <Stat value={formatNumber(meta.totales.nuevas_hoy)} label="Nuevas hoy" />
          <Stat value={formatNumber(meta.totales.cierran_48h)} label="Abren propuestas en 48 h" hint="Donde la fuente publica la fecha" />
          <Stat value={formatMXNShort(meta.totales.monto_adjudicado_12m)} label="Adjudicado en 12 meses" hint="CFE y ComprasMX" />
        </Card>
      )}

      {meta && (
        <Card className="mt-6 grid gap-5 p-6 sm:grid-cols-[1.3fr_1fr] sm:items-center">
          <div>
            <p className="eyebrow mb-2 flex items-center gap-2"><span className="lights" aria-hidden><i /><i /><i /></span> Vertical destacada</p>
            <h2 className="text-2xl tracking-[-0.04em]">Energía y O&amp;G</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-2">
              CFE y PEMEX no publican en ComprasMX: los leemos directo de sus portales y los
              cruzamos con diez años de adjudicaciones de CFE, más CENACE, CENAGAS, IMP y SENER.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:items-end">
            <div className="flex gap-6">
              <Stat value={formatNumber(meta.sectores.energia.abiertas)} label="Abiertas en energía" />
              <Stat value={formatNumber(meta.sectores.energia.procedimientos)} label="Procedimientos" />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button as={Link} size="sm" to="/buscar?sector=energia&estatus=abierta">Ver convocatorias</Button>
              <Button as={Link} size="sm" variant="secondary" to="/precios#energia">Precios del sector</Button>
            </div>
          </div>
        </Card>
      )}

      {topCats.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-2">
          {topCats.map((c) => (
            <Link key={c.codigo} to={`/giro/${c.codigo}`} className="rounded-full border border-line px-3 py-1 text-[13px] text-ink-2 hover:border-accent hover:text-accent">
              {c.nombre} <span className="num text-ink-3">{c.abiertas}</span>
            </Link>
          ))}
        </div>
      )}

      <Section
        title="Recién publicadas"
        aside={<Link to="/buscar?estatus=abierta" className="text-sm text-accent hover:underline">Ver todas</Link>}
      >
        {loading && <Loading />}
        {error && <ErrorNote error={error} />}
        {!loading && !error && <TenderTable records={recent} />}
      </Section>

      <Section title="Qué puedes hacer">
        <div className="grid gap-4 md:grid-cols-3">
          {[
            ['Encontrar convocatorias', 'Busca por lo que vendes en más de 800 dependencias federales, CFE y PEMEX. Filtra por estado, categoría, comprador y sector.', '/buscar?estatus=abierta', 'Buscar'],
            ['Saber cuánto se ha pagado', 'Percentiles de precio en 35 categorías con más de 300 mil adjudicaciones, y un comparador para ver dónde cae tu monto.', '/precios', 'Ver precios'],
            ['Ver quién gana', 'Ganadores recientes, 60 mil empresas con su historial y la concentración de cada mercado.', '/ganadores', 'Ver ganadores'],
          ].map(([title, text, to, cta]) => (
            <Card key={title} className="flex flex-col p-5">
              <h3 className="font-semibold">{title}</h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-ink-2">{text}</p>
              <Link to={to} className="mt-4 text-sm font-medium text-accent hover:underline">{cta}</Link>
            </Card>
          ))}
        </div>
      </Section>

      {meta && (
        <Section title="Fuentes de hoy" aside={<Link to="/fuentes" className="text-sm text-accent hover:underline">Cómo se arma</Link>}>
          <div className="grid gap-3 sm:grid-cols-3">
            {Object.entries(meta.fuentes).map(([key, f]) => (
              <Card key={key} className="p-4 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{f.nombre}</span>
                  <span className="text-xs" style={{ color: f.falla_desde ? 'var(--danger)' : 'var(--open)' }}>
                    {f.falla_desde ? `Sin leer desde ${formatDate(f.falla_desde)}` : `Leída ${formatDate(f.ultima_ok)}`}
                  </span>
                </div>
                <div className="mt-2 text-ink-2">
                  <span className="num">{formatNumber(f.abiertas)}</span> abiertas · <span className="num">{formatNumber(f.procedimientos)}</span> en total
                </div>
              </Card>
            ))}
          </div>
        </Section>
      )}
    </>
  )
}
