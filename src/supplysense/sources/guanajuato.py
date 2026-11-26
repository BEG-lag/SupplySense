"""Guanajuato: licitaciones del gobierno estatal en el portal de la Unidad de Transparencia
(transparencia.guanajuato.gob.mx).

``data/licitacion.php`` devuelve JSON con todo desde 2021, lo más nuevo primero (sin mandar
``sort``: con él se invierte el orden). Cada fila trae número, objeto, dependencia, tipo, fecha de
publicación y los nombres de los archivos publicados (convocatoria, junta, apertura y fallo),
pero no estatus, monto ni ganador. El estatus sale de qué actas ya se publicaron y de las fechas
de la convocatoria, cuando su PDF tiene texto. Las de la Secretaría de Finanzas vienen dentro de
un ZIP de decenas de MB: el servidor acepta ``Range`` y se baja solo el PDF de la convocatoria.

Las convocatorias traen nombres y correos de servidores públicos: no se guardan.
"""

from __future__ import annotations

import io
import logging
import re
import struct
import zlib
from typing import Any
from urllib.parse import quote

from pypdf import PdfReader

from ..dates import from_dmy, from_spanish
from ..http import FetchError, PoliteClient
from ..rules import categorize
from ..text import clean

BASE = "https://transparencia.guanajuato.gob.mx"
LIST_URL = BASE + "/transparencia/data/licitacion.php"
DOCS_URL = BASE + "/biblioteca_digital/docart10/"
PORTAL_URL = BASE + "/transparencia/informacion_publica_licitaciones.php"
PAGE = 500
LAWS = {
    "Ley de Contrataciones Públicas para el Estado de Guanajuato",
    "Ley de Obra Pública y Servicios Relacionados con la Misma para el Estado y los Municipios "
    "de Guanajuato",
}
# Lo que también sale en ComprasMX (recursos federales) se descarta para no contarlo dos veces.
_FEDERAL_NUMBER = re.compile(r"^\s*(LA|LO|IA|IO|AA|AO|M3F)-", re.I)
_TYPES = {"Por Invtación I3": "Invitación a cuando menos tres"}


def _doc(name: str | None) -> str | None:
    return DOCS_URL + quote(name) if name else None


def parse_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for row in rows:
        numero = clean(row.get("licitacion_numero"))
        tipo = clean(row.get("licitacion_tipo"))
        if not row.get("dar_id") or not numero:
            continue
        if tipo == "Licitación Pública Federal" or _FEDERAL_NUMBER.match(numero):
            continue
        titulo = clean(row.get("finalidad")) or clean(row.get("licitacion_nombre")) or numero
        files = {k: clean(row.get(k)) for k in ("convocatoria", "junta", "apertura", "fallo")}
        if tipo == "Adjudicación Directa" or files["fallo"]:
            estatus = "concluida"
        elif files["apertura"]:
            estatus = "en_evaluacion"
        else:
            estatus = "abierta"
        materia = clean(row.get("materia"))
        records.append(
            {
                "id": f"gto:{row['dar_id']}",
                "fuente": "guanajuato",
                "fuente_id": int(row["dar_id"]),
                "numero": numero,
                "titulo": titulo,
                "comprador": clean(row.get("dependencia_nombre")),
                "entidad": "Guanajuato",
                "orden_gobierno": "GEM",
                "tipo_procedimiento": _TYPES.get(tipo or "", tipo),
                "tipo_contratacion": materia,
                "estatus": estatus,
                "publicado": (row.get("licitacion_fecha") or "")[:10] or None,
                "categoria": categorize(titulo),
                "convocatoria_archivo": files["convocatoria"],
                "actas": [k for k in ("junta", "apertura", "fallo") if files[k]],
                "url": _doc(files["convocatoria"])
                if (files["convocatoria"] or "").lower().endswith(".pdf")
                else PORTAL_URL,
            }
        )
    return records


def fetch_list(client: PoliteClient, pages: int = 1) -> list[dict[str, Any]]:
    """Las ``pages`` páginas más recientes (500 por página; todo el histórico son unas 6)."""
    records: list[dict[str, Any]] = []
    for page in range(pages):
        params = {
            "limit": PAGE,
            "offset": page * PAGE,
            "palabraclave": "",
            "dependencia": "",
            "materia": "",
            "tipolicitacion": "",
            "anio": "",
        }
        data = client.get_ok(LIST_URL, params=params).json()
        rows = data.get("rows") or []
        records += parse_rows(rows)
        if len(rows) < PAGE:
            break
    return records


# ── fechas de la convocatoria ────────────────────────────────────────────────

