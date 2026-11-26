"""Estado de México: COMPRAMEX (compramex.edomex.gob.mx), procedimientos adquisitivos del año.

Es JSF/PrimeFaces: cada consulta pide el ``ViewState`` de la página, un POST que filtra por tipo
de organismo y estatus, y un POST AJAX que pagina la tabla (acepta ``rows`` igual al total, así
que sale todo en una respuesta). Tipos: 6 sector central (exige estatus 1 a 4), 3 organismos
auxiliares, 1 municipios y 5 órganos autónomos (estatus 0, todos).

Un firewall corta la conexión por volumen acumulado (unas 130 peticiones en 20 minutos bastaron
para un bloqueo de más de 20 minutos), así que cada corrida hace unas 24 peticiones con pausas.

Calidad: el sector central trae número, partida genérica, fecha, estatus y etapa confiables. En
los demás tipos la fila es texto libre (número y, a veces, el objeto), hay documentos subidos
como si fueran procedimientos y el estatus VIGENTE no se actualiza: se toman solo licitaciones e
invitaciones con objeto, y su estatus se estima por fecha. La dependencia no aparece: se deduce
del prefijo cuando es inequívoco.
"""

from __future__ import annotations

import html
import re
import time
from typing import Any

from ..dates import from_dmy
from ..http import PoliteClient
from ..text import clean

