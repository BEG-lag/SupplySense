# Fuentes de SupplySense

Cada registro del sitio liga a su fuente oficial. Este documento dice de dónde sale cada dato, cómo se lee y qué limitaciones tiene. Prueba inicial: 25 de noviembre de 2026.

| Fuente | Semáforo | Qué aporta | Volumen al 25-11-2026 |
|---|---|---|---|
| CFE, Micrositio de Concursos | VERDE | Convocatorias vigentes, ganadores y montos desde 2015 | 114,970 procedimientos; 608 vigentes en la fuente (406 con apertura aún por venir); 88,153 adjudicados con monto |
| PEMEX, concursos abiertos | VERDE | Avisos de concursos de PEMEX por segmento | 11,926 avisos desde 2015; sin fecha límite, montos ni ganadores |
| ComprasMX, datos abiertos | VERDE | Todos los procedimientos y contratos federales (y estatales con dinero federal) | 2025 y 2026: 183 mil expedientes y 222 mil contratos; unos 1,080 abiertos |
| Jalisco | VERDE | Compras estatales con recursos propios | Unas 60 abiertas a la vez; historial desde 2022 en el portal |
| CDMX | VERDE | Concurso Digital: convocatorias de dependencias locales | Unas 1,500 al año [ESTIMADO]; pocas abiertas a la vez |
| Campeche | AMARILLO | Licitaciones estatales de SAFIN, desde los PDF | 336 convocatorias de 2022 a 2026 |
| Guanajuato | VERDE | Licitaciones, invitaciones y adjudicaciones del gobierno estatal (portal de transparencia) | 2,623 registros desde 2021; unos 365 al año |
| Nuevo León, subastas | VERDE | Subastas electrónicas inversas con precio base, ganador, mejor oferta y participantes | 521 subastas desde 2016; unas 30 al año |
| Banxico | VERDE | Licitaciones e invitaciones con calendario de etapas | 923 procedimientos desde 2021 |
| Poder Judicial (OAJ) | VERDE | Convocatorias de Recursos Materiales e Inmuebles; compra también para SCJN y TEPJF | Unas 90 al año |
| DOF, sección de concursos | AMARILLO | Resúmenes de licitaciones públicas de quien no publica en ComprasMX (universidades, INE, Diputados, estados, municipios) | 60 a 140 notas por edición, la mayoría ya en ComprasMX |
| Estado de México | ROJO | COMPRAMEX (JSF/PrimeFaces) | Pendiente |
| Tabasco | ROJO | Portal estatal sin respuesta | Pendiente |
| Nuevo León, licitaciones | ROJO | nl.gob.mx rechaza a lectores automáticos (HTTP 403) | No se lee: se respeta el bloqueo |
| Veracruz y TEPJF | ROJO | Verificación anti-robots (CAPTCHA) | No se lee; lo que publican en el DOF o con dinero federal sí aparece |
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
- **Límites**: CFE y PEMEX no publican aquí. La vertical de energía (IMP, CENACE, CENAGAS, SENER, INEEL, ASEA, CNE, CONUEE y palabras de contexto) es de unos 1,100 procedimientos y 1,000 contratos al año.
- **Almacenamiento**: los archivos son fotos completas de cada año, así que no se guardan en git. Se bajan cada día (el año anterior, los lunes), se validan columnas y volumen antes de sustituir los de la caché de Actions, y en `data/vistos/` solo se registra cuándo se vio cada registro por primera vez.

## Portales estatales (compras con recursos propios)

Los portales estatales solo muestran lo vigente: lo que sale del listado se conserva con su último estado y el estatus se estima por fechas (pasada la apertura, "en evaluación"; pasado el fallo, "concluida"). Lo que trae número federal ya viene de ComprasMX y se descarta para no duplicar. No se guardan nombres de servidores públicos ni datos bancarios.

### Jalisco

- **Listado**: `GET https://compras.jalisco.gob.mx/requisition/tree?tender_stage=<etapa>&step=500`, con etapas `posted`, `in_clarification_meeting`, `in_evaluation` y `cancelled`. Tabla HTML con celdas identificadas (`stage-cell`, `code-cell`, `responsible-unit-cell`, `description-cell`, `character-cell`, `published-cell`).
- **Detalle**: `/requisition/view/{id}`, con "Calendario de Actividades" (junta aclaratoria, presentación y apertura de propuestas, fallo). Se lee para las abiertas, a lo más una vez por semana.

### Ciudad de México

