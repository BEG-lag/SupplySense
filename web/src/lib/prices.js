// Ubicar un monto entre los percentiles publicados (P5 a P95, cada 5) por interpolación lineal.
// No es una probabilidad de ganar: solo dice qué parte de las adjudicaciones fue más barata.

export function percentileOf(amount, percentiles) {
  if (amount == null || !percentiles) return null
  const points = Object.entries(percentiles)
    .map(([p, v]) => [Number(p), v])
    .sort((a, b) => a[0] - b[0])
  if (!points.length) return null
  if (amount <= points[0][1]) return { value: points[0][0], bound: 'below' }
  const last = points[points.length - 1]
  if (amount >= last[1]) return { value: last[0], bound: 'above' }
  for (let i = 1; i < points.length; i += 1) {
    const [p0, v0] = points[i - 1]
    const [p1, v1] = points[i]
    if (amount <= v1) {
      const t = v1 === v0 ? 0 : (amount - v0) / (v1 - v0)
      return { value: Math.round(p0 + t * (p1 - p0)), bound: null }
    }
  }
  return null
}

export function describePercentile(result) {
  if (!result) return null
  if (result.bound === 'below') return `Más bajo que el ${100 - result.value}% de las adjudicaciones`
  if (result.bound === 'above') return `Más alto que el ${result.value}% de las adjudicaciones`
  return `Más alto que el ${result.value}% de las adjudicaciones`
}
