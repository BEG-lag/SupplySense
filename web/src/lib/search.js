// Búsqueda en el navegador: sin acentos, todas las palabras deben aparecer.
import { liveStatus } from './dates.js'

export function fold(text) {
  return (text || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
}

export const FILTER_KEYS = ['q', 'sector', 'fuente', 'comprador', 'entidad', 'categoria', 'estatus']

export function filtersFromParams(params) {
  const out = {}
  for (const key of FILTER_KEYS) {
    const value = params.get(key)
    if (value) out[key] = value
  }
  return out
}

export function haystack(rec, buyers) {
  return fold([rec.titulo, rec.numero, buyers?.[rec.comprador_id], rec.ganador, rec.entidad].join(' '))
}

/** Aplica filtros a registros del índice. `today` permite recalcular el estatus vivo. */
export function applyFilters(records, filters, { buyers, today } = {}) {
  const words = fold(filters.q).split(/\s+/).filter(Boolean)
  return records.filter((rec) => {
    if (filters.sector && rec.sector !== filters.sector) return false
    if (filters.fuente && rec.fuente !== filters.fuente) return false
    if (filters.comprador && rec.comprador_id !== filters.comprador) return false
    if (filters.entidad && rec.entidad !== filters.entidad) return false
    if (filters.categoria && rec.categoria !== filters.categoria) return false
    if (filters.estatus) {
      const status = liveStatus(rec.estatus, rec.apertura, today)
      if (status !== filters.estatus) return false
    }
    if (words.length) {
      const text = haystack(rec, buyers)
      if (!words.every((w) => text.includes(w))) return false
    }
    return true
  })
}

export function describeFilters(filters, meta) {
  const parts = []
  if (filters.q) parts.push(`"${filters.q}"`)
  if (filters.sector === 'energia') parts.push('Energía y O&G')
  if (filters.estatus) parts.push(meta?.estatus?.[filters.estatus] || filters.estatus)
  if (filters.fuente) parts.push(meta?.fuentes?.[filters.fuente]?.nombre || filters.fuente)
  if (filters.comprador) parts.push(meta?.compradores?.[filters.comprador] || filters.comprador)
  if (filters.categoria) {
    parts.push(meta?.categorias?.find((c) => c.codigo === filters.categoria)?.nombre || filters.categoria)
  }
  if (filters.entidad) parts.push(filters.entidad)
  return parts.join(' · ') || 'Todas las licitaciones'
}
