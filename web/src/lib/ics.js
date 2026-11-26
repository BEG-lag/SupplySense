// Calendario descargable (.ics) con las fechas de uno o varios procedimientos. Es un archivo que
// se guarda en el equipo y cada quien lo importa en su propio calendario: no hay suscripción,
// correo ni recordatorios, y nada sale del navegador.
import { todayMx } from './dates.js'
import { displayTitle } from './text.js'

const TZ = 'America/Mexico_City'
// México no tiene horario de verano desde octubre de 2022: UTC-6 todo el año.
const VTIMEZONE = [
  'BEGIN:VTIMEZONE', `TZID:${TZ}`,
  'BEGIN:STANDARD', 'DTSTART:19700101T000000', 'TZOFFSETFROM:-0600', 'TZOFFSETTO:-0600', 'TZNAME:CST', 'END:STANDARD',
  'END:VTIMEZONE',
]

export const STAGES = [
  ['registro', 'Fecha límite de registro'],
  ['aclaraciones', 'Junta de aclaraciones'],
  ['apertura', 'Presentación y apertura de propuestas'],
  ['apertura_economica', 'Apertura económica'],
  ['fallo', 'Fallo'],
]

export function escapeText(value) {
  return String(value ?? '')
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,')
    .replace(/\r?\n/g, '\\n')
}

/** Corta una línea en tramos de 75 octetos como pide el RFC 5545 (sin partir caracteres). */
export function fold(line) {
  const enc = new TextEncoder()
  const parts = []
  let current = ''
  let size = 0
  for (const ch of line) {
    const n = enc.encode(ch).length
    const limit = parts.length ? 74 : 75 // las continuaciones empiezan con un espacio
    if (size + n > limit) {
      parts.push(current)
      current = ''
      size = 0
    }
    current += ch
    size += n
  }
  parts.push(current)
  return parts.join('\r\n ')
}

const pad = (n) => String(n).padStart(2, '0')

function compact(date) {
  return `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}`
}

/** "2026-11-26T11:00:00" → hora local de CDMX; "2026-11-26" o medianoche → día completo. */
function parse(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/.exec(iso || '')
  if (!m) return null
  const [, y, mo, d, h = '00', mi = '00', s = '00'] = m
  // Se usa UTC como reloj "de pared" para sumar sin que intervenga la zona del navegador.
  const wall = new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi, +s))
  return { wall, allDay: h === '00' && mi === '00' && s === '00' }
}

function eventLines(rec, key, label, iso, { siteBase, stamp }) {
  const p = parse(iso)
  if (!p) return []
  const title = displayTitle(rec.titulo || rec.numero || rec.id)
  const lines = [
    'BEGIN:VEVENT',
    `UID:${rec.id}:${key}@supplysense`,
    `DTSTAMP:${stamp}`,
  ]
  if (p.allDay) {
    const next = new Date(p.wall.getTime() + 86400000)
    lines.push(`DTSTART;VALUE=DATE:${compact(p.wall)}`, `DTEND;VALUE=DATE:${compact(next)}`)
  } else {
    const end = new Date(p.wall.getTime() + 3600000)
    const t = (d) => `${compact(d)}T${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}00`
    lines.push(`DTSTART;TZID=${TZ}:${t(p.wall)}`, `DTEND;TZID=${TZ}:${t(end)}`)
  }
  const url = `${siteBase}licitacion/${encodeURIComponent(rec.id)}`
  const description = [
    rec.numero && `Procedimiento ${rec.numero}`,
    rec.comprador_nombre,
    `Detalle: ${url}`,
    'Fechas tomadas de la fuente oficial. Valídalas en la convocatoria.',
  ].filter(Boolean).join('\n')
  lines.push(
    `SUMMARY:${escapeText(`${label}: ${title}`.slice(0, 160))}`,
    `DESCRIPTION:${escapeText(description)}`,
    `URL:${url}`,
    'TRANSP:TRANSPARENT',
    'END:VEVENT',
  )
  return lines
}

/** Eventos de hoy en adelante para cada etapa con fecha. Devuelve null si no hay ninguno. */
export function buildCalendar(records, { siteBase, now = new Date(), today = todayMx(now) } = {}) {
  const stamp = `${now.toISOString().replace(/[-:]/g, '').slice(0, 15)}Z`
  const events = []
  for (const rec of records) {
    for (const [key, label] of STAGES) {
      const iso = rec[key]
      if (!iso || iso.slice(0, 10) < today) continue
      events.push(...eventLines(rec, key, label, iso, { siteBase, stamp }))
    }
  }
  if (!events.length) return null
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//SupplySense//Licitaciones//ES',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'X-WR-CALNAME:SupplySense',
    ...VTIMEZONE,
    ...events,
    'END:VCALENDAR',
  ]
  return `${lines.map(fold).join('\r\n')}\r\n`
}

export function siteBase() {
  return `${window.location.origin}${import.meta.env.BASE_URL}`
}

/** Baja el archivo .ics en el navegador. */
export function downloadCalendar(text, filename) {
  const blob = new Blob([text], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function calendarFilename(id) {
  return `supplysense-${String(id).replace(/[^a-z0-9-]+/gi, '-').replace(/^-|-$/g, '')}.ics`
}
