import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { feedUrl, toRecords, useJson } from '../lib/data.js'
import { formatDate, formatNumber } from '../lib/format.js'
import { useMeta } from '../lib/meta.jsx'
import { useSaved } from '../lib/saved.js'
import { applyFilters, describeFilters } from '../lib/search.js'
import { Button, Card, Empty, Loading, PageHeader, Section } from '../ui/index.jsx'

export default function Saved() {
  const { data: meta } = useMeta()
  const { data: open } = useJson('abiertas.json')
  const { list, remove, markSeen } = useSaved()
  const records = useMemo(() => (open && meta ? toRecords(open, meta.indice_campos) : null), [open, meta])

  return (
    <>
      <PageHeader eyebrow="Guardadas" title="Tus búsquedas">
        Se guardan solo en este navegador, sin cuenta ni correo. Cada vez que vuelvas te decimos
        cuántas convocatorias abiertas son nuevas desde tu última visita.
      </PageHeader>
      {!records && <Loading />}
      {records && list.length === 0 && (
        <Empty title="Aún no guardas búsquedas">
          En <Link className="text-accent" to="/buscar?estatus=abierta">Buscar</Link>, filtra por lo que vendes y usa “Guardar búsqueda”.
        </Empty>
      )}
      {records && list.length > 0 && (
        <div className="grid gap-3">
          {list.map((s) => {
            const filters = { ...s.filters, estatus: 'abierta' }
            const matches = applyFilters(records, filters, { buyers: meta.compradores })
            const fresh = matches.filter((r) => (r.primera_vez || '') > s.visto).length
            const params = new URLSearchParams(filters)
            return (
              <Card key={s.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="font-medium">{s.nombre}</div>
                  <div className="text-[13px] text-ink-3">{describeFilters(s.filters, meta)} · última visita {formatDate(s.visto)}</div>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-sm">
                    <span className="num font-medium">{formatNumber(matches.length)}</span> abiertas
                    {fresh > 0 && <span className="ml-2 rounded-full px-2 py-0.5 text-xs font-medium" style={{ color: 'var(--open)', background: 'var(--open-bg)' }}>{fresh} nuevas</span>}
                  </span>
                  <Button as={Link} size="sm" to={`/buscar?${params}`} onClick={() => markSeen(s.id)}>Ver</Button>
                  <Button variant="ghost" size="sm" onClick={() => remove(s.id)} aria-label={`Borrar ${s.nombre}`}>Borrar</Button>
                </div>
              </Card>
            )
          })}
        </div>
      )}
      <Section title="Recibirlas sin entrar al sitio">
        <Card className="p-5 text-sm leading-relaxed text-ink-2">
          Cada fuente y cada categoría tiene un feed Atom que puedes conectar a tu lector o a tu correo
          (por ejemplo con un servicio de RSS a email). El general es{' '}
          <a className="num text-accent hover:underline" href={feedUrl()}>feed.xml</a>; por categoría, cambia el final:{' '}
          <span className="num">feeds/valvulas.xml</span>, <span className="num">feeds/cfe.xml</span>, etcétera.
        </Card>
      </Section>
    </>
  )
}
