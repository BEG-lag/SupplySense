// GitHub Pages responde 404 (con el sitio) a cualquier ruta que no exista como archivo.
// Para que las páginas principales respondan 200 (y se vean bien al compartirlas), se copia
// index.html en cada una. Las de detalle (licitación, empresa, comprador) usan el 404.html.
import { copyFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const dist = new URL('../dist/', import.meta.url).pathname
const index = join(dist, 'index.html')
const routes = ['buscar', 'ganadores', 'precios', 'empresas', 'compradores', 'guardadas', 'fuentes']
const precios = join(dist, 'data', 'precios.json')
if (existsSync(precios)) {
  for (const { codigo } of JSON.parse(readFileSync(precios, 'utf8'))) routes.push(`precios/${codigo}`)
}
for (const route of routes) {
  mkdirSync(join(dist, route), { recursive: true })
  copyFileSync(index, join(dist, route, 'index.html'))
}
copyFileSync(index, join(dist, '404.html'))
console.log(`rutas con index.html: ${routes.length}`)
