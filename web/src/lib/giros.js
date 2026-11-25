// Búsqueda por giro: clasifica lo que alguien escribe con las mismas reglas del build
// (reglas/categorias.csv y reglas/sinonimos.csv, exportadas en meta.json). Así "patrullas"
// encuentra convocatorias de vehículos aunque no usen esa palabra. Todo ocurre en el navegador.
import { fold } from './search.js'

const compiled = new WeakMap()

function rulesOf(meta) {
  if (!compiled.has(meta)) {
    compiled.set(meta, (meta.giros || []).map((g) => ({
      codigo: g.codigo,
      incluir: new RegExp(g.incluir),
      excluir: g.excluir ? new RegExp(g.excluir) : null,
    })))
  }
  return compiled.get(meta)
}

/** Categorías a las que pertenece el texto buscado (puede ser más de una). */
export function inferCategories(query, meta) {
  const text = fold(query).trim()
  const found = new Set()
  if (!text || !meta) return found
  for (const word of text.split(/\s+/)) {
    const code = meta.sinonimos?.[word]
    if (code) found.add(code)
  }
  for (const rule of rulesOf(meta)) {
    if (rule.incluir.test(text) && !(rule.excluir && rule.excluir.test(text))) found.add(rule.codigo)
  }
  return found
}
