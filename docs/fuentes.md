# Fuentes de SupplySense

Cada registro del sitio liga a su fuente oficial. Este documento dice de dónde sale cada dato, cómo se lee y qué limitaciones tiene. Prueba inicial: 25 de noviembre de 2026.

| Fuente | Semáforo | Qué aporta | Volumen al 25-11-2026 |
|---|---|---|---|
| CFE, Micrositio de Concursos | VERDE | Convocatorias vigentes, ganadores y montos desde 2015 | 114,970 procedimientos; 608 vigentes en la fuente (406 con apertura aún por venir); 88,153 adjudicados con monto |
| PEMEX, concursos abiertos | VERDE | Avisos de concursos de PEMEX por segmento | 11,926 avisos desde 2015; sin fecha límite, montos ni ganadores |
| ComprasMX, datos abiertos | AMARILLO | Procedimientos y contratos de IMP, CENACE, CENAGAS, SENER, INEEL, ASEA, CNE y CONUEE | 2026: unos 1,100 procedimientos y 1,000 contratos de energía; unos 25 abiertos |
| Campeche | AMARILLO | Filtro por entidad sobre las tres fuentes; el canal estatal propio no está identificado | [BRECHA DE DATO] |
| Tipo de cambio FIX | VERDE | Conversión de contratos en dólares | Serie diaria desde 1991, del repo indicadores-mx |

## CFE: Micrositio de Concursos (msc.cfe.mx)

- **Listado**: `POST https://msc.cfe.mx/Aplicaciones/NCFE/Concursos/Procedure/getProcBusqueda` con el token antifalsificación que trae la página `GET /Aplicaciones/NCFE/Concursos/` (misma sesión). Con los filtros en su valor por omisión (`IdEntidadFederativa=0`, `EstadoProcedimientoContratacionClave=0`, `TestigoSocial=2`, `idCaracterProcedimiento=0`, `Modalidad=0`, el resto vacío) devuelve **todo el histórico** en un solo JSON (unos 25 s).
- **Campos**: `Id`, `Numero`, `Descripcion`, `EstadoProcedimiento` (Vigente, Adjudicado, Desierto, Cancelado, Suspendido, Concluido, Contrato Sin Formalizar), `EntidadFederativa`, `TipoProcedimientoClave`, `TipoContratacionClave`, `FechaPublicacion` (formato `/Date(ms)/`), `NombProveedorAdjudicado` (varios separados por coma), `MONTO` (pesos), `FechaLimiteOfertas` y `FechaFallo` (vacíos en el listado).
- **Detalle**: `POST Procedure/Details` con `id` y el token. Trae la empresa de CFE (por ejemplo "0100 - CFE Distribución"), anexos y las fechas de apertura técnica, apertura económica y fallo. No tiene URL pública directa: el sitio liga al buscador de CFE y muestra el número para copiarlo. Las fechas se leen solo de los vigentes nuevos o modificados.
- **Montos**: el 100% de los adjudicados de octubre de 2026 traen monto.

## PEMEX: concursos abiertos (SharePoint)

- `GET https://www.pemex.com/procura/procedimientos-de-contratacion/concursosabiertos/_api/web/lists/getbytitle('<lista>')/items` con `Accept: application/json;odata=verbose`, sin login. Paginación con `d.__next`.
- **Listas** (registros totales): Concursos-Abiertos-PTI (8,488), -PEP (2,099), Concursos-e-invitaciones (611), -PL (492), -PE (181), -PF (48), -PPS (17), -PCS (1).
- **Campos**: `Id`, `Title` (número del procedimiento), `descripcion`, `inicio`, `vencimiento`, `tipoevento`, `tiposuministro`, `areacontratante`, `Created`, `Modified`.
- **Límites**: no publica montos ni ganadores; PEMEX no aparece en ComprasMX.
- **`vencimiento` no es la fecha límite**: es el retiro del aviso, casi siempre un año después de publicado (1,959 de 2,099 avisos de PEP). Por eso el sitio trata un aviso de PEMEX como abierto durante 30 días desde su publicación [SUPUESTO] y lo marca como estimado; la fecha real está en la convocatoria o en SISCeP (`ID_SISCEP`).
- No se guarda el campo `contacto` (correo de un servidor público).

## ComprasMX: datos abiertos

- **Archivos**: `GET https://upcp-cnetservicios.buengobierno.gob.mx/norah/documentos/recursos/lck/expedientes/obtener/{Expedientes|Contratos}_ComprasMX_{AAAA}.csv`. Responde a GET sin navegador; a HEAD responde 403. Tamaños: expedientes 2026, 98 MB; contratos 2026, 111 MB; contratos 2025, 158 MB.
- **Codificación**: mayormente latin-1 con secuencias UTF-8 sueltas y algunas palabras corruptas desde el origen ("MONSEÃOR"). Se decodifica en modo mixto y se repara con una tabla.
- **Expedientes** (38 columnas): estatus (ADJUDICADO, VIGENTE, EN APERTURA, EN ACLARACIONES, PENDIENTE DE APERTURA, DESIERTO, CANCELADO…), fechas de publicación, junta de aclaraciones, apertura y fallo, y `Dirección del anuncio` con la liga al detalle.
- **Contratos** (73 columnas): proveedor, RFC, montos sin impuestos mínimo y máximo, moneda (MXN, USD, EUR), fechas de firma, inicio y fin.
- **Límites**: CFE y PEMEX no publican aquí. En 2026 el filtro por institución de energía deja unos 1,100 procedimientos y 1,000 contratos.

## Campeche

- Lo que pasa por ComprasMX y CFE se filtra por `Entidad Federativa`. PEMEX no da entidad; su lista PEP (Exploración y Producción) concentra lo de la Sonda de Campeche.
- [BRECHA DE DATO] El canal oficial de las compras estatales con recursos propios no está identificado.

## Advertencia

SupplySense reúne información pública para consulta. No constituye opinión legal ni asesoría fiscal; antes de participar en un procedimiento, valida bases, fechas y requisitos en la fuente oficial.
