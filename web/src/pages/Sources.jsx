import { Link } from 'react-router-dom'
import { formatDate, formatNumber } from '../lib/format.js'
import { useMeta } from '../lib/meta.jsx'
import { Card, Loading, PageHeader, Section } from '../ui/index.jsx'

const SOURCES = {
  cfe: {
    url: 'https://msc.cfe.mx/Aplicaciones/NCFE/Concursos/',
    what: 'Todos los procedimientos del Micrositio de Concursos desde 2015: estatus, ganadores y monto adjudicado. De los vigentes se lee además el detalle (empresa de CFE y fechas de apertura y fallo).',
    limits: 'El detalle no tiene liga pública directa: el sitio te lleva al buscador de CFE y te da el número para copiarlo.',
  },
  pemex: {
    url: 'https://www.pemex.com/procura/procedimientos-de-contratacion/concursosabiertos/Paginas/default.aspx',
    what: 'Los avisos de concursos abiertos que PEMEX publica por segmento (Exploración y Producción, Transformación Industrial, Logística y soporte).',
    limits: 'PEMEX no publica en datos abiertos la fecha límite, el monto ni el ganador. Un aviso se marca como abierto (estimado) durante 30 días desde su publicación.',
  },
  comprasmx: {
    url: 'https://comprasmx.buengobierno.gob.mx/datos-abiertos',
    what: 'Expedientes y contratos 2025 y 2026 de IMP, CENACE, CENAGAS, SENER, INEEL, ASEA, CNE y CONUEE, y de otros compradores cuando el título habla de gasoductos, hidrocarburos, refinerías o plataformas.',
    limits: 'CFE y PEMEX no publican en ComprasMX. Los archivos vienen en una codificación mixta que se corrige al leerlos.',
  },
}

export default function Sources() {
  const { data: meta } = useMeta()
  if (!meta) return <Loading />
  return (
    <>
      <PageHeader eyebrow="Fuentes y método" title="De dónde sale cada dato">
        SupplySense no inventa ni estima convocatorias: reúne lo que publican CFE, PEMEX y ComprasMX,
        lo ordena y lo cruza. Cada registro liga a su fuente oficial.
      </PageHeader>

      <div className="grid gap-4">
        {Object.entries(SOURCES).map(([key, s]) => {
          const f = meta.fuentes[key]
          return (
            <Card key={key} className="p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <a href={s.url} target="_blank" rel="noreferrer" className="text-lg font-semibold hover:text-accent">{f.nombre}</a>
                <span className="text-sm" style={{ color: f.falla_desde ? 'var(--danger)' : 'var(--open)' }}>
                  {f.falla_desde ? `Falla desde ${formatDate(f.falla_desde)}` : `Leída el ${formatDate(f.ultima_ok)}`}
                </span>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-ink-2">{s.what}</p>
              <p className="mt-2 text-sm leading-relaxed text-ink-3">{s.limits}</p>
              <p className="num mt-3 text-[13px] text-ink-2">
                {formatNumber(f.procedimientos)} procedimientos · {formatNumber(f.abiertas)} abiertos hoy
              </p>
            </Card>
          )
        })}
      </div>

      <Section title="Cómo se arma">
        <ol className="list-decimal space-y-2 pl-5 text-[15px] leading-relaxed text-ink-2">
          <li>Cada mañana, un proceso automático (GitHub Actions) lee las tres fuentes. Si una falla, se conserva lo último bueno y se avisa al tercer día.</li>
          <li>Los registros se guardan en archivos de texto versionados: cada cambio de una fuente queda en el historial público del repositorio.</li>
          <li>Las reglas son archivos legibles: compradores del sector, palabras de contexto, categorías y correcciones manuales.</li>
          <li>Los precios son percentiles del monto adjudicado por procedimiento (CFE) o por contrato (ComprasMX), en pesos. Los contratos en dólares se convierten con el tipo de cambio FIX del día de firma. Montos atípicos (arriba del percentil 99 de su categoría o debajo de $10,000) se excluyen.</li>
          <li>Los ganadores son públicos por ley y así se publican. El RFC solo se muestra para personas morales; el de personas físicas contiene su fecha de nacimiento y no se publica. Tampoco se guardan los nombres ni correos de los servidores públicos que operan los anuncios.</li>
        </ol>
      </Section>

      <Section title="Límites">
        <ul className="list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-ink-2">
          <li>La clasificación por categoría es por palabras clave: es buena para orientarse, no infalible. Lo que no encaja queda en “Otros”.</li>
          <li>Un monto adjudicado por procedimiento puede cubrir varias partidas o ganadores; compárese con cuidado.</li>
          <li>Campeche: hoy se cubre con el filtro de entidad sobre CFE y ComprasMX. El canal estatal de compras con recursos propios aún no está integrado.</li>
        </ul>
      </Section>

      <Section title="Aviso">
        <Card className="p-5 text-sm leading-relaxed text-ink-2">
          Este sitio no constituye opinión legal ni asesoría fiscal. Antes de participar en un
          procedimiento, valida bases, fechas, requisitos y el estado vigente en la fuente oficial y,
          si hace falta, con la autoridad o un asesor.
        </Card>
      </Section>
      <p className="mt-6 text-sm text-ink-3">Más detalle técnico en el <a className="text-accent hover:underline" href="https://github.com/BEG-lag/SupplySense/blob/main/docs/fuentes.md" target="_blank" rel="noreferrer">documento de fuentes</a>. <Link className="text-accent hover:underline" to="/">Volver al inicio</Link></p>
    </>
  )
}
