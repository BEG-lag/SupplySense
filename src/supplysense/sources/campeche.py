"""Campeche: convocatorias estatales de la Secretaría de Administración, Finanzas y Planeación
(safin.campeche.gob.mx).

El listado es una página de descargas; cada convocatoria es un PDF con texto (no escaneado) del
que se extraen número, objeto, quién la solicita, la ley estatal aplicable y la tabla de fechas
(registro, junta de aclaraciones y apertura). Las convocatorias nacionales de esa misma página
ya vienen en ComprasMX. No se guarda el nombre del servidor público que firma.
"""

from __future__ import annotations

import html
import io
import logging
import re
from typing import Any

from ..dates import from_spanish
from ..http import PoliteClient
from ..rules import categorize
from ..text import clean

BASE = "https://safin.campeche.gob.mx"
LIST_URL = BASE + "/convocatorias/estatales"
_ITEM = re.compile(
    r'href="(/convocatorias/estatales\?download=(\d+):[^"]+)"[^>]*>\s*([^<]+?)\s*</a>'
)
_NUMERO = re.compile(r"\b([A-Z]{2,}(?:-[A-Z0-9]+){1,4}-\d{4})\b")
_OBJETO = re.compile(
    r"relativ[oa] a(?: la| el| los| las)?\s+(.+?)"
    r"(?:,\s*solicitad[oa]s? por|,\s*conforme a lo siguiente|\.\s)",
    re.S,
)
_SOLICITA = re.compile(r"solicitad[oa]s? por (?:la |el )?(.+?),\s*conforme", re.S)
_LEY = re.compile(r"(Ley de Adquisiciones[^;]*?del Estado de Campeche)", re.S)
_FIRMA = re.compile(r"Campeche,\s*Cam\.?,?\s*a\s+(\d{1,2}\s+de\s+[a-záéíóú]+\s+de\s+\d{4})", re.I)
_FECHA_TABLA = re.compile(r"\d{1,2}\s*/\s*[a-záéíóú]+\s*/\s*\d{4}\s+\d{1,2}:\d{2}", re.I)


def parse_list(page: str) -> list[dict[str, str]]:
    items: dict[str, dict[str, str]] = {}
    for href, did, label in _ITEM.findall(page):
        if label.strip().lower() == "descarga" or did in items:
            continue
        items[did] = {"id": did, "href": html.unescape(href), "titulo": clean(label) or ""}
    return list(items.values())


def pdf_text(content: bytes) -> str:
    from pypdf import PdfReader

    # Las convocatorias usan fuentes CFF; pypdf avisa que no las decodifica completas, pero el
    # texto que necesitamos sale bien.
    logging.getLogger("pypdf").setLevel(logging.ERROR)

    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _one_line(text: str | None) -> str | None:
    return clean(re.sub(r"\s+", " ", text)) if text else None


def parse_text(
    text: str, download_id: str, label: str, href: str = "/convocatorias/estatales"
) -> dict[str, Any] | None:
    m = _NUMERO.search(label) or _NUMERO.search(text)
    if not m:
        return None
    numero = m.group(1)
    objeto = _one_line(m.group(1)) if (m := _OBJETO.search(text)) else None
    solicita = _one_line(m.group(1)) if (m := _SOLICITA.search(text)) else None
    ley = _one_line(m.group(1)) if (m := _LEY.search(text)) else None
    firma = from_spanish(m.group(1)) if (m := _FIRMA.search(text)) else None
    # La tabla de fechas sigue al número: registro y venta de bases, junta y apertura.
    row_start = text.rfind(numero, 0, text.find("Junta de")) if "Junta de" in text else -1
    tail = text[row_start:] if row_start >= 0 else text
    fechas = [from_spanish(f) for f in _FECHA_TABLA.findall(tail)[:3]]
    titulo = objeto[0].upper() + objeto[1:] if objeto else (label or numero)
    return {
        "id": f"camp:{download_id}",
        "fuente": "campeche",
        "fuente_id": int(download_id),
        "numero": numero,
        "titulo": titulo,
        "comprador": "Secretaría de Administración, Finanzas y Planeación de Campeche",
        "unidad": solicita,
        "entidad": "Campeche",
        "orden_gobierno": "GEM",
        "tipo_procedimiento": "Licitación pública estatal",
        "ley": ley,
        "estatus": "abierta",
        "publicado": firma,
        "registro": fechas[0] if len(fechas) > 0 else None,
        "aclaraciones": fechas[1] if len(fechas) > 1 else None,
        "apertura": fechas[2] if len(fechas) > 2 else None,
        "categoria": categorize(titulo),
        "url": BASE + href,
    }


def fetch_list(client: PoliteClient) -> list[dict[str, str]]:
    return parse_list(client.get_ok(LIST_URL, params={"limit": 0}).text)


def fetch_pdf(client: PoliteClient, item: dict[str, str]) -> bytes:
    return client.get_ok(BASE + item["href"]).content