_DATE_WORDS = r"(\d{1,2} de [a-záéíóú]+ de \d{4})(?:\s*,?\s*a las (\d{1,2}:\d{2}))?"
_PATTERNS = {
    "aclaraciones": re.compile(
        r"junta de aclaraciones se (?:llevar[áa] a cabo|realizar[áa]|efectuar[áa]) el d[íi]a "
        + _DATE_WORDS,
        re.I,
    ),
    "apertura": re.compile(
        r"apertura de (?:las )?(?:ofertas|proposiciones|propuestas)[^.]{0,80}?se "
        r"(?:efectuar[áa]|llevar[áa] a cabo|realizar[áa]) el d[íi]a " + _DATE_WORDS,
        re.I,
    ),
}
_FALLO = re.compile(
    r"Apertura t[ée]cnica y econ[óo]mica\s+\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s*hrs\.?\s+"
    r"(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})",
    re.I,
)
_REGISTRO = re.compile(r"\$\s?[\d,]+\.\d{2}\s+(\d{1,2}/\d{1,2}/\d{4})")
_RECURSOS = re.compile(r"procedencia de los recursos es:?\s*([A-Za-zÁÉÍÓÚáéíóú]+)", re.I)


def parse_text(text: str) -> dict[str, Any]:
    """Fechas, ley y origen de los recursos del texto de una convocatoria."""
    text = re.sub(r"\s+", " ", text)
    out: dict[str, Any] = {}
    for key, pattern in _PATTERNS.items():
        m = pattern.search(text)
        if m and (day := from_spanish(m.group(1))):
            out[key] = (
                f"{day}T{int(m.group(2)[:-3]):02d}{m.group(2)[-3:]}:00" if m.group(2) else day
            )
    if (m := _FALLO.search(text)) and (fallo := from_dmy(m.group(1))):
        out["fallo"] = fallo
    if (m := _REGISTRO.search(text)) and (registro := from_dmy(m.group(1))):
        out["registro"] = registro
    if m := _RECURSOS.search(text):
        out["recursos"] = m.group(1).capitalize()
    for law in LAWS:
        if law.lower() in text.lower():
            out["ley"] = law
            break
    return out


def pdf_text(data: bytes) -> str:
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    reader = PdfReader(io.BytesIO(data))
    return " ".join((page.extract_text() or "") for page in reader.pages[:8])


def _range(client: PoliteClient, url: str, start: int, end: int) -> bytes:
    response = client.request("GET", url, headers={"Range": f"bytes={start}-{end}"})
    if response.status_code not in (200, 206):
        raise FetchError(f"HTTP {response.status_code} en {url}")
    return response.content


def zip_member(client: PoliteClient, url: str, pattern: str) -> bytes | None:
    """Un solo archivo de un ZIP remoto, leyendo con ``Range`` el directorio central y el
    archivo, sin bajar el ZIP completo."""
    head = client.request("HEAD", url)
    size = int(head.headers.get("content-length") or 0)
    if head.status_code != 200 or size < 22:
        return None
    tail = _range(client, url, max(0, size - 65536), size - 1)
    end = tail.rfind(b"PK\x05\x06")
    if end < 0:
        return None
    cd_size, cd_offset = struct.unpack("<II", tail[end + 12 : end + 20])
    tail_start = size - len(tail)
    if cd_offset >= tail_start:
        directory = tail[cd_offset - tail_start : cd_offset - tail_start + cd_size]
    else:
        directory = _range(client, url, cd_offset, cd_offset + cd_size - 1)
    pos = 0
    regex = re.compile(pattern, re.I)
    while directory[pos : pos + 4] == b"PK\x01\x02":
        flags, method = struct.unpack("<HH", directory[pos + 8 : pos + 12])
        csize = struct.unpack("<I", directory[pos + 20 : pos + 24])[0]
        name_len, extra_len, comment_len = struct.unpack("<HHH", directory[pos + 28 : pos + 34])
        offset = struct.unpack("<I", directory[pos + 42 : pos + 46])[0]
        raw_name = directory[pos + 46 : pos + 46 + name_len]
        name = raw_name.decode("utf-8" if flags & 0x800 else "cp437", errors="replace")
        if regex.search(name) and method in (0, 8):
            local = _range(client, url, offset, offset + 29)
            start = offset + 30 + sum(struct.unpack("<HH", local[26:30]))
            blob = _range(client, url, start, start + csize - 1)
            return zlib.decompress(blob, -15) if method == 8 else blob
        pos += 46 + name_len + extra_len + comment_len
    return None


def fetch_convocatoria(client: PoliteClient, rec: dict[str, Any]) -> bytes | None:
    """PDF de la convocatoria: el archivo publicado si es PDF, o el ``*-C.pdf`` del ZIP de la
    Secretaría de Finanzas. Otros formatos (RAR, DOCX) se dejan."""
    name = rec.get("convocatoria_archivo") or ""
    url = _doc(name)
    if not url:
        return None
    if name.lower().endswith(".pdf"):
        return client.get_ok(url).content
    if name.lower().endswith(".zip"):
        return zip_member(client, url, r"-C\.pdf$") or zip_member(
            client, url, r"convocatoria[^/]*\.pdf$"
        )
    return None
