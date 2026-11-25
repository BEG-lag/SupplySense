// Empresas, compradores y licitaciones que alguien sigue, guardados solo en este navegador.
// No hay correos ni notificaciones: en Guardadas se ve qué cambió desde la última visita.
import { useCallback, useEffect, useState } from 'react'
import { todayMx } from './dates.js'

const KEY = 'supplysense:siguiendo:v1'
const EVENT = 'supplysense:siguiendo'

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
    /* almacenamiento bloqueado: el seguimiento vive solo en esta pestaña */
  }
  window.dispatchEvent(new Event(EVENT))
}

export function useFollowed() {
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

  const isFollowing = useCallback((tipo, id) => list.some((f) => f.tipo === tipo && f.id === id), [list])

  /** `snapshot` guarda el estado al seguir (estatus de una licitación, número de adjudicaciones). */
  const toggle = useCallback((tipo, id, nombre, snapshot = {}) => {
    const current = read()
    if (current.some((f) => f.tipo === tipo && f.id === id)) {
      write(current.filter((f) => !(f.tipo === tipo && f.id === id)))
    } else {
      write([...current, { tipo, id, nombre, desde: todayMx(), visto: todayMx(), ...snapshot }])
    }
  }, [])

  const markSeen = useCallback((tipo, id, snapshot = {}) => {
    write(read().map((f) => (f.tipo === tipo && f.id === id ? { ...f, visto: todayMx(), ...snapshot } : f)))
  }, [])

  return { list, isFollowing, toggle, markSeen }
}
