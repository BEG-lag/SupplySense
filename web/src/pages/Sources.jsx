import { Link } from 'react-router-dom'
import { formatDate, formatNumber } from '../lib/format.js'
import { useMeta } from '../lib/meta.jsx'
import { Card, Loading, PageHeader, Section } from '../ui/index.jsx'

const SOURCES = {
  jalisco: {
    url: 'https://compras.jalisco.gob.mx/requisition/tree',
    what: 'Compras con recursos propios del gobierno de Jalisco (Secretaría de Administración): convocatorias abiertas, en junta, en evaluación y canceladas, con el calendario de junta, apertura y fallo.',
    limits: 'El portal solo lista lo vigente: lo que sale del listado se conserva con su último estado y se da por concluido cuando pasa la fecha de fallo. Lo que tiene número federal ya viene de ComprasMX y no se duplica.',
  },
  cdmx: {
    url: 'https://concursodigital.finanzas.cdmx.gob.mx/convocatorias_publicas',
    what: 'Concurso Digital de la Ciudad de México: convocatorias de dependencias locales con fechas de junta de aclaraciones, apertura y fallo.',
    limits: 'El portal no publica estatus: se estima por fechas. No se guardan el nombre del servidor público responsable ni datos bancarios que muestra la página.',
  },
  campeche: {
    url: 'https://safin.campeche.gob.mx/convocatorias/estatales',
    what: 'Licitaciones públicas estatales de la Secretaría de Administración, Finanzas y Planeación de Campeche, leídas del PDF de cada convocatoria: objeto, dependencia que solicita, ley aplicable y fechas.',
    limits: 'Solo las de esa Secretaría; las de salud, obra pública y municipios (Carmen incluido) aún no. El estatus se estima por fechas.',
  },
  guanajuato: {
    url: 'https://transparencia.guanajuato.gob.mx/transparencia/informacion_publica_licitaciones.php',
    what: 'Licitaciones, invitaciones y adjudicaciones del gobierno de Guanajuato desde 2021, en el portal de la Unidad de Transparencia. De las recientes se leen las fechas y la ley aplicable en la convocatoria (incluso dentro del ZIP de la Secretaría de Finanzas, sin bajarlo completo).',
    limits: 'No publica estatus: con acta de fallo se da por concluida, con acta de apertura queda en evaluación, y si no, se estima por fechas. Las convocatorias escaneadas (Educación) no dan fechas. Lo pagado con recursos federales se descarta porque ya está en ComprasMX.',
  },
  nuevo_leon: {
    url: 'https://subasta.nl.gob.mx/monitoreosubastas.asp',
    what: 'Subastas electrónicas inversas del gobierno de Nuevo León desde 2016: dependencia que solicita, fecha, precio base, ganador, mejor oferta y proveedores que participaron.',
    limits: 'Las convocatorias de licitación de nl.gob.mx rechazan a los lectores automáticos y no se leen; las de Agua y Drenaje de Monterrey están escaneadas.',
  },
  banxico: {
    url: 'https://www.banxico.org.mx/PortalProveedores/',
    what: 'Licitaciones e invitaciones del Banco de México desde 2021 (adquisiciones, enajenaciones y obra), con el calendario de cada etapa.',
    limits: 'Banxico no publica en ComprasMX. Ganador y monto solo vienen en las actas en PDF y no se leen.',
  },
  oaj: {
    url: 'https://www.oaj.gob.mx/convocatoriasDGRMSG.htm',
    what: 'Convocatorias del Órgano de Administración Judicial (antes Consejo de la Judicatura Federal), de Recursos Materiales e Inmuebles y Mantenimiento. También compra para la Suprema Corte y el Tribunal Electoral.',
    limits: 'No publica estatus: con acta de fallo se da por concluida y, si no, se estima por la fecha de publicación.',
  },
  dof: {
    url: 'https://www.dof.gob.mx/',
    what: 'Resúmenes de convocatoria de la sección de concursos del Diario Oficial: universidades, poderes, organismos autónomos, estados y municipios que no publican en ComprasMX (INE, Cámara de Diputados, UNAM, universidades estatales, entre otros).',
    limits: 'Solo licitaciones públicas (las invitaciones no se publican ahí). Se descarta lo que ya trae número de ComprasMX y lo de los portales que ya leemos. El texto del DOF a veces corta palabras; el estatus se estima por fechas.',
  },
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
    what: 'Todos los expedientes y contratos 2025 y 2026 de la Administración Pública Federal y de los estados y municipios cuando usan dinero federal: más de 800 compradores. Los de IMP, CENACE, CENAGAS, SENER, INEEL, ASEA, CNE y CONUEE, y los que hablan de gasoductos, hidrocarburos o refinerías, forman la vertical de energía.',
    limits: 'CFE y PEMEX no publican en ComprasMX. Los archivos son fotos completas de cada año: se descargan cada día y no se guardan en el repositorio. Vienen en una codificación mixta que se corrige al leerlos.',
  },
}

