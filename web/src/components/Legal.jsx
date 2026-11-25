// Marco legal y calendario de un procedimiento. Orientación general en lenguaje sencillo, a
// partir del dato oficial (la ley que reporta ComprasMX, o el régimen propio de CFE y PEMEX).
// No es opinión legal: requisitos y plazos se validan en la convocatoria.
import { daysUntil, todayMx } from '../lib/dates.js'
import { formatDateTime } from '../lib/format.js'
import { Card, Section } from '../ui/index.jsx'

const LEYES_MX = 'https://github.com/BEG-lag/leyes-mx/blob/main/leyes/'
const DIPUTADOS = 'https://www.diputados.gob.mx/LeyesBiblio/index.htm'

const LAWS = {
  'LEY DE ADQUISICIONES, ARRENDAMIENTOS Y SERVICIOS DEL SECTOR PÚBLICO': {
    nombre: 'Ley de Adquisiciones, Arrendamientos y Servicios del Sector Público',
    url: DIPUTADOS,
    fuente: 'Texto vigente en la Cámara de Diputados',
  },
  'LEY DE OBRAS PÚBLICAS Y SERVICIOS RELACIONADOS CON LAS MISMAS': {
    nombre: 'Ley de Obras Públicas y Servicios Relacionados con las Mismas',
    url: DIPUTADOS,
    fuente: 'Texto vigente en la Cámara de Diputados',
  },
  'LEY DE ASOCIACIONES PÚBLICO PRIVADAS': {
    nombre: 'Ley de Asociaciones Público Privadas',
    url: DIPUTADOS,
    fuente: 'Texto vigente en la Cámara de Diputados',
  },
}

function lawFor(rec) {
  if (rec.fuente === 'cfe') {
    return {
      nombre: 'Ley de la Empresa Pública del Estado, Comisión Federal de Electricidad (DOF 18-03-2025)',
      nota: 'CFE contrata con un régimen propio, distinto de la ley general de adquisiciones, y con sus disposiciones internas de contratación.',
      url: `${LEYES_MX}lepecfe.md`,
      fuente: 'Texto y reformas en leyes-mx',
    }
  }
  if (rec.fuente === 'pemex') {
    return {
      nombre: 'Ley de la Empresa Pública del Estado, Petróleos Mexicanos (DOF 18-03-2025)',
      nota: 'PEMEX contrata con un régimen propio, distinto de la ley general de adquisiciones, y con sus disposiciones internas de contratación.',
      url: `${LEYES_MX}lepepm.md`,
      fuente: 'Texto y reformas en leyes-mx',
    }
  }
  if (rec.ley && LAWS[rec.ley]) return LAWS[rec.ley]
  if (rec.ley) return { nombre: rec.ley.charAt(0) + rec.ley.slice(1).toLowerCase() }
  return null
}

// Explicaciones generales por tipo de procedimiento (ComprasMX y CFE).
const TYPES = [
  [/licitaci[oó]n p[uú]blica|concurso abierto/i, 'Procedimiento abierto: cualquier proveedor que cumpla los requisitos de la convocatoria puede presentar propuesta.'],
  [/invitaci[oó]n a cuando menos tres|invitaci[oó]n restringida/i, 'La dependencia invita a un grupo de proveedores. Si no te invitaron, en general no puedes participar, pero sirve para conocer el mercado y prepararte para la siguiente.'],
  [/concurso simplificado/i, 'Procedimiento abreviado de CFE, con menos etapas y plazos más cortos que un concurso abierto.'],
  [/acuerdo marco/i, 'Compra hecha a proveedores que ya forman parte de un acuerdo marco vigente.'],
  [/entre entes p[uú]blicos/i, 'Contrato entre dependencias o entidades públicas; no hay competencia con proveedores privados.'],
  [/adjudicaci[oó]n directa/i, 'Se asigna sin concurso a un proveedor. No es una oportunidad abierta, pero sirve como referencia de precios y de a quién le compra cada dependencia.'],
]

