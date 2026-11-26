"""Órgano de Administración Judicial (antes Consejo de la Judicatura Federal), www.oaj.gob.mx.

Las páginas de licitaciones cargan con jQuery fragmentos de tabla por año:
``include/convocatorias/dgrm{AAAA}.html`` (Recursos Materiales y Servicios Generales) e
``include/convocatorias/dgim{AAAA}.html`` (Inmuebles y Mantenimiento). Cada fila trae número,
documentos (convocatoria, bases, aclaraciones, fallo), fecha de publicación y objeto. No hay
estatus: con acta de fallo publicada se da por concluida; si no, el estatus sale de la fecha.
Compra también para la SCJN y el TEPJF. Los ZIP de bases llegan a cientos de MB: no se bajan.
"""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import quote

from ..dates import from_dmy
from ..http import FetchError, PoliteClient
from ..rules import categorize
from ..text import clean

BASE = "https://www.oaj.gob.mx/"
AREAS = {
    "dgrm": (
        "ServiciosGenerales",
        "convocatoriasDGRMSG.htm",
        "Dirección General de Recursos Materiales",
    ),
    "dgim": (
        "InmueblesMantenimiento",
        "licitacionesDGIM.htm",
        "Dirección General de Inmuebles y Mantenimiento",
    ),
}
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td\b([^>]*)>(.*?)</td>", re.S)
_FIELD = re.compile(r'data-field="([^"]+)"')
_HREF = re.compile(r'href="([^"]+)"')
_NUMBER = re.compile(r"^(OAJ|CJF|SCJN|TEPJF)[/\-]", re.I)
_DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
_TYPES = {
    "LPN": "Licitación pública nacional",
    "LPI": "Licitación pública internacional",
    "LP": "Licitación pública",
    "ITP": "Invitación a cuando menos tres personas",
}


def _text(fragment: str) -> str | None:
    return clean(html.unescape(re.sub(r"<[^>]+>", " ", fragment)))


def parse_list(page: str, area: str, year: int) -> list[dict[str, Any]]:
    folder, portal, unidad = AREAS[area]
    records = []
    for row in _ROW.findall(page):
        cells = _CELL.findall(row)
        if len(cells) < 4:
            continue
        texts = [_text(c) or "" for _, c in cells]
        numero = texts[0]
        if not _NUMBER.match(numero):
            continue
        cancelled = "cancelad" in row.lower()
        numero = clean(re.sub(r"\(\s*cancelad[ao]\s*\)", "", numero, flags=re.I)) or numero
        fields = {m.group(1): c for attrs, c in cells if (m := _FIELD.search(attrs))}
        published = next((t for t in texts if _DATE.match(t)), None)
        objeto = texts[-1] or numero
        fallo = fields.get("fallo", "")
        has_fallo = bool(_HREF.search(fallo)) or any(
            "fallo" in h.lower() for h in _HREF.findall(row)
        )
        docs = [h for h in _HREF.findall(row) if h.lower().endswith(".pdf")]
        conv = next((h for h in docs if "convocatoria" in h.lower()), None) or next(
            (h for h in docs if "bases" in h.lower()), None
        )
        kind = re.search(r"/(LPN|LPI|LP|ITP)/", numero.upper())
        records.append(
            {
                "id": f"oaj:{area}:{numero.upper().replace(' ', '')}",
                "fuente": "oaj",
                "fuente_id": numero,
                "numero": numero,
                "titulo": objeto,
                "comprador": "Órgano de Administración Judicial",
                "unidad": unidad,
                "entidad": "Ciudad de México",
                "orden_gobierno": "Poder Judicial",
                "tipo_procedimiento": _TYPES.get(kind.group(1)) if kind else None,
                "estatus": "cancelada" if cancelled else "concluida" if has_fallo else "abierta",
                "publicado": from_dmy(published),
                "categoria": categorize(objeto),
                "url": f"{BASE}resources/convocatorias/{folder}/{year}/{quote(conv)}"
                if conv
                else f"{BASE}{portal}",
            }
        )
    return records


def fetch_list(client: PoliteClient, years: tuple[int, ...]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for area in AREAS:
        for year in years:
            try:
                page = client.get_ok(f"{BASE}include/convocatorias/{area}{year}.html").text
            except FetchError:
                continue  # el año todavía no tiene archivo
            records += parse_list(page, area, year)
    return records
