import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PriceRange from '../components/PriceRange.jsx'
import { loadDetail, useJson } from '../lib/data.js'
import { closingLabel, liveStatus, todayMx } from '../lib/dates.js'
import { formatDate, formatDateTime, formatMXN, formatMXNShort } from '../lib/format.js'
import { buyerName, categoryName, SOURCE_NAMES, useMeta } from '../lib/meta.jsx'
import { describePercentile, percentileOf } from '../lib/prices.js'
import { Button, Card, Empty, Loading, Section, StatusBadge, Tag } from '../ui/index.jsx'
import { displayTitle } from '../lib/text.js'
import FollowButton from '../components/FollowButton.jsx'
import Legal from '../components/Legal.jsx'

function Fact({ label, children }) {
  if (children == null || children === '' || children === false) return null
  return (
    <div className="border-b border-line py-3 sm:grid sm:grid-cols-[200px_1fr] sm:gap-4">
      <dt className="text-[13px] text-ink-3">{label}</dt>
      <dd className="mt-0.5 text-[15px] sm:mt-0">{children}</dd>
    </div>
  )
}

const CFE_URL = 'https://msc.cfe.mx/Aplicaciones/NCFE/Concursos/'
const CMX_URL = (id) => `https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/detalle/${id}/procedimiento`

function officialUrl(rec) {
  if (rec.fuente === 'cfe') return CFE_URL
  if (rec.anuncio) return CMX_URL(rec.anuncio)
  return rec.url || null
}

function OfficialLink({ rec }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard?.writeText(rec.numero).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })
  }
  const label = {
    cfe: 'Abrir el buscador de CFE',
    pemex: 'Ver en el portal de PEMEX',
    comprasmx: 'Ver en ComprasMX',
    jalisco: 'Ver en Compras Jalisco',
    cdmx: 'Ver en Concurso Digital CDMX',
    campeche: 'Descargar la convocatoria (PDF)',
    guanajuato: rec.url?.toLowerCase().endsWith('.pdf') ? 'Descargar la convocatoria (PDF)' : 'Ver en el portal de Guanajuato',
    nuevo_leon: 'Ver la subasta en Nuevo León',
    banxico: 'Abrir el Portal de Proveedores de Banxico',
    oaj: 'Ver la convocatoria del OAJ',
    dof: 'Ver el resumen en el DOF',
  }[rec.fuente]
  const url = officialUrl(rec)
  return (
    <div className="flex flex-wrap items-center gap-2">
      {url && <Button as="a" href={url} target="_blank" rel="noreferrer">{label}</Button>}
      {rec.fuente !== 'comprasmx' && (
        <Button variant="secondary" onClick={copy}>{copied ? 'Número copiado' : 'Copiar número'}</Button>
      )}
    </div>
  )
}

function PriceContext({ rec, meta }) {
  const { data: prices } = useJson(rec.categoria ? `precios/${rec.categoria}.json` : null)
  if (!prices?.percentiles) return null
  const pct = rec.monto ? percentileOf(rec.monto, prices.percentiles) : null
  return (
    <Section title={`Cuánto se ha pagado en ${categoryName(meta, rec.categoria).toLowerCase()}`}
      aside={<Link to={`/precios/${rec.categoria}`} className="text-sm text-accent hover:underline">Ver la categoría</Link>}>
      <Card className="p-5">
        <p className="text-sm text-ink-2">
          Monto adjudicado por procedimiento o contrato en los últimos 36 meses,{' '}
          <span className="num">{prices.n.toLocaleString('es-MX')}</span> adjudicaciones (CFE y ComprasMX, sin montos atípicos).
        </p>
        <PriceRange percentiles={prices.percentiles} mark={rec.monto} markLabel="Esta adjudicación" />
        {pct && <p className="mt-3 text-sm">{describePercentile(pct)} de la categoría.</p>}
      </Card>
    </Section>
  )
}

