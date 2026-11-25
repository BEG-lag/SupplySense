import { describe, expect, it } from 'vitest'
import { displayTitle } from '../src/lib/text.js'
import { daysUntil, liveStatus, closingLabel } from '../src/lib/dates.js'
import { percentileOf } from '../src/lib/prices.js'
import { applyFilters, fold } from '../src/lib/search.js'

describe('displayTitle', () => {
  it('pasa a tipo oración y conserva siglas, claves y nombres propios', () => {
    expect(displayTitle('SERVICIO DE SUMINISTRO DE DIÉSEL Y GASOLINA PARA CFE DISTRIBUCIÓN EN VERACRUZ'))
      .toBe('Servicio de suministro de diésel y gasolina para CFE Distribución en Veracruz')
    expect(displayTitle('6100003062 SUMINISTRO E INSTALACIÓN DE SISTEMA SCADA'))
      .toBe('6100003062 suministro e instalación de sistema SCADA')
    expect(displayTitle('SUMINISTRO DE DIÉSEL CON DESTINO A LA DIVISIÓN CENTRO SUR 2027'))
      .toBe('Suministro de diésel con destino a la división centro sur 2027')
  })
  it('no toca títulos que ya vienen en minúsculas', () => {
    expect(displayTitle('Suministro de gas para operación de cromatógrafos')).toBe('Suministro de gas para operación de cromatógrafos')
  })
})

describe('fechas en CDMX', () => {
  it('cuenta días naturales', () => {
    expect(daysUntil('2026-11-27T10:00:00', '2026-11-25')).toBe(2)
    expect(daysUntil('2026-11-25', '2026-11-25')).toBe(0)
    expect(daysUntil('2026-11-24', '2026-11-25')).toBe(-1)
  })
  it('una abierta cuya apertura ya pasó se muestra en evaluación', () => {
    expect(liveStatus('abierta', '2026-11-20T10:00:00', '2026-11-25')).toBe('en_evaluacion')
    expect(liveStatus('abierta', '2026-11-30T10:00:00', '2026-11-25')).toBe('abierta')
    expect(liveStatus('abierta', null, '2026-11-25')).toBe('abierta')
  })
  it('etiqueta de cierre', () => {
    expect(closingLabel('2026-11-25', '2026-11-25')).toBe('Cierra hoy')
    expect(closingLabel('2026-11-28', '2026-11-25')).toBe('Cierra en 3 días')
  })
})

describe('percentileOf', () => {
  const p = { 5: 100, 25: 200, 50: 400, 75: 800, 95: 1600 }
  it('interpola entre percentiles', () => {
    expect(percentileOf(300, p)).toEqual({ value: 38, bound: null })
    expect(percentileOf(400, p)).toEqual({ value: 50, bound: null })
  })
  it('marca los extremos', () => {
    expect(percentileOf(50, p).bound).toBe('below')
    expect(percentileOf(5000, p).bound).toBe('above')
  })
})

describe('búsqueda', () => {
  const recs = [
    { id: 'a', titulo: 'Válvulas de compuerta', fuente: 'cfe', estatus: 'abierta', apertura: null, categoria: 'valvulas', comprador_id: 'cfe' },
    { id: 'b', titulo: 'Tubería de acero', fuente: 'pemex', estatus: 'abierta', apertura: null, categoria: 'tuberia_ductos', comprador_id: 'pemex' },
  ]
  it('ignora acentos y exige todas las palabras', () => {
    expect(fold('Válvulas')).toBe('valvulas')
    expect(applyFilters(recs, { q: 'valvulas compuerta' }).map((r) => r.id)).toEqual(['a'])
    expect(applyFilters(recs, { q: 'valvulas acero' })).toEqual([])
  })
  it('filtra por fuente y categoría', () => {
    expect(applyFilters(recs, { fuente: 'pemex' }).map((r) => r.id)).toEqual(['b'])
    expect(applyFilters(recs, { categoria: 'valvulas' }).map((r) => r.id)).toEqual(['a'])
  })
})

import { inferCategories } from '../src/lib/giros.js'

describe('búsqueda por giro', () => {
  const meta = {
    giros: [
      { codigo: 'vehiculos', incluir: '\\bvehiculos?\\b|camioneta', excluir: null },
      { codigo: 'valvulas', incluir: '\\bvalvula', excluir: null },
      { codigo: 'perforacion', incluir: '\\bpozos?\\b', excluir: 'pozos? de agua' },
    ],
    sinonimos: { patrullas: 'vehiculos' },
  }
  it('usa sinónimos y las mismas reglas del build', () => {
    expect([...inferCategories('Patrullas', meta)]).toEqual(['vehiculos'])
    expect([...inferCategories('válvulas de compuerta', meta)]).toEqual(['valvulas'])
  })
  it('respeta las exclusiones', () => {
    expect([...inferCategories('pozos de agua', meta)]).toEqual([])
    expect([...inferCategories('reparación de pozos', meta)]).toEqual(['perforacion'])
  })
})
