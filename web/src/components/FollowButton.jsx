import { useFollowed } from '../lib/follow.js'
import { Button } from '../ui/index.jsx'

/** Botón "Seguir" para empresas, compradores y licitaciones (se guarda en el navegador). */
export default function FollowButton({ tipo, id, nombre, snapshot }) {
  const { isFollowing, toggle } = useFollowed()
  const on = isFollowing(tipo, id)
  return (
    <Button
      variant={on ? 'primary' : 'secondary'}
      size="sm"
      aria-pressed={on}
      onClick={() => toggle(tipo, id, nombre, snapshot)}
      title={on ? 'Dejar de seguir' : 'Lo verás en Guardadas, con lo que cambie desde tu última visita'}
    >
      {on ? 'Siguiendo' : 'Seguir'}
    </Button>
  )
}
