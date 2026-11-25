// Fechas en hora del centro de México (America/Mexico_City), calculadas en el navegador
// para que "cierra en N días" sea correcto aunque el sitio no se haya publicado hoy.

const partsFmt = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/Mexico_City', year: 'numeric', month: '2-digit', day: '2-digit',
})

/** "AAAA-MM-DD" de hoy en la Ciudad de México. */
export function todayMx(now = new Date()) {
  return partsFmt.format(now)
}

/** Días naturales entre hoy (CDMX) y la fecha ISO dada; negativo si ya pasó. */
export function daysUntil(iso, today = todayMx()) {
  if (!iso) return null
  const a = Date.UTC(+today.slice(0, 4), +today.slice(5, 7) - 1, +today.slice(8, 10))
  const d = iso.slice(0, 10)
  const b = Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10))
  return Math.round((b - a) / 86400000)
}

/** Estatus que se muestra: una convocatoria "abierta" cuya apertura ya pasó, en evaluación. */
export function liveStatus(estatus, apertura, today = todayMx()) {
  if (estatus === 'abierta' && apertura) {
    const left = daysUntil(apertura, today)
    if (left != null && left < 0) return 'en_evaluacion'
  }
  return estatus
}

export function closingLabel(apertura, today = todayMx()) {
  const left = daysUntil(apertura, today)
  if (left == null) return null
  if (left < 0) return null
  if (left === 0) return 'Cierra hoy'
  if (left === 1) return 'Cierra mañana'
  return `Cierra en ${left} días`
}
