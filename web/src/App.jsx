import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import { MetaProvider } from './lib/meta.jsx'
import { Buyer, BuyersIndex } from './pages/Buyers.jsx'
import { CompaniesIndex, Company } from './pages/Companies.jsx'
import Home from './pages/Home.jsx'
import Saved from './pages/Saved.jsx'
import Search from './pages/Search.jsx'
import Sources from './pages/Sources.jsx'
import Tender from './pages/Tender.jsx'
import Winners from './pages/Winners.jsx'
import { Empty, Loading } from './ui/index.jsx'

// Las gráficas (recharts) solo se cargan en Precios.
const PricesIndex = lazy(() => import('./pages/Prices.jsx').then((m) => ({ default: m.PricesIndex })))
const PriceCategory = lazy(() => import('./pages/Prices.jsx').then((m) => ({ default: m.PriceCategory })))

const TITLES = {
  '/': 'SupplySense · Licitaciones del gobierno de México',
  '/buscar': 'Buscar · SupplySense',
  '/ganadores': 'Ganadores · SupplySense',
  '/precios': 'Precios · SupplySense',
  '/empresas': 'Empresas · SupplySense',
  '/compradores': 'Compradores · SupplySense',
  '/guardadas': 'Guardadas · SupplySense',
  '/fuentes': 'Fuentes y método · SupplySense',
}

function ScrollAndTitle() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
    if (TITLES[pathname]) document.title = TITLES[pathname]
  }, [pathname])
  return null
}

function NotFound() {
  return <Empty title="Esta página no existe"><Link className="text-accent" to="/">Ir al inicio</Link></Empty>
}

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '')}>
      <MetaProvider>
        <ScrollAndTitle />
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="buscar" element={<Search />} />
            <Route path="licitacion/:id" element={<Tender />} />
            <Route path="ganadores" element={<Winners />} />
            <Route path="precios" element={<Suspense fallback={<Loading />}><PricesIndex /></Suspense>} />
            <Route path="precios/:codigo" element={<Suspense fallback={<Loading />}><PriceCategory /></Suspense>} />
            <Route path="empresas" element={<CompaniesIndex />} />
            <Route path="empresa/:id" element={<Company />} />
            <Route path="compradores" element={<BuyersIndex />} />
            <Route path="comprador/:id" element={<Buyer />} />
            <Route path="guardadas" element={<Saved />} />
            <Route path="fuentes" element={<Sources />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </MetaProvider>
    </BrowserRouter>
  )
}
