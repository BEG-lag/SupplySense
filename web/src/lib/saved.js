// Búsquedas guardadas en este navegador (sin cuentas). Cada una recuerda la fecha de la última
// visita para contar "nuevas desde tu última visita" con el campo primera_vez del índice.
import { useCallback, useEffect, useState } from 'react'
import { todayMx } from './dates.js'

const KEY = 'supplysense:guardadas:v1'
const EVENT = 'supplysense:guardadas'

function read() {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function write(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list))
  } catch {
    /* almacenamiento bloqueado: la búsqueda vive solo en esta pestaña */
  }
  window.dispatchEvent(new Event(EVENT))
}

export function useSaved() {
  const [list, setList] = useState(read)
  useEffect(() => {
    const sync = () => setList(read())
    window.addEventListener(EVENT, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const save = useCallback((nombre, filters) => {
    const id = `${Date.now().toString(36)}`
    write([...read(), { id, nombre, filters, creada: todayMx(), visto: todayMx() }])
    return id
  }, [])

  const remove = useCallback((id) => write(read().filter((s) => s.id !== id)), [])

  const markSeen = useCallback((id) => {
    write(read().map((s) => (s.id === id ? { ...s, visto: todayMx() } : s)))
  }, [])

  return { list, save, remove, markSeen }
}
