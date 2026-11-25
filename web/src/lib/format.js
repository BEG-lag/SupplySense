// Formatos es-MX. Celda vacía: "N/D".
const EMPTY = 'N/D'

const mxn = new Intl.NumberFormat('es-MX', {
  style: 'currency', currency: 'MXN', minimumFractionDigits: 0, maximumFractionDigits: 0,
})
const mxnShort = new Intl.NumberFormat('es-MX', {
  style: 'currency', currency: 'MXN', notation: 'compact', maximumFractionDigits: 1,
})
const num = new Intl.NumberFormat('es-MX')
const dateFmt = new Intl.DateTimeFormat('es-MX', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
const dateTimeFmt = new Intl.DateTimeFormat('es-MX', {
  day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
})

export const formatMXN = (v) => (v == null ? EMPTY : mxn.format(v))
export const formatMXNShort = (v) => (v == null ? EMPTY : mxnShort.format(v))
export const formatNumber = (v) => (v == null ? EMPTY : num.format(v))

// Las fechas llegan como texto ISO en hora del centro de México y sin zona:
// se formatean "tal cual" (UTC en el formateador) para no correrlas de día.
function asUTC(iso) {
  const [d, t] = iso.split('T')
  return new Date(`${d}T${t || '00:00:00'}Z`)
}

export function formatDate(iso) {
  if (!iso) return EMPTY
  return dateFmt.format(asUTC(iso.slice(0, 10)))
}

export function formatDateTime(iso) {
  if (!iso) return EMPTY
  if (iso.length <= 10 || iso.endsWith('T00:00:00')) return formatDate(iso)
  return dateTimeFmt.format(asUTC(iso))
}

export const EMPTY_VALUE = EMPTY
