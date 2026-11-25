import { useEffect, useState } from 'react'

const BASE = `${import.meta.env.BASE_URL}data/`
const cache = new Map()

/** Lee un JSON del sitio una sola vez por sesión. */
export function loadJson(path) {
  if (!cache.has(path)) {
    const promise = fetch(BASE + path).then((res) => {
      if (!res.ok) throw new Error(`No se pudo leer ${path} (HTTP ${res.status})`)
      return res.json()
    })
    promise.catch(() => cache.delete(path))
    cache.set(path, promise)
  }
  return cache.get(path)
}

/** Hook: { data, error, loading } para uno o varios JSON. */
export function useJson(path) {
  const key = Array.isArray(path) ? path.join('|') : path
  const [state, setState] = useState({ data: null, error: null, loading: Boolean(path) })
  useEffect(() => {
    if (!path) return undefined
    let alive = true
    setState((s) => ({ ...s, loading: true, error: null }))
    const req = Array.isArray(path) ? Promise.all(path.map(loadJson)) : loadJson(path)
    req.then(
      (data) => alive && setState({ data, error: null, loading: false }),
      (error) => alive && setState({ data: null, error, loading: false }),
    )
    return () => { alive = false }
  }, [key]) // eslint-disable-line react-hooks/exhaustive-deps
  return state
}

export const feedUrl = (rel = 'feed.xml') => BASE + rel

/** Fragmento (2 caracteres hex del SHA-1) en el que vive un id, igual que en el build. */
export async function shardOf(id) {
  const bytes = new TextEncoder().encode(id)
  const digest = await crypto.subtle.digest('SHA-1', bytes)
  return [...new Uint8Array(digest).slice(0, 1)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

export async function loadDetail(id) {
  const shard = await shardOf(id)
  const items = await loadJson(`detalle/${shard}.json`)
  return items[id] || null
}

export async function loadCompany(id) {
  const shard = await shardOf(id)
  const items = await loadJson(`empresas/${shard}.json`)
  return items[id] || null
}

/** Filas compactas del índice → objetos con nombre de campo (orden de meta.indice_campos). */
export function toRecords(rows, fields) {
  return rows.map((row) => {
    const rec = {}
    fields.forEach((f, i) => { rec[f] = row[i] })
    rec.estatus_estimado = Boolean(rec.estatus_estimado)
    return rec
  })
}
