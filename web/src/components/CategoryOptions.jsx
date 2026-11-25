// Opciones de categoría agrupadas: energía y O&G, salud y general.
export default function CategoryOptions({ meta }) {
  const groups = [['energia', 'Energía y O&G'], ['salud', 'Salud'], ['general', 'General']]
  return groups.map(([key, label]) => (
    <optgroup key={key} label={label}>
      {meta.categorias.filter((c) => c.grupo === key).sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
        .map((c) => <option key={c.codigo} value={c.codigo}>{c.nombre}</option>)}
    </optgroup>
  ))
}
