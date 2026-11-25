import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { feedUrl } from '../lib/data.js'
import { formatDate } from '../lib/format.js'
import { useMeta } from '../lib/meta.jsx'
import { useFollowed } from '../lib/follow.js'
import { useSaved } from '../lib/saved.js'
import { cx } from '../ui/index.jsx'

const NAV = [
  { to: '/buscar', label: 'Buscar' },
  { to: '/ganadores', label: 'Ganadores' },
  { to: '/precios', label: 'Precios' },
  { to: '/empresas', label: 'Empresas' },
  { to: '/compradores', label: 'Compradores' },
  { to: '/fuentes', label: 'Fuentes' },
]

function Mark({ className = 'h-7 w-7' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect width="32" height="32" rx="8" fill="var(--lime)" />
      <path d="M9 20.5c1.4 1.3 3.5 2 5.8 2 3.3 0 5.4-1.5 5.4-3.9 0-2.2-1.6-3.1-4.6-3.7l-1.6-.3c-1.6-.3-2.2-.8-2.2-1.6 0-1 .9-1.6 2.5-1.6 1.6 0 3 .6 4 1.6l1.6-2c-1.3-1.2-3.2-1.9-5.5-1.9-3.1 0-5.2 1.6-5.2 3.9 0 2.1 1.5 3.2 4.4 3.7l1.6.3c1.7.3 2.4.8 2.4 1.7 0 1.1-1 1.7-2.7 1.7-1.9 0-3.4-.7-4.5-1.8z" fill="var(--ink)" />
    </svg>
  )
}

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="SupplySense, inicio">
      <Mark />
      <span className="font-mono text-[12.5px] tracking-[0.14em] text-ink">SUPPLYSENSE</span>
    </Link>
  )
}

function Header() {
  const [open, setOpen] = useState(false)
  const { list } = useSaved()
  const { list: followed } = useFollowed()
  const savedCount = list.length + followed.length
  const location = useLocation()
  const pill = ({ isActive }) => cx(
    'rounded-full px-3.5 py-1.5 text-[13.5px] transition-colors',
    isActive ? 'bg-accent text-accent-ink font-semibold' : 'text-ink-2 hover:bg-muted hover:text-ink',
  )
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-[rgba(10,12,16,0.82)] backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Brand />
        <nav className="ml-auto hidden items-center gap-0.5 rounded-full border border-line bg-subtle p-1 lg:flex" aria-label="Principal">
          {NAV.map((n) => <NavLink key={n.to} to={n.to} className={pill}>{n.label}</NavLink>)}
        </nav>
        <div className="ml-auto flex items-center gap-2 lg:ml-2">
          <NavLink to="/guardadas" className={({ isActive }) => cx(
            'rounded-full border px-3.5 py-1.5 text-[13.5px] transition-colors',
            isActive ? 'border-accent text-accent' : 'border-line text-ink-2 hover:border-accent hover:text-accent',
          )}>
            Guardadas{savedCount > 0 && <span className="num ml-1.5">{savedCount}</span>}
          </NavLink>
          <button
            type="button"
            className="rounded-full border border-line px-3.5 py-1.5 text-[13.5px] text-ink-2 lg:hidden"
            aria-expanded={open}
            aria-controls="menu-movil"
            onClick={() => setOpen((o) => !o)}
          >
            Menú
          </button>
        </div>
      </div>
      {open && (
        <nav id="menu-movil" key={location.pathname} className="flex flex-wrap gap-1 border-t border-line px-4 py-3 lg:hidden" aria-label="Principal">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} className={pill} onClick={() => setOpen(false)}>{n.label}</NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}

function Footer() {
  const { data: meta } = useMeta()
  const link = 'text-ink-2 underline decoration-line-strong underline-offset-4 hover:text-accent hover:decoration-accent'
  return (
    <footer className="mt-24 border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 text-sm sm:grid-cols-3 sm:px-6">
        <div>
          <Brand />
          <p className="mt-4 leading-relaxed text-ink-2">
            Licitaciones del gobierno de México, con una vertical de energía y O&amp;G:
            convocatorias abiertas, ganadores y precios históricos, cada uno con liga a su fuente.
          </p>
          {meta && (
            <p className="eyebrow mt-4 flex items-center gap-2">
              <span className="live" aria-hidden /> Datos al {formatDate(meta.generado)} · cada mañana
            </p>
          )}
        </div>
        <div>
          <p className="eyebrow mb-3">Fuentes</p>
          <ul className="space-y-1.5">
            <li><a className={link} href="https://comprasmx.buengobierno.gob.mx/datos-abiertos" rel="noreferrer" target="_blank">ComprasMX, datos abiertos</a></li>
            <li><a className={link} href="https://msc.cfe.mx/Aplicaciones/NCFE/Concursos/" rel="noreferrer" target="_blank">CFE, Micrositio de Concursos</a></li>
            <li><a className={link} href="https://www.pemex.com/procura/procedimientos-de-contratacion/concursosabiertos/Paginas/default.aspx" rel="noreferrer" target="_blank">PEMEX, concursos abiertos</a></li>
            <li><Link className={link} to="/estados">Convocatorias por estado</Link></li>
            <li><a className={link} href={feedUrl()}>Feed Atom de convocatorias</a></li>
          </ul>
        </div>
        <div>
          <p className="eyebrow mb-3">Aviso</p>
          <p className="leading-relaxed text-ink-2">
            Información pública reunida automáticamente. No constituye opinión legal ni asesoría
            fiscal: valida bases, fechas y requisitos en la fuente oficial antes de participar.
          </p>
          <p className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="lights" aria-hidden><i /><i /><i /></span>
            <span className="text-ink-2">Un proyecto de</span>
            <a className={link} href="https://pivotek.mx" rel="noreferrer" target="_blank">Benjamín Esponda García · PIVOTEK</a>
            <span className="text-ink-3">·</span>
            <a className={link} href="https://github.com/BEG-lag/SupplySense" rel="noreferrer" target="_blank">Código</a>
          </p>
        </div>
      </div>
    </footer>
  )
}

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-full focus:bg-accent focus:px-4 focus:py-2 focus:text-accent-ink">Saltar al contenido</a>
      <Header />
      <main id="contenido" className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-12">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
