// Modo sin conexión de SupplySense. Guarda en este navegador lo que ya visitaste (la aplicación
// y los datos que consultaste) para poder verlo sin internet. No envía nada a ningún servidor:
// solo repite las mismas peticiones al sitio y conserva las respuestas en la caché local.
const VERSION = 'v1'
const SHELL = `supplysense-app-${VERSION}`
const DATA = `supplysense-datos-${VERSION}`
const BASE = new URL('./', self.location).pathname // "/SupplySense/"
const MAX_DATA = 40 // archivos de datos guardados como máximo (los más viejos salen primero)

const PRECACHE = [
  BASE,
  `${BASE}manifest.webmanifest`,
  `${BASE}favicon.svg`,
  `${BASE}icons/icon-192.png`,
  `${BASE}pivotek-logotipo-naranja.svg`,
  `${BASE}pivotek-isotipo-naranja.svg`,
  `${BASE}data/meta.json`,
  `${BASE}data/abiertas.json`,
]

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const shell = await caches.open(SHELL)
    await shell.addAll(PRECACHE.filter((u) => !u.includes('/data/')))
    // El código va con nombre versionado: se toma de la página de inicio recién bajada.
    const html = await (await shell.match(BASE)).text()
    const assets = [...new Set(html.match(new RegExp(`${BASE}assets/[^"']+`, 'g')) || [])]
    await shell.addAll(assets)
    const data = await caches.open(DATA)
    await data.addAll(PRECACHE.filter((u) => u.includes('/data/')))
  })())
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keep = new Set([SHELL, DATA])
    for (const name of await caches.keys()) {
      if (name.startsWith('supplysense-') && !keep.has(name)) await caches.delete(name)
    }
    await self.clients.claim()
  })())
})

async function trim(cache) {
  const keys = await cache.keys()
  for (const req of keys.slice(0, Math.max(0, keys.length - MAX_DATA))) await cache.delete(req)
}

// Datos: primero la red (se actualizan cada mañana); sin conexión, la última copia guardada.
async function networkFirst(request) {
  const cache = await caches.open(DATA)
  try {
    const response = await fetch(request)
    if (response.ok) {
      await cache.delete(request) // reinsertar para que cuente como reciente
      await cache.put(request, response.clone())
      trim(cache)
    }
    return response
  } catch {
    const cached = await cache.match(request)
    if (cached) return cached
    throw new Error('sin conexión y sin copia guardada')
  }
}

// Código con nombre versionado: si ya está guardado no cambia.
async function cacheFirst(request) {
  const cache = await caches.open(SHELL)
  const cached = await cache.match(request)
  if (cached) return cached
  const response = await fetch(request)
  if (response.ok) cache.put(request, response.clone())
  return response
}

// Páginas: la red manda (GitHub Pages responde 404 con la aplicación en rutas de detalle, y eso
// también sirve); sin conexión, la aplicación guardada resuelve la ruta en el navegador.
async function page(request) {
  try {
    return await fetch(request)
  } catch {
    const shell = await caches.open(SHELL)
    return (await shell.match(BASE)) || Response.error()
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) return
  if (request.mode === 'navigate') return event.respondWith(page(request))
  if (url.pathname.startsWith(`${BASE}data/`)) return event.respondWith(networkFirst(request))
  if (url.pathname.startsWith(`${BASE}assets/`) || /\.(svg|png|webmanifest)$/.test(url.pathname)) {
    return event.respondWith(cacheFirst(request))
  }
})