export default function Tender() {
  const { id } = useParams()
  const { data: meta } = useMeta()
  const [state, setState] = useState({ rec: undefined, error: null })

  useEffect(() => {
    let alive = true
    setState({ rec: undefined, error: null })
    loadDetail(id).then((rec) => alive && setState({ rec, error: null }), (error) => alive && setState({ rec: null, error }))
    return () => { alive = false }
  }, [id])

  if (state.rec === undefined || !meta) return <Loading />
  if (!state.rec) return <Empty title="No encontramos esta licitación">Puede que la fuente la haya retirado. <Link className="text-accent" to="/buscar">Volver a buscar</Link></Empty>

  const rec = state.rec
  const today = todayMx()
  const status = rec.tipo === 'contrato' ? null : liveStatus(rec.estatus, rec.apertura, today)
  const closing = status === 'abierta' ? closingLabel(rec.apertura, today) : null
  const winners = rec.ganadores
    ? rec.ganadores.map((name, i) => [name, rec.ganadores_ids?.[i]])
    : rec.proveedor ? [[rec.proveedor, rec.proveedor_id]] : []
  document.title = `${displayTitle(rec.titulo).slice(0, 70)} · SupplySense`

  return (
    <>
      <nav className="mb-4 text-[13px] text-ink-3" aria-label="Ruta">
        <Link to="/buscar" className="hover:text-ink">Buscar</Link> / <span>{SOURCE_NAMES[rec.fuente]}</span> / <span className="num">{rec.numero || rec.numero_contrato}</span>
      </nav>
      <div className="flex flex-wrap items-center gap-2">
        {status && <StatusBadge status={status} label={meta.estatus[status]} estimated={rec.estatus_estimado} />}
        {rec.tipo === 'contrato' && <Tag>Contrato</Tag>}
        <Tag tone="accent" to={`/precios/${rec.categoria}`}>{categoryName(meta, rec.categoria)}</Tag>
        {closing && <Tag tone="warn">{closing}</Tag>}
      </div>
      <h1 className="mt-3 max-w-4xl text-[24px] font-semibold leading-snug tracking-[-0.02em] [overflow-wrap:anywhere] sm:text-[30px]">{displayTitle(rec.titulo)}</h1>
      {rec.descripcion && <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-ink-2 [overflow-wrap:anywhere]">{displayTitle(rec.descripcion)}</p>}
      <div className="mt-5 flex flex-wrap items-center gap-2">
        <OfficialLink rec={rec} />
        <FollowButton tipo="licitacion" id={rec.id} nombre={rec.titulo} snapshot={{ estatus: status }} />
      </div>

      {rec.fuente === 'pemex' && (
        <p className="mt-4 max-w-3xl rounded-lg bg-subtle p-3 text-[13px] text-ink-2">
          * PEMEX no publica en datos abiertos la fecha límite del concurso. Lo marcamos como abierto
          durante {meta.pemex_dias_abierta} días desde su publicación; confirma fechas y bases en el portal de PEMEX
          o en SISCeP{rec.siscep ? ` (evento ${rec.siscep})` : ''}.
        </p>
      )}

      <Section title="Datos del procedimiento" className="mt-8">
        <dl className="border-t border-line">
          <Fact label="Comprador"><Link className="hover:text-accent" to={`/comprador/${rec.comprador_id}`}>{rec.comprador_nombre || buyerName(meta, rec.comprador_id)}</Link></Fact>
          <Fact label="Unidad o área">{rec.unidad}</Fact>
          <Fact label="Entidad">{rec.entidad}</Fact>
          <Fact label="Número"><span className="num">{rec.numero || rec.numero_contrato}</span></Fact>
          <Fact label="Tipo de procedimiento">{rec.tipo_procedimiento}</Fact>
          <Fact label="Tipo de contratación">{rec.tipo_contratacion}</Fact>
          <Fact label="Carácter">{rec.caracter}</Fact>
          <Fact label="Publicación">{rec.publicado && formatDateTime(rec.publicado)}</Fact>
          <Fact label="Firma del contrato">{rec.firma && formatDate(rec.firma)}</Fact>
          <Fact label="Vigencia">{rec.inicio && `${formatDate(rec.inicio)} a ${formatDate(rec.fin)}`}</Fact>
          <Fact label={winners.length > 1 ? 'Ganadores' : 'Ganador'}>
            {winners.length > 0 && (
              <span className="flex flex-col gap-1">
                {winners.map(([name, key]) => (key
                  ? <Link key={name} className="hover:text-accent" to={`/empresa/${key}`}>{name}</Link>
                  : <span key={name}>{name}</span>))}
              </span>
            )}
          </Fact>
          <Fact label="RFC del proveedor">{rec.proveedor_rfc && <span className="num">{rec.proveedor_rfc}</span>}</Fact>
          <Fact label="Monto adjudicado">{rec.monto && <span className="num">{formatMXN(rec.monto)}{rec.moneda && rec.moneda !== 'MXN' ? ` ${rec.moneda}` : ''}</span>}</Fact>
          <Fact label="Precio base de la subasta">{rec.precio_base && <span className="num">{formatMXN(rec.precio_base)}{rec.monto ? ` · se adjudicó ${((1 - rec.monto / rec.precio_base) * 100).toFixed(1)}% abajo` : ''}</span>}</Fact>
          <Fact label="Participantes">{rec.participantes?.length > 0 && <span>{rec.participantes.length}: {rec.participantes.join(', ')}</span>}</Fact>
          <Fact label="Testigo social">{rec.testigo_social ? 'Sí' : null}</Fact>
          <Fact label="Sector">{rec.sector === 'energia' ? `Energía y O&G (${(rec.motivo_alcance || '').replace('comprador:', 'comprador del sector: ').replace('palabra:', 'palabra de contexto: ')})` : 'General'}</Fact>
          <Fact label="Fuente">{SOURCE_NAMES[rec.fuente]} · visto por primera vez el {formatDate(rec.primera_vez)}</Fact>
        </dl>
      </Section>

      <Legal rec={rec} />

      <PriceContext rec={rec} meta={meta} />

      {rec.similares?.length > 0 && (
        <Section title="Procedimientos parecidos ya adjudicados">
          <div className="overflow-hidden rounded-xl border border-line">
            <ul className="divide-y divide-line">
              {rec.similares.map((s) => (
                <li key={s.id} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
                  <div className="min-w-0 [overflow-wrap:anywhere]">
                    <Link to={`/licitacion/${encodeURIComponent(s.procedimiento_id || s.id)}`} className="text-sm font-medium hover:text-accent">{displayTitle(s.titulo)}</Link>
                    <div className="mt-0.5 text-xs text-ink-2">
                      {s.ganadores.slice(0, 2).join(', ')}{s.ganadores.length > 2 ? ` y ${s.ganadores.length - 2} más` : ''} · {buyerName(meta, s.comprador_id)} · {formatDate(s.fecha)}
                    </div>
                  </div>
                  <div className="num shrink-0 text-sm font-medium">{formatMXNShort(s.monto_mxn)}</div>
                </li>
              ))}
            </ul>
          </div>
        </Section>
      )}

      {rec.contratos?.length > 0 && (
        <Section
          title="Contratos de este procedimiento"
          aside={rec.contratos_total ? <span className="eyebrow">Los {rec.contratos.length} de mayor monto de {rec.contratos_total} · total {formatMXNShort(rec.contratos_monto_total)}</span> : null}
        >
          <div className="overflow-x-auto rounded-xl border border-line" role="region" aria-label="Contratos de este procedimiento" tabIndex={0}>
            <table className="w-full text-sm">
              <thead className="bg-subtle text-left text-xs text-ink-3">
                <tr><th className="px-4 py-2 font-medium">Proveedor</th><th className="px-4 py-2 font-medium">Firma</th><th className="px-4 py-2 text-right font-medium">Monto sin IVA</th></tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rec.contratos.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-2.5">{c.proveedor_id ? <Link className="hover:text-accent" to={`/empresa/${c.proveedor_id}`}>{c.proveedor}</Link> : c.proveedor}</td>
                    <td className="num px-4 py-2.5 text-ink-2">{formatDate(c.firma || c.inicio)}</td>
                    <td className="num px-4 py-2.5 text-right">{formatMXN(c.monto)} {c.moneda !== 'MXN' ? c.moneda : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}
    </>
  )
}