- **Listado**: `GET https://concursodigital.finanzas.cdmx.gob.mx/convocatorias_publicas` (el host `panel.concursodigital.cdmx.gob.mx` tiene un certificado que no cubre su nombre).
- **Detalle**: `/proveedores/detalle_convocatoria/{base64(id)}`, con ids consecutivos: cada día se avanza desde el último conocido hasta dejar de encontrar. Trae unidad convocante, método, tipo, carácter, número y fechas de junta, apertura y fallo.

### Campeche

- **Listado**: `GET https://safin.campeche.gob.mx/convocatorias/estatales?limit=0` (descargas de Joomla). Las de `/convocatorias/nacionales` ya están en ComprasMX.
- **PDF**: texto digital; se extraen número, objeto, dependencia que solicita, ley estatal aplicable, fecha límite de registro y venta de bases, junta de aclaraciones y apertura.
- Lo que pasa por ComprasMX y CFE en Campeche se ve con el filtro de entidad; PEMEX no da entidad (su lista PEP concentra lo de la Sonda de Campeche).

### Guanajuato

- **Listado**: `GET https://transparencia.guanajuato.gob.mx/transparencia/data/licitacion.php?limit=500&offset=N` (con `palabraclave`, `dependencia`, `materia`, `tipolicitacion` y `anio` vacíos). JSON `{total, rows}`, lo más nuevo primero; **sin** `sort` (con él se invierte). Cada fila trae número, objeto (`finalidad`), dependencia, tipo, materia, fecha y los nombres de archivo de convocatoria, junta, apertura y fallo en `/biblioteca_digital/docart10/`.
- **Estatus**: con acta de fallo, concluida; con acta de apertura, en evaluación; si no, abierta hasta la fecha de apertura de la convocatoria o 30 días tras publicarse [SUPUESTO]. Las adjudicaciones directas se registran como concluidas.
- **Fechas**: de las recientes sin actas se lee la convocatoria. La Secretaría de Finanzas la publica dentro de un ZIP de 40 a 70 MB: el servidor acepta `Range`, así que se lee el directorio central y se baja solo el `*-C.pdf` (unos 200 KB). De ahí salen junta, apertura, fallo, fecha límite de bases, ley y origen de los recursos. Lo que dice "procedencia de los recursos: Federal" se descarta porque está en ComprasMX, igual que la "Licitación Pública Federal" y los números LA-, LO-, IA-.
- Las convocatorias de Educación están escaneadas y no dan fechas. SICOM (obra carretera) no publica aquí desde 2024 [BRECHA DE DATO].

### Nuevo León

- **Subastas**: `GET https://subasta.nl.gob.mx/monitoreosubastas.asp`, una sola página (cp1252 sin declarar, con comentarios HTML que se quitan) con las 521 subastas desde 2016: número, objeto con "SOLICITADO POR <dependencia>", fecha y las actas en `/docs/{tipo}_{id}.pdf`.
- **Detalle**: `monitoreopartidassubasta.asp?ids=N`: estatus ("Registro" mientras se inscriben, "Cerrada" al terminar), precio base por partida, ganador con su mejor oferta y proveedores participantes. Con ganador, el monto entra a precios y ganadores igual que CFE. Se lee el de las recientes que no han terminado.
- **Licitaciones de nl.gob.mx**: responden 403 a un lector que se identifica como tal; no se intenta saltar el bloqueo. Agua y Drenaje de Monterrey publica PDF escaneados.

## Organismos fuera de ComprasMX

### Banco de México

- **Listado**: `POST https://www.banxico.org.mx/PortalProveedores/ConsultaProcedimientos` (en curso) y `ConsultaProcedimientosCerrados` (desde 2021), con `BMXC_materia` 1, 2 o 3 y los demás filtros vacíos. JSON en ISO-8859-1 sin declararlo.
- **Estatus**: `A` abierta, `L` en evaluación (ya se abrieron propuestas), `F` fallo publicado, `C` concluido; con motivo de cancelación, cancelada.
- **Etapas**: `POST ConsultaEtapas` con `BMXC_idProcedimiento`: aclaraciones, apertura, fallo y firma. Ganador y monto solo en actas PDF [BRECHA DE DATO].

### Órgano de Administración Judicial

