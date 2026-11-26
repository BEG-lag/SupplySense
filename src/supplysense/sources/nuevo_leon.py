"""Nuevo León: subastas electrónicas inversas del gobierno estatal (subasta.nl.gob.mx).

``monitoreosubastas.asp`` es una sola página pública con todas las subastas desde 2016: número,
descripción (con "SOLICITADO POR <dependencia>"), fecha de la subasta y las actas en PDF. El
detalle (``monitoreopartidassubasta.asp?ids=N``) trae el estatus, el precio base de cada partida,
el ganador con su mejor oferta y los proveedores participantes. Las páginas vienen en cp1252 sin
declararlo y con comentarios HTML que hay que quitar antes de leer.

Las convocatorias de ``nl.gob.mx`` rechazan a los lectores automáticos que se identifican como
tales (HTTP 403); se respeta y no se leen.
"""

from __future__ import annotations

import html
import re
from typing import Any

from ..http import PoliteClient
from ..rules import categorize
from ..text import clean, title_name

BASE = "https://subasta.nl.gob.mx"
LIST_URL = BASE + "/monitoreosubastas.asp"
DETAIL_URL = BASE + "/monitoreopartidassubasta.asp?ids={n}"
DOC_URL = BASE + "/docs/{kind}_{n}.pdf"
# Actas que publica cada subasta (número del archivo en /docs).
DOCS = {
    1: "Bases",
    2: "Ficha técnica",
    4: "Acta de aclaraciones",
    7: "Acta de apertura técnica",
    8: "Acta de fallo técnico",
    3: "Acta de apertura de subasta",
    6: "Acta de comité",
    5: "Acta de adjudicación",
}
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_IDS = re.compile(r"monitoreopartidassubasta\.asp\?ids=(\d+)")
_DOC = re.compile(r"docs/(\d)_(\d+)\.pdf")
_SOLICITA = re.compile(r",?\s*SOLICITAD[OA]S? POR (?:LA |EL |LOS |LAS )?(.+?)\.?\s*$", re.I | re.S)
_NUMERO = re.compile(
    r"^\s*(?:NO\.?\s*)?([A-Z0-9][A-Z0-9-]*-\d+/\d{4})\s*"
    r"(?:,|RELATIV[OA]S?\s+A(?:L|\s+LA|\s+LOS|\s+LAS)?\b)?\s*",
    re.I,
)
_FECHA = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})(?::\d{2})?\s*([ap])\.?\s*m\.?", re.I
)
_MONEY = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)")


def decode(raw: bytes) -> str:
    return re.sub(r"<!--.*?-->", "", raw.decode("cp1252", errors="replace"), flags=re.S)


def _text(fragment: str) -> str | None:
    return clean(html.unescape(re.sub(r"<[^>]+>", " ", fragment)))


def parse_datetime(value: str | None) -> str | None:
    """``30/11/2026 08:00:00 A.M.`` → ``2026-11-30T08:00:00`` (reloj de 12 horas)."""
    m = _FECHA.search(value or "")
    if not m:
        return None
    day, month, year, hour, minute, half = m.groups()
    h = int(hour) % 12 + (12 if half.lower() == "p" else 0)
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}T{h:02d}:{int(minute):02d}:00"


def split_description(text: str) -> tuple[str | None, str, str | None]:
    """ "DGCNL-DC-SEIN-029/2026, SERVICIO …, SOLICITADO POR LA SECRETARÍA DE ECONOMÍA." →
    (número, objeto, dependencia que lo pide)."""
    numero = None
    m = _NUMERO.match(text)
    if m:
        numero, text = m.group(1), text[m.end() :]
    solicitante = None
    m = _SOLICITA.search(text)
    if m:
        solicitante = title_name(clean(m.group(1)))
        text = text[: m.start()]
    return numero, clean(text.strip(" ,.")) or "", solicitante


