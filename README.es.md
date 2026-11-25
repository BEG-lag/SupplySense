<p align="center">
  <a href="https://pivotek.mx"><img src="assets/pivotek-logo.svg" alt="PIVOTEK" width="200"></a>
</p>

# SupplySense

<p><a href="README.md">English</a> · <b>Español</b></p>

**Licitaciones del gobierno de México, con lo que ya se pagó por lo mismo.** Cada mañana
SupplySense lee todas las convocatorias abiertas del gobierno federal en ComprasMX, más CFE y
PEMEX, y las cruza con más de 300 mil adjudicaciones: quién ganó, a qué precio y para qué
comprador. Energía y O&G es su vertical destacada. Cada registro liga a su fuente oficial.

**Sitio:** [beg-lag.github.io/SupplySense](https://beg-lag.github.io/SupplySense/) ·
**Feed:** [`feed.xml`](https://beg-lag.github.io/SupplySense/data/feed.xml) ·
**Fuentes:** [`docs/fuentes.md`](docs/fuentes.md)

## Contenido

| # | Sección | Estatus |
|---|---|---|
| 1 | [Qué hace](#1-qué-hace) | VERDE |
| 2 | [Fuentes](#2-fuentes) | VERDE (compras estatales con recursos propios: AMARILLO) |
| 3 | [Cómo funciona](#3-cómo-funciona) | VERDE |
| 4 | [Decisiones de datos y privacidad](#4-decisiones-de-datos-y-privacidad) | VERDE |
| 5 | [Correr en local](#5-correr-en-local) | VERDE |
| 6 | [Límites](#6-límites) | AMARILLO |
| 7 | [Licencia y aviso](#7-licencia-y-aviso) | VERDE |

## 1. Qué hace

- **Buscar convocatorias abiertas** por lo que vendes, con filtros por sector, fuente,
  comprador, estado, categoría y estatus. Los filtros viven en la URL, así que una búsqueda se comparte.
- **Ver el detalle** de cada procedimiento: fechas de junta, apertura y fallo, comprador, liga a
  la fuente y, lo propio de SupplySense, **cuánto se ha pagado en su categoría** y **qué
  procedimientos parecidos ya se adjudicaron, a quién y por cuánto**.
- **Precios por categoría** (35, en tres grupos: energía y O&G, salud y general): percentiles
  (P5 a P95) de más de 300 mil adjudicaciones, serie anual,
  concentración del mercado (HHI) y un comparador para ubicar un monto. No calcula
  "probabilidad de ganar".
- **Ganadores, empresas y compradores**: adjudicaciones recientes, historial de cada empresa y a
  quién le compra cada dependencia.
- **Búsqueda por giro y por significado**: "patrullas" también encuentra las convocatorias de
  vehículos (mismas reglas de clasificación del build y una lista de sinónimos), y las parecidas
  por significado salen de vectores de palabras entrenados con los títulos de unas 530 mil
  compras públicas. El modelo es un archivo del propio sitio y todo se calcula en el navegador.
- **Marco legal y calendario** en cada procedimiento: la ley aplicable que reporta la fuente (y el
  régimen propio de CFE y PEMEX, ligado a [leyes-mx](https://github.com/BEG-lag/leyes-mx)), qué
  significa el tipo de procedimiento y las fechas de junta, apertura y fallo. No es opinión legal.
- **Páginas por estado y por giro**, con título propio para compartirlas.
- **Búsquedas guardadas y seguimiento** de empresas, compradores y licitaciones, solo en el
  navegador: sin cuenta, sin correos y sin notificaciones; al volver ves qué cambió.

## 2. Fuentes

| Fuente | Semáforo | Qué aporta |
|---|---|---|
| CFE, Micrositio de Concursos | VERDE | Unos 115 mil procedimientos desde 2015 con estatus, ganador y monto; de los vigentes, fechas de apertura y fallo |
| PEMEX, concursos abiertos | VERDE | Unos 12 mil avisos por segmento; PEMEX no publica fecha límite, monto ni ganador |
| ComprasMX, datos abiertos | VERDE | Todos los expedientes (unos 180 mil) y contratos (unos 220 mil) 2025 y 2026 del gobierno federal y de estados y municipios con dinero federal |
| Tipo de cambio FIX | VERDE | Del repo [indicadores-mx](https://github.com/BEG-lag/indicadores-mx), para contratos en dólares |
| Compras estatales y municipales con recursos propios | AMARILLO | Portales locales aún no integrados |

El detalle de cada endpoint, formato y rareza está en [`docs/fuentes.md`](docs/fuentes.md).

## 3. Cómo funciona

```
GitHub Actions (06:30 CDMX)
  → supplysense update   lee CFE, PEMEX, ComprasMX y FIX, cada fuente aislada
  → data/*.jsonl         CFE y PEMEX por mes, versionados en git
  → data/vistos/*.tsv    ComprasMX: solo cuándo se vio cada registro (sus archivos van en caché)
  → supplysense build    reglas, estados unificados, DuckDB para percentiles
  → web/public/data      JSON para el sitio y feeds Atom
  → Vite + React         sitio estático en GitHub Pages
```

- **Sin servidor ni base de datos en línea.** El sitio es estático: no hay login, API ni llaves
  que proteger.
- **Fuentes aisladas y con freno.** Si una fuente falla se conserva lo último bueno; si trae menos
  del 70% de lo que había, se rechaza. El workflow avisa cuando una fuente lleva 3 días fallando.
- **Reglas legibles.** Compradores del sector, palabras de contexto, categorías, estatus y
  correcciones manuales viven en [`reglas/`](reglas/) como CSV. Cambiar una regla no exige volver
  a descargar nada: se aplica en `build`.
- **Pruebas.** `pytest` para fuentes (con fixtures), normalización, reglas, almacén, build y el
  dataset real; `vitest` para fechas, búsqueda y percentiles del sitio. CI con `ruff`.

```
src/supplysense/   cli, pipeline, store, http, text, dates, rules, build, feeds, sources/
reglas/            compradores_energia, alcance_palabras, categorias, estatus, correcciones
data/              procedimientos/AAAA/AAAA-MM.jsonl, contratos/…, estado_fuentes.json
web/               React 19 + Vite + Tailwind 4, marca PIVOTEK (Inter, JetBrains Mono, Cormorant Garamond)
tests/             pytest
```

## 4. Decisiones de datos y privacidad

- **Ganadores**: son públicos por ley y se muestran como los publica la fuente.
- **RFC**: solo se publica el de personas morales. El de personas físicas incluye su fecha de
  nacimiento y no se guarda; los RFC genéricos de extranjeros no se usan como clave.
- **Servidores públicos**: no se guardan el nombre ni el correo del operador de cada anuncio
  (ComprasMX) ni el contacto de PEMEX.
- **Estatus estimados** van marcados con asterisco: PEMEX se trata como abierto 30 días desde su
  publicación, y una convocatoria "vigente" cuya apertura ya pasó se muestra en evaluación.
- **Montos atípicos** (arriba del P99 de su categoría o debajo de $10,000) se excluyen de los
  precios. Los contratos en dólares se convierten con el FIX del día de firma.

## 5. Correr en local

```bash
uv sync
uv run supplysense update          # lee las fuentes (unos 2 minutos)
uv run supplysense build           # genera web/public/data
cd web && npm install && npm run dev
```

Pruebas: `uv run pytest`, `uv run ruff check .`, `cd web && npm test`.

## 6. Límites

- La clasificación por categoría es por palabras clave: orienta, no es infalible.
- Un monto de CFE es por procedimiento y puede cubrir varias partidas o ganadores.
- ComprasMX cubre 2025 y 2026; el histórico más largo de precios es el de CFE (desde 2015).
- El build lee unos 530 mil registros: tarda unos 4 minutos y usa unos 3.5 GB de memoria.
- [SUPUESTO] Los 30 días de "abierto" de PEMEX son una estimación; confirma fechas en SISCeP.

## 7. Licencia y aviso

Código bajo licencia [MIT](LICENSE). Los datos son información pública de CFE, PEMEX y la
Secretaría Anticorrupción y Buen Gobierno (ComprasMX); se citan con su fuente.

Este proyecto no constituye opinión legal ni asesoría fiscal. Antes de participar en un
procedimiento, valida bases, fechas y requisitos en la fuente oficial.

Hecho por [Benjamín Esponda García](https://pivotek.mx).