function typeNote(tipo) {
  if (!tipo) return null
  return TYPES.find(([re]) => re.test(tipo))?.[1] || null
}

function characterNote(caracter) {
  if (!caracter) return null
  if (/internacional/i.test(caracter)) return 'Carácter internacional: pueden participar también proveedores extranjeros, en los términos de la convocatoria.'
  if (/nacional/i.test(caracter)) return 'Carácter nacional: en general participan proveedores mexicanos; revisa en la convocatoria los requisitos de origen.'
  return null
}

function relative(iso, today) {
  const d = daysUntil(iso, today)
  if (d == null) return ''
  if (d === 0) return 'hoy'
  if (d === 1) return 'mañana'
  if (d === -1) return 'ayer'
  return d > 0 ? `en ${d} días` : `hace ${-d} días`
}

export default function Legal({ rec }) {
  if (rec.tipo === 'contrato') return null
  const today = todayMx()
  const law = lawFor(rec)
  const notes = [typeNote(rec.tipo_procedimiento), characterNote(rec.caracter)].filter(Boolean)
  const events = [
    ['Publicación', rec.publicado],
    ['Junta de aclaraciones', rec.aclaraciones],
    ['Presentación y apertura de propuestas', rec.apertura],
    ['Apertura económica', rec.apertura_economica],
    ['Fallo', rec.fallo],
  ].filter(([, d]) => d)
  const next = events.find(([, d]) => (daysUntil(d, today) ?? -1) >= 0)

  return (
    <Section title="Marco legal y calendario">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <p className="eyebrow mb-2">Ley aplicable</p>
          {law ? (
            <>
              <p className="font-medium leading-snug">{law.nombre}</p>
              {law.nota && <p className="mt-2 text-sm leading-relaxed text-ink-2">{law.nota}</p>}
              {law.url && (
                <a className="mt-2 inline-block text-sm text-accent underline-offset-4 hover:underline" href={law.url} target="_blank" rel="noreferrer">{law.fuente}</a>
              )}
            </>
          ) : <p className="text-sm text-ink-3">La fuente no reporta la ley aplicable.</p>}
          {notes.length > 0 && (
            <>
              <p className="eyebrow mb-2 mt-5">Tipo de procedimiento</p>
              <p className="text-sm font-medium">{rec.tipo_procedimiento}</p>
              {notes.map((n) => <p key={n} className="mt-1.5 text-sm leading-relaxed text-ink-2">{n}</p>)}
            </>
          )}
        </Card>
        <Card className="p-5">
          <p className="eyebrow mb-3">Calendario</p>
          {events.length ? (
            <ol className="relative space-y-4 border-l border-line pl-5">
              {events.map(([label, d]) => {
                const isNext = next && next[0] === label
                const past = (daysUntil(d, today) ?? 0) < 0
                return (
                  <li key={label} className="relative">
                    <span
                      className="absolute -left-[26px] top-1 h-2.5 w-2.5 rounded-full"
                      style={{ background: isNext ? 'var(--lime)' : past ? 'var(--fg-3)' : 'var(--line-strong)' }}
                      aria-hidden
                    />
                    <div className={isNext ? 'font-medium text-accent' : past ? 'text-ink-3' : ''}>{label}</div>
                    <div className="num text-[13px] text-ink-2">{formatDateTime(d)} · {relative(d, today)}</div>
                  </li>
                )
              })}
            </ol>
          ) : <p className="text-sm text-ink-3">La fuente no publica fechas de las etapas.</p>}
          {rec.fallo && (
            <p className="mt-4 text-[13px] leading-relaxed text-ink-3">
              Si participas y no estás de acuerdo con el resultado, la ley aplicable prevé medios de
              defensa con plazos cortos. Revisa el plazo en la convocatoria y en la ley.
            </p>
          )}
        </Card>
      </div>
      <p className="mt-3 text-xs text-ink-3">
        Orientación general a partir de los datos publicados. No constituye opinión legal: valida
        requisitos, plazos y el régimen aplicable en la convocatoria y, en su caso, con la autoridad
        competente.
      </p>
    </Section>
  )
}
