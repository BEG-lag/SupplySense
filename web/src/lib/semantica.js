// Búsqueda por significado en el navegador. Usa vectores de palabras entrenados con los títulos
// de las compras públicas (ver src/supplysense/semantica.py). El modelo es un archivo del propio
// sitio (semantica.json); no se consulta ningún servicio externo.
import { loadJson } from './data.js'
import { fold } from './search.js'

const TOKEN = /[a-z][a-z0-9]{2,}/g
let modelPromise = null

function decode(b64) {
  const bin = atob(b64)
  const out = new Int8Array(bin.length)
  for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i) << 24 >> 24
  return out
}

/** Carga y prepara el modelo una sola vez (se pide solo cuando alguien busca). */
export function loadSemantic() {
  if (!modelPromise) {
    modelPromise = loadJson('semantica.json').then((m) => ({
      dim: m.dim,
      stop: new Set(m.stopwords),
      index: new Map(m.vocab.map((w, i) => [w, i])),
      idf: Float32Array.from(m.idf),
      vectors: decode(m.vectores),
      ids: m.ids,
      docs: m.docs ? decode(m.docs) : new Int8Array(0),
    }))
    modelPromise.catch(() => { modelPromise = null })
  }
  return modelPromise
}

export function tokens(text, stop) {
  return (fold(text).match(TOKEN) || []).filter((w) => !stop.has(w))
}

/** Vector de una consulta (promedio ponderado por idf, normalizado) o null si no hay palabras conocidas. */
export function embed(text, model) {
  const v = new Float32Array(model.dim)
  let any = false
  for (const w of tokens(text, model.stop)) {
    const i = model.index.get(w)
    if (i === undefined) continue
    any = true
    const weight = model.idf[i]
    for (let d = 0; d < model.dim; d += 1) v[d] += (model.vectors[i * model.dim + d] / 127) * weight
  }
  if (!any) return null
  const norm = Math.hypot(...v)
  return norm ? v.map((x) => x / norm) : null
}

/** Similitud (aprox. coseno) de la consulta con cada convocatoria abierta: Map id → puntaje. */
export function scoreOpen(query, model) {
  const q = embed(query, model)
  const scores = new Map()
  if (!q) return scores
  const { dim, docs, ids } = model
  for (let r = 0; r < ids.length; r += 1) {
    let s = 0
    for (let d = 0; d < dim; d += 1) s += q[d] * (docs[r * dim + d] / 127)
    scores.set(ids[r], s)
  }
  return scores
}
