import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { feedUrl } from '../lib/data.js'
import { formatDate } from '../lib/format.js'
import { useMeta } from '../lib/meta.jsx'
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

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 font-semibold tracking-[-0.02em]" aria-label="SupplySense, inicio">
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden>
        <rect width="32" height="32" rx="7" fill="var(--accent)" />
        <path d="M9 20.5c1.4 1.3 3.5 2 5.8 2 3.3 0 5.4-1.5 5.4-3.9 0-2.2-1.6-3.1-4.6-3.7l-1.6-.3c-1.6-.3-2.2-.8-2.2-1.6 0-1 .9-1.6 2.5-1.6 1.6 0 3 .6 4 1.6l1.6-2c-1.3-1.2-3.2-1.9-5.5-1.9-3.1 0-5.2 1.6-5.2 3.9 0 2.1 1.5 3.2 4.4 3.7l1.6.3c1.7.3 2.4.8 2.4 1.7 0 1.1-1 1.7-2.7 1.7-1.9 0-3.4-.7-4.5-1.8z" fill="var(--accent-ink)" />
      </svg>
      <span className="text-[17px]">SupplySense</span>
    </Link>
  )
}

function Header() {
  const [open, setOpen] = useState(false)
  const { list } = useSaved()
  const location = useLocation()
  const link = ({ isActive }) => cx(
    'rounded-md px-2.5 py-1.5 text-[14px] transition-colors',
    isActive ? 'bg-subtle text-ink' : 'text-ink-2 hover:text-ink',
  )
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Logo />
        <nav className="ml-2 hidden items-center gap-0.5 md:flex" aria-label="Principal">
          {NAV.map((n) => <NavLink key={n.to} to={n.to} className={link}>{n.label}</NavLink>)}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <NavLink to="/guardadas" className={link}>
            Guardadas{list.length > 0 && <span className="num ml-1 text-ink-3">{list.length}</span>}
          </NavLink>
          <button
            type="button"
            className="rounded-md px-2.5 py-1.5 text-[14px] text-ink-2 md:hidden"
            aria-expanded={open}
            aria-controls="menu-movil"
            onClick={() => setOpen((o) => !o)}
          >
            Menú
          </button>
        </div>
      </div>
      {open && (
        <nav id="menu-movil" key={location.pathname} className="border-t border-line px-4 py-2 md:hidden" aria-label="Principal">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => cx(link({ isActive }), 'block')} onClick={() => setOpen(false)}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}

function Footer() {
  const { data: meta } = useMeta()
  return (
    <footer className="mt-20 border-t border-line bg-subtle">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 text-sm text-ink-2 sm:grid-cols-3 sm:px-6">
        <div>
          <Logo />
          <p className="mt-3 leading-relaxed">
            Licitaciones de energía y O&amp;G en México: convocatorias abiertas, ganadores y precios
            históricos, cada uno con liga a su fuente oficial.
          </p>
          {meta && <p className="mt-3 text-ink-3">Datos al {formatDate(meta.generado)}. Se actualiza cada mañana.</p>}
        </div>
        <div>
          <p className="font-medium text-ink">Fuentes</p>
          <ul className="mt-2 space-y-1">
            <li><a className="hover:text-ink" href="https://msc.cfe.mx/Aplicaciones/NCFE/Concursos/" rel="noreferrer" target="_blank">CFE, Micrositio de Concursos</a></li>
            <li><a className="hover:text-ink" href="https://www.pemex.com/procura/procedimientos-de-contratacion/concursosabiertos/Paginas/default.aspx" rel="noreferrer" target="_blank">PEMEX, concursos abiertos</a></li>
            <li><a className="hover:text-ink" href="https://comprasmx.buengobierno.gob.mx/datos-abiertos" rel="noreferrer" target="_blank">ComprasMX, datos abiertos</a></li>
            <li><a className="hover:text-ink" href={feedUrl()}>Feed Atom de convocatorias</a></li>
          </ul>
        </div>
        <div>
          <p className="font-medium text-ink">Aviso</p>
          <p className="mt-2 leading-relaxed">
            Información pública reunida automáticamente. No constituye opinión legal ni asesoría
            fiscal: valida bases, fechas y requisitos en la fuente oficial antes de participar.
          </p>
          <p className="mt-3">
            Hecho por <a className="text-ink underline-offset-2 hover:underline" href="https://pivotek.mx" rel="noreferrer" target="_blank">Benjamín Esponda García</a> ·{' '}
            <a className="text-ink underline-offset-2 hover:underline" href="https://github.com/BEG-lag/SupplySense" rel="noreferrer" target="_blank">Código</a>
          </p>
        </div>
      </div>
    </footer>
  )
}

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded focus:bg-bg focus:px-3 focus:py-2">Saltar al contenido</a>
      <Header />
      <main id="contenido" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