export default function Sources() {
  const { data: meta } = useMeta()
  if (!meta) return <Loading />
  return (
    <>
      <PageHeader eyebrow="Fuentes y método" title="De dónde sale cada dato">
        SupplySense no inventa ni estima convocatorias: reúne lo que publican ComprasMX, CFE, PEMEX,
        los portales de compras de Jalisco, CDMX, Campeche, Guanajuato y Nuevo León, Banxico, el
        Poder Judicial y la sección de concursos del DOF, lo ordena y lo cruza. Cada registro liga a
        su fuente oficial.
      </PageHeader>

      <div className="grid gap-4">
        {['comprasmx', 'cfe', 'pemex', 'jalisco', 'cdmx', 'campeche', 'guanajuato', 'nuevo_leon', 'banxico', 'oaj', 'dof']
          .filter((key) => meta.fuentes[key])
          .map((key) => [key, SOURCES[key]]).map(([key, s]) => {
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

      <p className="mt-4 text-sm leading-relaxed text-ink-3">
        Pendientes: Estado de México (su portal exige sesiones de JSF y publica las fechas solo en
        PDF) y Tabasco (el portal estatal no respondió al revisarlo). Veracruz y el Tribunal Electoral
        protegen sus sitios con verificación anti-robots: no se leen, y lo que publican en el DOF o con
        dinero federal sí aparece.
      </p>

      <Section title="Cómo se arma">
        <ol className="list-decimal space-y-2 pl-5 text-[15px] leading-relaxed text-ink-2">
          <li>Cada mañana, un proceso automático (GitHub Actions) lee todas las fuentes. Si una falla, se conserva lo último bueno y se avisa al tercer día.</li>
          <li>Los registros se guardan en archivos de texto versionados: cada cambio de una fuente queda en el historial público del repositorio.</li>
          <li>Las reglas son archivos legibles: compradores del sector, palabras de contexto, categorías y correcciones manuales.</li>
          <li>Cada registro lleva una de 35 categorías, en tres grupos: energía y O&amp;G, salud y general. La vertical de energía reúne a CFE, PEMEX, las dependencias del sector y lo que menciona gasoductos, hidrocarburos o refinerías.</li>
          <li>La búsqueda por significado usa vectores de palabras entrenados cada día con los títulos de unas 530 mil compras públicas (co-ocurrencias, PPMI y SVD). El modelo pesa alrededor de 1.5 MB, es un archivo del propio sitio y la comparación se hace en tu navegador: no se envía lo que buscas a ningún servicio.</li>
          <li>Los precios son percentiles del monto adjudicado por contrato (ComprasMX) o por procedimiento (CFE), en pesos. Los contratos en dólares se convierten con el tipo de cambio FIX del día de firma. Montos atípicos (arriba del percentil 99 de su categoría o debajo de $10,000) se excluyen.</li>
          <li>Los ganadores son públicos por ley y así se publican. El RFC solo se muestra para personas morales; el de personas físicas contiene su fecha de nacimiento y no se publica. Tampoco se guardan los nombres ni correos de los servidores públicos que operan los anuncios.</li>
        </ol>
      </Section>

      <Section title="Límites">
        <ul className="list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-ink-2">
          <li>La clasificación por categoría es por palabras clave: es buena para orientarse, no infalible. Lo que no encaja queda en “Otros”.</li>
          <li>Un monto adjudicado por procedimiento puede cubrir varias partidas o ganadores; compárese con cuidado.</li>
          <li>Estados y municipios: aparecen sus compras con dinero federal (ComprasMX), sus licitaciones públicas resumidas en el DOF y, en cinco estados, las de su portal propio. Las invitaciones y adjudicaciones con recursos propios de los demás estados aún no.</li>
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
