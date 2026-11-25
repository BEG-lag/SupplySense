"""Ciudad de México: Concurso Digital (Tianguis Digital), Secretaría de Administración y
Finanzas.

El listado público trae las convocatorias vigentes; el detalle está en
``/proveedores/detalle_convocatoria/{base64(id)}`` con ids consecutivos, así que también se
avanza desde el último id conocido para atrapar las nuevas. No se guardan el nombre del
servidor público responsable ni datos bancarios que publica la página.
"""

from __future__ import annotations

import base64
import html
import re
from typing import Any

from ..dates import from_local
from ..http import FetchError, PoliteClient
from ..rules import categorize
from ..text import clean, title_name

BASE = "https://concursodigital.finanzas.cdmx.gob.mx"
LIST_URL = BASE + "/convocatorias_publicas"
_ID = re.compile(r"detalle_convocatoria/([A-Za-z0-9=]+)")


def encode(n: int) -> str:
    return base64.b64encode(str(n).encode()).decode()


def detail_url(n: int) -> str:
    return f"{BASE}/proveedores/detalle_convocatoria/{encode(n)}"


def list_ids(page: str) -> list[int]:
    ids = []
    for token in _ID.findall(page):
        try:
            ids.append(int(base64.b64decode(token).decode()))
        except (ValueError, UnicodeDecodeError):
            continue
    return sorted(set(ids))


def fetch_detail(client: PoliteClient, n: int) -> str | None:
    """Detalle de un id, o None si no existe: el portal responde 500 a ids que aún no hay, así
    que aquí un 500 no se reintenta ni se trata como falla de la fuente."""
    try:
        response = client.request("GET", detail_url(n), retries=0)
    except FetchError:
        return None
    if response.status_code != 200 or "Número de Procedimiento" not in response.text:
        return None
    return response.text


def _lines(page: str) -> list[str]:
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", page)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", text))
    return [line.strip() for line in text.split("\n") if line.strip()]


# Etiquetas de la ficha: si el valor de un campo viene vacío, la línea siguiente es otra
# etiqueta y no debe tomarse como valor.
LABELS = frozenset(
    {
        "Nombre del Procedimiento",
        "Unidad Convocante",
        "Método de Contratación",
        "Fecha de Publicación",
        "Tipo de contratación",
        "Carácter",
        "Número de Procedimiento",
        "ID convocante",
        "Área(s) Requirente(s)",
        "Servidor Público Responsable",
        "Objeto de la Contratación:",
        "Idioma de la Propuesta",
        "Documentos",
    }
)


def _after(lines: list[str], label: str) -> str | None:
    for i, line in enumerate(lines[:-1]):
        if line == label:
            value = lines[i + 1]
            return None if value in LABELS else value
    return None


def _when(value: str | None) -> str | None:
    return from_local((value or "").replace("hrs", "").strip()) if value else None


def parse_detail(page: str, n: int) -> dict[str, Any] | None:
    lines = _lines(page)
    if "Nombre del Procedimiento" not in lines:
        return None
    # Algunas fichas traen el número vacío: se usa el id del portal para no perder la convocatoria.
    numero = clean(_after(lines, "Número de Procedimiento")) or f"CDMX-ID-{n}"
    titulo = clean(_after(lines, "Nombre del Procedimiento")) or numero
    objeto = clean(_after(lines, "Objeto de la Contratación:"))
    metodo = clean(_after(lines, "Método de Contratación"))
    tipo_contratacion = clean(_after(lines, "Tipo de contratación"))
    return {
        "id": f"cdmx:{n}",
        "fuente": "cdmx",
        "fuente_id": n,
        "numero": numero,
        "titulo": titulo,
        "descripcion": objeto if objeto and objeto != titulo else None,
        "comprador": title_name(clean(_after(lines, "Unidad Convocante"))),
        "unidad": title_name(clean(_after(lines, "Área(s) Requirente(s)"))),
        "entidad": "Ciudad de México",
        "orden_gobierno": "GEM",
        "tipo_procedimiento": re.sub(r"^[A-Z]{1,4}\s*-\s*", "", metodo) if metodo else None,
        "tipo_contratacion": tipo_contratacion,
        "caracter": clean(_after(lines, "Carácter")),
        "estatus": "abierta",
        "publicado": from_local(_after(lines, "Fecha de Publicación")),
        "aclaraciones": _when(_after(lines, "Fecha y hora de la junta de aclaraciones")),
        "apertura": _when(
            _after(lines, "Fecha y hora de la presentación y apertura de propuestas")
        ),
        "fallo": _when(_after(lines, "Fecha y hora de la emision del fallo")),
        "categoria": categorize(f"{titulo} {objeto or ''}", tipo_contratacion),
        "url": detail_url(n),
    }
