import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import TenderTable from '../components/TenderTable.jsx'
import { toRecords, useJson } from '../lib/data.js'
import { formatDate, formatMXNShort, formatNumber } from '../lib/format.js'
import { useMeta } from '../lib/meta.jsx'
import { Button, Card, ErrorNote, Loading, Section, Stat } from '../ui/index.jsx'

const EXAMPLES = ['válvulas', 'transformadores', 'grúas', 'mantenimiento de bombas', 'diésel', 'tubería']

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
          <span className="text-accent">{formatNumber(meta.totales.abiertas)}</span> convocatorias abiertas · CFE, PEMEX y ComprasMX
        </p>
      )}
      <h1 className="text-[38px] leading-[1] tracking-[-0.05em] sm:text-[60px]">
        Licitaciones de energía y O&amp;G, con <em>lo que ya se pagó</em> por lo mismo
      </h1>
      <p className="mx-auto mt-4 max-w-2xl text-[16px] leading-relaxed text-ink-2 sm:text-[17px]">
        Cada mañana reunimos las convocatorias abiertas de CFE, PEMEX y el sector energía, y las
        cruzamos con diez años de adjudicaciones: quién ganó, a qué precio y para qué comprador.
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
          placeholder="¿Qué vendes? Ej. válvulas de compuerta"
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

      {topCats.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-2">
          {topCats.map((c) => (
            <Link key={c.codigo} to={`/buscar?estatus=abierta&categoria=${c.codigo}`} className="rounded-full border border-line px-3 py-1 text-[13px] text-ink-2 hover:border-accent hover:text-accent">
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
            ['Encontrar convocatorias', 'Busca por lo que vendes en CFE, PEMEX, CENAGAS, CENACE, IMP y el resto del sector. Filtra por estado, categoría y comprador.', '/buscar?estatus=abierta', 'Buscar'],
            ['Saber cuánto se ha pagado', 'Percentiles de precio por categoría con más de 90 mil adjudicaciones, y un comparador para ver dónde cae tu monto.', '/precios', 'Ver precios'],
            ['Ver quién gana', 'Ganadores recientes, empresas con más contratos y concentración de cada mercado.', '/ganadores', 'Ver ganadores'],
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
