import { createContext, useContext } from 'react'
import { useJson } from './data.js'

const MetaContext = createContext(null)

/** meta.json (catálogos, totales, fuentes) se lee una vez y lo comparten todas las páginas. */
export function MetaProvider({ children }) {
  const state = useJson('meta.json')
  return <MetaContext.Provider value={state}>{children}</MetaContext.Provider>
}

export function useMeta() {
  return useContext(MetaContext)
}

export function categoryName(meta, code) {
  return meta?.categorias?.find((c) => c.codigo === code)?.nombre || code
}

export function buyerName(meta, id) {
  return meta?.compradores?.[id] || id
}

export const SOURCE_NAMES = { comprasmx: 'ComprasMX', cfe: 'CFE', pemex: 'PEMEX', jalisco: 'Jalisco', cdmx: 'CDMX', campeche: 'Campeche' }
export const STATE_SOURCES = ['jalisco', 'cdmx', 'campeche']
