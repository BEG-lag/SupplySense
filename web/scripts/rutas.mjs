// GitHub Pages responde 404 (con el sitio) a cualquier ruta que no exista como archivo.
// Para que las páginas principales, las de cada estado y las de cada giro respondan 200 y se
// vean bien al compartirlas, se copia index.html en cada una con su propio título y
// descripción. Las de detalle (licitación, empresa, comprador) usan el 404.html.
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const dist = new URL('../dist/', import.meta.url).pathname
const base = readFileSync(join(dist, 'index.html'), 'utf8')
const fold = (t) => t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ñ/g, 'n')
const slugify = (t) => fold(t).replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
const esc = (t) => t.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')

function page(route, title, description) {
  let html = base.replace(/<title>[^<]*<\/title>/, `<title>${esc(title)}</title>`)
  if (description) {
    html = html.replace(/<meta name="description" content="[^"]*" \/>/, `<meta name="description" content="${esc(description)}" />`)
  }
  mkdirSync(join(dist, route), { recursive: true })
  writeFileSync(join(dist, route, 'index.html'), html)
}

const pages = [
  ['buscar', 'Buscar licitaciones · SupplySense'],
  ['ganadores', 'Ganadores · SupplySense'],
  ['precios', 'Precios por giro · SupplySense'],
  ['empresas', 'Empresas · SupplySense'],
  ['compradores', 'Compradores · SupplySense'],
  ['guardadas', 'Guardadas · SupplySense'],
  ['fuentes', 'Fuentes y método · SupplySense'],
  ['estados', 'Licitaciones por estado · SupplySense'],
]
for (const [route, title] of pages) page(route, title)

const metaPath = join(dist, 'data', 'meta.json')
if (existsSync(metaPath)) {
  const meta = JSON.parse(readFileSync(metaPath, 'utf8'))
  for (const c of meta.categorias) {
    const name = c.nombre.toLowerCase()
    page(`precios/${c.codigo}`, `Precios de ${name} · SupplySense`, `Cuánto se ha pagado en ${name} en las compras públicas de México: percentiles, tendencia y quién gana.`)
    page(`giro/${c.codigo}`, `Licitaciones de ${name} · SupplySense`, `Convocatorias abiertas de ${name} en el gobierno federal, CFE, PEMEX, Jalisco, CDMX y Campeche, con el rango de precios del giro.`)
  }
  for (const e of meta.entidades) {
    page(`estado/${slugify(e)}`, `Licitaciones abiertas en ${e} · SupplySense`, `Convocatorias abiertas en ${e}: dependencias federales, compras con dinero federal y CFE.`)
  }
}
copyFileSync(join(dist, 'index.html'), join(dist, '404.html'))
console.log('rutas con index.html propio: listo')