- **Listado**: fragmentos de tabla `https://www.oaj.gob.mx/include/convocatorias/dgrm{AAAA}.html` y `dgim{AAAA}.html` que cargan las páginas `convocatoriasDGRMSG.htm` y `licitacionesDGIM.htm`. Número, documentos, fecha de publicación y objeto.
- **Estatus**: con acta de fallo, concluida; "(CANCELADA)" en el número, cancelada; si no, se estima por la fecha de publicación (30 días). Los ZIP de bases (hasta 516 MB) no se bajan.

### DOF, convocatorias

- **Notas**: `GET https://sidof.segob.gob.mx/dof/sidof/notas/DD-MM-AAAA` (JSON de la edición); se toman las de `codOrgaUno == "CV"`. **Detalle**: `GET https://sidof.segob.gob.mx/notas/docFuente/{codNota}`.
- **Formatos**: tabla de dos columnas (dato y valor), tabla con encabezados en un renglón y valores en el siguiente, o texto corrido. El DOF corta palabras y números con espacios ("diciembr e", "20 26"): las fechas se leen con el texto compactado.
- **Duplicados**: se descarta la nota si trae un número de ComprasMX (LA-, LO-, IA-…) o si el convocante es CFE o PEMEX, y en el build, la que repite el número de un portal que ya leemos (Banxico, OAJ). No se guardan los nombres de quien firma.
- Cada día se leen las ediciones de los últimos 3 días (las notas ya leídas no se vuelven a pedir; las descartadas sí, unas 200 peticiones); la carga inicial, 45.

### Pendientes

- **Estado de México** (AMARILLO, revisado el 26-11-2026): COMPRAMEX (`compramex.edomex.gob.mx/compramex/public/catalogosExternos/procedimientsoAdquisitivos.xhtml`) es JSF/PrimeFaces, pero sí tiene lista global. Con "Unidad administrativa = 0" trae todo un tipo de organismo (3 auxiliares, 1 municipios, 5 autónomos; el 6, sector central, exige estatus 1 a 4). Receta: GET por `javax.faces.ViewState`; POST AJAX `change` de `formulario:slTipoOrganismo` (salvo tipo 6); POST `formulario:btnFiltrar` (da `rowCount` y el id de la tabla); POST AJAX de paginación con `_rows` igual a `rowCount` (1,671 filas en una respuesta). Solo el año en curso; el histórico está en `historico/historicoProcedimientos.xhtml`. Problemas: filas que son documentos ("ACTA…", "FALLO…") y números repetidos; la dependencia no aparece (se deduce del prefijo: ISEM-, ISSEMYM, JCEM, DIFEM); solo el sector central tiene estatus confiable y PDF con texto. **Un firewall corta la conexión por volumen acumulado** (unas 130 peticiones en 20 minutos bastaron para un bloqueo de más de 20 minutos): presupuesto diario de unas 20 peticiones de lista y 40 de detalle [ESTIMADO].
- **Tabasco** (AMARILLO, revisado el 26-11-2026): el iframe viejo (`187.157.9.81`) está muerto. Su reemplazo es Compranet 3.0 de la Secretaría Anticorrupción y Buen Gobierno estatal: `https://portalanticorrupcion.tabasco.gob.mx:85/compranet/Publico/Licitacion_Adquisiciones/Adq_{Vigentes,Seguimiento,Fallos,Contratos}.aspx` y `Licitacion_Obra_Pub/Obra_Pub_*.aspx`. ASP.NET WebForms con DevExpress: dos GET (el primero crea la sesión), paginación por POST con `__EVENTTARGET=ctl00$ContentPlaceHolder1$grd_licitaciones` y `__EVENTARGUMENT=12|PAGERONCLICK3|PN<k>`; año con `chklist_anio`. 2026: 59 de adquisiciones y 25 de obra; contratos con proveedor e importe (130 en 2025). Objeto y fechas solo en PDF escaneado con OCR; el Periódico Oficial (`tabasco.gob.mx/PeriodicoOficial/resultado/LICITACI/0?page=N`) da convocante y objeto en la lista.
- **SCJN**: su página de vigentes trae uno o dos procedimientos; sus licitaciones públicas salen en el DOF y muchas compras las hace el OAJ.
- **INE, UNAM y Cámara de Diputados**: sus licitaciones públicas entran por el DOF; sus portales propios (Elementor, certificado incompleto y Oracle APEX) quedan para después.
- **Veracruz y TEPJF**: protegidos con verificación anti-robots; no se intenta saltarla.

## Advertencia

SupplySense reúne información pública para consulta. No constituye opinión legal ni asesoría fiscal; antes de participar en un procedimiento, valida bases, fechas y requisitos en la fuente oficial.
