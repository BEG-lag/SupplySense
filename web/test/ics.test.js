import { describe, expect, it } from 'vitest'
import { buildCalendar, calendarFilename, escapeText, fold } from '../src/lib/ics.js'

const rec = {
  id: 'jal:5024',
  numero: 'LPL-43068001-001-2026',
  titulo: 'CONTRATACIÓN DEL SERVICIO DE ESTUDIO ESTRUCTURAL, CENDI',
  comprador_nombre: 'Secretaría de Administración (JAL)',
  publicado: '2026-11-24',
  aclaraciones: '2026-11-26T11:00:00',
  apertura: '2026-12-01T09:30:00',
  fallo: '2026-12-11',
}
const opts = { siteBase: 'https://beg-lag.github.io/SupplySense/', now: new Date('2026-11-25T18:00:00Z'), today: '2026-11-25' }

describe('calendario .ics', () => {
  it('crea un evento por etapa futura, en hora de CDMX', () => {
    const ics = buildCalendar([rec], opts)
    expect(ics.startsWith('BEGIN:VCALENDAR\r\n')).toBe(true)
    expect(ics.endsWith('END:VCALENDAR\r\n')).toBe(true)
    expect(ics.match(/BEGIN:VEVENT/g)).toHaveLength(3)
    expect(ics).toContain('DTSTART;TZID=America/Mexico_City:20261126T110000')
    expect(ics).toContain('DTEND;TZID=America/Mexico_City:20261126T120000')
    expect(ics).toContain('DTSTART;VALUE=DATE:20261211')
    expect(ics).toContain('DTEND;VALUE=DATE:20261212')
    expect(ics).toContain('UID:jal:5024:apertura@supplysense')
    expect(ics).toContain('DTSTAMP:20261125T180000Z')
    expect(ics).not.toContain('VALARM')
  })
  it('omite fechas pasadas y regresa null si no queda ninguna', () => {
    expect(buildCalendar([rec], { ...opts, today: '2026-12-02' }).match(/BEGIN:VEVENT/g)).toHaveLength(1)
    expect(buildCalendar([rec], { ...opts, today: '2026-12-12' })).toBeNull()
  })
  it('escapa texto y corta líneas largas sin pasar de 75 octetos', () => {
    expect(escapeText('a, b; c\\d\ne')).toBe('a\\, b\\; c\\\\d\\ne')
    const folded = fold(`SUMMARY:${'Adquisición de diésel '.repeat(10)}`)
    for (const line of folded.split('\r\n')) expect(new TextEncoder().encode(line).length).toBeLessThanOrEqual(75)
    expect(folded.split('\r\n').slice(1).every((l) => l.startsWith(' '))).toBe(true)
  })
  it('da nombres de archivo seguros', () => {
    expect(calendarFilename('cmx:E-2026-00012345')).toBe('supplysense-cmx-E-2026-00012345.ics')
  })
})