def parse_list(page: str) -> list[dict[str, Any]]:
    records = []
    for row in _ROW.findall(page):
        m = _IDS.search(row)
        cells = _CELL.findall(row)
        if not m or len(cells) < 4:
            continue
        n = int(m.group(1))
        description = _text(cells[2]) or _text(cells[1]) or ""
        numero, objeto, solicitante = split_description(description)
        docs = sorted({int(k) for k, ids in _DOC.findall(row) if int(ids) == n})
        records.append(
            {
                "id": f"nl:{n}",
                "fuente": "nuevo_leon",
                "fuente_id": n,
                "numero": numero or f"SUBASTA-{n}",
                "titulo": objeto or description,
                "comprador": solicitante,
                "entidad": "Nuevo León",
                "orden_gobierno": "GEM",
                "tipo_procedimiento": "Subasta electrónica inversa",
                "apertura": parse_datetime(_text(cells[3])),
                "documentos": docs,
                "categoria": categorize(objeto or description),
                "url": DETAIL_URL.format(n=n),
            }
        )
    return records


def _section(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    return text[i + len(start) : j if j > 0 else None]


def _money(value: str) -> float | None:
    m = _MONEY.search(value)
    return float(m.group(1).replace(",", "")) if m else None


def parse_detail(page: str) -> dict[str, Any]:
    """Estatus, ganadores con su mejor oferta y participantes de una subasta."""
    body = page.split("<main", 1)[-1]
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    cells = [c for c in (_text(x) for x in re.split(r"<[^>]+>", body)) if c]
    text = "\n".join(cells)
    out: dict[str, Any] = {}
    if (i := _index(cells, "Estatus de la subasta:")) is not None:
        out["estatus_fuente"] = cells[i + 1]
    if (i := _index(cells, "Fechas de subasta:")) is not None:
        start = parse_datetime(cells[i + 1])
        if start:
            out["apertura"] = start
    if (i := _index(cells, "Subasta terminada:")) is not None and (
        end := parse_datetime(cells[i + 1])
    ):
        out["fallo"] = end
    # Resultados: N | Partida | Proveedor | Precio base | Mejor oferta (una fila por partida).
    winners: list[str] = []
    total = base = 0.0
    for _, _, proveedor, precio_base, oferta in _rows(
        _section(text, "Resultados", "Proveedores participantes"), "Mejor oferta", 5
    ):
        amount = _money(oferta)
        if amount is None:
            break
        name = title_name(proveedor) or proveedor
        if name not in winners:
            winners.append(name)
        total += amount
        base += _money(precio_base) or 0
    if winners:
        out.update(ganadores=winners, monto=round(total, 2), moneda="MXN")
        if base:
            out["precio_base"] = round(base, 2)
    # Participantes: N | Proveedor | Alias ("Proveedor 800": así aparecen en el historial).
    names = []
    for _, proveedor, alias in _rows(
        _section(text, "Proveedores participantes", "Historial de operaciones"), "Alias", 3
    ):
        if not alias.lower().startswith("proveedor"):
            break
        names.append(title_name(proveedor) or proveedor)
    if names:
        out["participantes"] = names
    return out


def _rows(section: str, last_header: str, width: int) -> list[list[str]]:
    """Celdas de una tabla aplanada, agrupadas de ``width`` en ``width`` tras el encabezado."""
    cells = section.split("\n")
    if last_header not in cells:
        return []
    body = cells[cells.index(last_header) + 1 :]
    return [body[i : i + width] for i in range(0, len(body) - width + 1, width)]


def _index(cells: list[str], label: str) -> int | None:
    try:
        i = cells.index(label)
    except ValueError:
        return None
    return i if i + 1 < len(cells) else None


def status(rec: dict[str, Any]) -> str:
    """Estatus a partir del de la fuente ("Registro" mientras se inscriben, "Cerrada" al
    terminar) y de lo publicado: con ganador o acta de adjudicación ya está adjudicada."""
    raw = (rec.get("estatus_fuente") or "").lower()
    if "cancel" in raw:
        return "cancelada"
    if "desiert" in raw:
        return "desierta"
    if rec.get("ganadores") or 5 in (rec.get("documentos") or []):
        return "adjudicada"
    if raw.startswith("cerr"):
        return "en_evaluacion"
    return "abierta"


def fetch_list(client: PoliteClient) -> list[dict[str, Any]]:
    return parse_list(decode(client.get_ok(LIST_URL).content))


def fetch_detail(client: PoliteClient, n: int) -> dict[str, Any]:
    return parse_detail(decode(client.get_ok(DETAIL_URL.format(n=n)).content))