URL = "https://compramex.edomex.gob.mx/compramex/public/catalogosExternos/procedimientsoAdquisitivos.xhtml"
AJAX = {"Faces-Request": "partial/ajax", "X-Requested-With": "XMLHttpRequest"}
PAUSE = 2.0
CENTRAL_STATUS = ("1", "2", "3", "4")
TYPES = {"3": "Organismo auxiliar", "1": "Municipio", "5": "Órgano autónomo"}
CENTRAL_BUYER = "Gobierno del Estado de México (sector central)"
CENTRAL_UNIT = "Dirección General de Recursos Materiales"
STATUS = {"VIGENTE": "abierta", "SEGUIMIENTO": "en_evaluacion", "CONCLUIDO": "concluida"}
# Prefijos inequívocos de organismos auxiliares (catálogo de unidades de COMPRAMEX).
PREFIXES = {
    "ISSEMYM": "Instituto de Seguridad Social del Estado de México y Municipios",
    "ISEM": "Instituto de Salud del Estado de México",
    "JCEM": "Junta de Caminos del Estado de México",
    "CAEM": "Comisión del Agua del Estado de México",
    "DIFEM": "Sistema para el Desarrollo Integral de la Familia del Estado de México",
    "SEIEM": "Servicios Educativos Integrados al Estado de México",
    "COBAEM": "Colegio de Bachilleres del Estado de México",
    "COMECYT": "Consejo Mexiquense de Ciencia y Tecnología",
    "HRAEZ": "Hospital Regional de Alta Especialidad de Zumpango",
    "IGECEM": "Instituto de Información e Investigación Geográfica, Estadística y Catastral "
    "del Estado de México",
    "IFREM": "Instituto de la Función Registral del Estado de México",
    "CEPANAF": "Comisión Estatal de Parques Naturales y de la Fauna",
    "CCLEM": "Centro de Conciliación Laboral del Estado de México",
    "UPVT": "Universidad Politécnica del Valle de Toluca",
}
_ROW = re.compile(r'<tr data-ri="\d+"[^>]*>(.*?)</tr>', re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_VIEWSTATE = re.compile(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"')
_VIEWSTATE_AJAX = re.compile(r'ViewState:0"><!\[CDATA\[([^\]]+)')
_TABLE = re.compile(r'DataTable","\w+",\{id:"([^"]+)"')
_ROWCOUNT = re.compile(r"rowCount:(\d+)")
# Filas que son documentos o adjudicaciones directas, no convocatorias.
_NOT_TENDER = re.compile(
    r"^(ACTA|FALLO|CONTRATO|BASES|JUNTA|CONTRAOFERTA|DICTAMEN|ANEXO|OFICIO|AVISO|NOTIFICACI|"
    r"AD[-/ ]|ADP|ADE|AA-|AO-)",
    re.I,
)
_TENDER = re.compile(r"\b(LPN|LPNP|LPE|LPI|LP|IR|IRP|IRNP|ITP|I3P)\b|LICITACI|INVITACI", re.I)
# "UNIFORMES - JUNTA ACLARACIONES": el documento subido, no parte del objeto.
_DOC_SUFFIX = re.compile(
    r"\s+-\s+(CONTRATO|JUNTA[\w ]*|FALLO|ACTA[\w ]*|BASES|CONVOCATORIA|CONTRAOFERTA)\s*$", re.I
)
_NUMBER = re.compile(r"^((?:NO\.?\s*)?[A-Z0-9][A-Z0-9/.\-]*\d[A-Z0-9/.\-]*)\s*(.*)$", re.I)


def _cells(row: str) -> list[str]:
    cells = []
    for td in _TD.findall(row):
        td = re.sub(r"<script.*?</script>", "", td, flags=re.S)
        cells.append(clean(html.unescape(re.sub(r"<[^>]+>", " ", td))) or "")
    return cells


def rows(page: str) -> list[list[str]]:
    return [_cells(r) for r in _ROW.findall(page)]


def _status(raw: str) -> str:
    raw = raw.upper()
    if "CANCEL" in raw:
        return "cancelada"
    if "DESIERT" in raw:
        return "desierta"
    return STATUS.get(raw, "en_evaluacion")


def parse_central(cells_list: list[list[str]]) -> list[dict[str, Any]]:
    """Filas del sector central: convocatoria, procedimiento, partida, fecha, estatus y etapa."""
    records = []
    for cells in cells_list:
        if len(cells) < 6 or not cells[1]:
            continue
        convocatoria, numero, partida, fecha, estatus, etapa = cells[:6]
        records.append(
            {
                "id": f"mex:{numero.upper()}",
                "fuente": "edomex",
                "fuente_id": numero,
                "numero": numero,
                "convocatoria": convocatoria,
                "titulo": partida.rstrip("."),
                "comprador": CENTRAL_BUYER,
                "unidad": CENTRAL_UNIT,
                "entidad": "Estado de México",
                "orden_gobierno": "GEM",
                "tipo_procedimiento": _type(numero),
                "estatus_fuente": f"{estatus} · {etapa}".strip(" ·"),
                "estatus": _status(estatus),
                "estatus_oficial": True,
                "publicado": from_dmy(fecha),
                "url": URL,
            }
        )
    return records


def _type(numero: str) -> str | None:
    n = numero.upper()
    if re.search(r"\bLP|LPN|LPE|LPI", n):
        return "Licitación pública"
    if re.search(r"\bIR|ITP|I3P|INVIT", n):
        return "Invitación restringida"
    return None


def _is_number(numero: str) -> bool:
    """Una clave, no una palabra cortada ("LPNP/020-IMPERMEABILIZACI" no lo es)."""
    return not re.search(r"[A-Z]{9,}", numero.upper())


def _is_object(objeto: str) -> bool:
    """Texto con al menos tres palabras y no una lista de más números de procedimiento."""
    words = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{3,}", objeto)
    codes = re.findall(r"[A-Z0-9]+[/\-][A-Z0-9/\-]+", objeto.upper())
    return len(words) >= 3 and len(codes) <= len(words) // 3


def buyer(numero: str, tipo: str) -> str:
    for prefix, name in PREFIXES.items():
        if re.search(rf"(^|[/\-\s]){prefix}([/\-\s]|$)", numero.upper()):
            return name
    return f"{TYPES[tipo]} del Estado de México"


def parse_other(cells_list: list[list[str]], tipo: str) -> list[dict[str, Any]]:
    """Filas de organismos, municipios y autónomos: texto libre con número y, a veces, objeto.
    Se quedan las licitaciones e invitaciones con objeto; un número repetido se toma una vez."""
    records: dict[str, dict[str, Any]] = {}
    for cells in cells_list:
        if len(cells) < 3:
            continue
        text, fecha, estatus = cells[0], cells[1], cells[2]
        if not text or _NOT_TENDER.search(text) or not _TENDER.search(text):
            continue
        m = _NUMBER.match(text)
        if not m:
            continue
        numero = re.sub(r"^NO\.?\s*", "", m.group(1), flags=re.I).strip(".-/")
        objeto = clean(_DOC_SUFFIX.sub("", m.group(2)).strip(' .,:;-"“”')) or ""
        if not _is_number(numero) or not _is_object(objeto):
            continue
        key = f"mex:{numero.upper()}"
        published = from_dmy(fecha)
        prev = records.get(key)
        if prev and (prev.get("publicado") or "") >= (published or ""):
            continue
        records[key] = {
            "id": key,
            "fuente": "edomex",
            "fuente_id": numero,
            "numero": numero,
            "titulo": objeto,
            "comprador": buyer(numero, tipo),
            "entidad": "Estado de México",
            "orden_gobierno": "GEM" if tipo != "1" else "Municipal",
            "tipo_procedimiento": _type(numero),
            "estatus_fuente": estatus,
            "estatus": _status(estatus),
            "publicado": published,
            "url": URL,
        }
    return list(records.values())


def fetch_rows(client: PoliteClient, tipo: str, estatus: str, year: int) -> list[list[str]]:
    """GET (ViewState), cambio de tipo si no es sector central, filtro y una sola página AJAX."""
    view = _VIEWSTATE.search(client.get_ok(URL).text)
    if not view:
        return []
    state = view.group(1)
    form = {
        "formulario": "formulario",
        "formulario:slTipoOrganismo_input": tipo,
        "formulario:slTipoOrganismoAuxiliar_input": "1" if tipo == "6" else "0",
        "formulario:slTipo_input": estatus,
        "formulario:slAnio_input": str(year),
    }
    if tipo != "6":
        time.sleep(PAUSE)
        change = client.post_ok(
            URL,
            headers=AJAX,
            data={
                **form,
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": "formulario:slTipoOrganismo",
                "javax.faces.partial.execute": "formulario:slTipoOrganismo",
                "javax.faces.partial.render": "formulario:slTipoOrganismoAuxiliar",
                "javax.faces.behavior.event": "change",
                "javax.faces.partial.event": "change",
                "javax.faces.ViewState": state,
            },
        ).text
        m = _VIEWSTATE_AJAX.search(change)
        if not m:
            return []
        state = m.group(1)
    time.sleep(PAUSE)
    page = client.post_ok(
        URL, data={**form, "formulario:btnFiltrar": "", "javax.faces.ViewState": state}
    ).text
    count, table = _ROWCOUNT.search(page), _TABLE.search(page)
    states = _VIEWSTATE.findall(page)
    if not count or not table or not states or int(count.group(1)) == 0:
        return rows(page)
    tid = table.group(1)
    frm = tid.rsplit(":", 1)[0]
    time.sleep(PAUSE)
    data = client.post_ok(
        URL,
        headers=AJAX,
        data={
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": tid,
            "javax.faces.partial.execute": tid,
            "javax.faces.partial.render": tid,
            tid: tid,
            f"{tid}_pagination": "true",
            f"{tid}_first": "0",
            f"{tid}_rows": count.group(1),
            f"{tid}_encodeFeature": "true",
            frm: frm,
            "javax.faces.ViewState": states[-1],
        },
    ).text
    return rows(data)


def fetch_all(client: PoliteClient, year: int) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for estatus in CENTRAL_STATUS:
        for rec in parse_central(fetch_rows(client, "6", estatus, year)):
            records[rec["id"]] = rec
        time.sleep(PAUSE)
    for tipo in TYPES:
        for rec in parse_other(fetch_rows(client, tipo, "0", year), tipo):
            records.setdefault(rec["id"], rec)
        time.sleep(PAUSE)
    return list(records.values())
