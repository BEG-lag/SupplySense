"""ComprasMX: archivos de datos abiertos (expedientes y contratos) del año.

Los archivos responden a GET sin navegador en una URL estable por año. Vienen en latin-1 con
secuencias UTF-8 sueltas (``text.decode_mixed``). Las columnas se leen por nombre, nunca por
posición. Se leen todos los giros; ``motivo_alcance`` marca los que forman la vertical de
energía y O&G. Estos archivos son fotos completas de cada año: no se guardan en git, se bajan
cada día y solo se registra cuándo vimos cada registro por primera vez. No se leen el nombre
ni el correo del operador del anuncio: son datos de servidores públicos que el sitio no usa.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..dates import from_local
from ..rules import categorize, normalize_status, scope_reason
from ..text import clean, decode_mixed, fold, public_rfc, rfc_kind

BASE = "https://upcp-cnetservicios.buengobierno.gob.mx/norah/documentos/recursos/lck/expedientes/obtener/"
FILES = {
    "expedientes": "Expedientes_ComprasMX_{year}.csv",
    "contratos": "Contratos_ComprasMX_{year}.csv",
}
REQUIRED = {
    "expedientes": ("codigo del expediente", "institucion", "estatus procedimiento"),
    "contratos": ("codigo del contrato", "codigo del expediente", "proveedor o contratista"),
}
_CODE_LIKE = re.compile(r"^[\w\-/. ]{0,20}\d[\w\-/. ]*$")


def url(kind: str, year: int) -> str:
    return BASE + FILES[kind].format(year=year)


def _key(header: str) -> str:
    return re.sub(r"\s+", " ", fold(header)).strip()


def read_rows(path: Path, kind: str) -> Iterator[dict[str, str]]:
    """Filas como dict con encabezados normalizados (sin acentos, minúsculas). Si un
    encabezado se repite, gana la primera columna."""
    text = decode_mixed(path.read_bytes())
    reader = csv.reader(io.StringIO(text, newline=""))
    header = [_key(h) for h in next(reader)]
    missing = [col for col in REQUIRED[kind] if col not in header]
    if missing:
        raise ValueError(f"{path.name}: faltan columnas {missing}")
    index: dict[str, int] = {}
    for i, name in enumerate(header):
        index.setdefault(name, i)
    for row in reader:
        if len(row) < len(header) // 2:
            continue
        yield {name: (row[i] if i < len(row) else "") for name, i in index.items()}


def _amount(value: str | None) -> float | None:
    if not value:
        return None
    try:
        number = float(value.replace(",", "").replace("$", "").strip())
    except ValueError:
        return None
    return round(number, 2) if number > 0 else None


def _title(row: dict[str, str], *fields: str) -> str | None:
    """Primer título que no sea solo un código ("1202600551")."""
    candidates = [clean(row.get(f)) for f in fields]
    for value in candidates:
        if value and not _CODE_LIKE.match(value):
            return value
    return next((v for v in candidates if v), None)


def parse_expediente(row: dict[str, str]) -> dict[str, Any] | None:
    codigo = clean(row.get("codigo del expediente"))
    if not codigo:
        return None
    titulo = _title(row, "titulo del expediente", "nombre anuncio", "descripcion anuncio")
    descripcion = clean(row.get("descripcion anuncio"))
    institucion = clean(row.get("institucion"))
    siglas = clean(row.get("siglas de la institucion"))
    motivo = scope_reason(institucion, siglas, f"{titulo or ''} {descripcion or ''}")
    estatus_fuente = clean(row.get("estatus procedimiento"))
    tipo_contratacion = clean(row.get("tipo de contratacion"))
    return {
        "id": f"cmx:{codigo}",
        "fuente": "comprasmx",
        "fuente_id": codigo,
        "numero": clean(row.get("numero de procedimiento/proyecto")) or codigo,
        "titulo": titulo or codigo,
        "descripcion": descripcion if descripcion and descripcion != titulo else None,
        "comprador": institucion,
        "siglas": siglas,
        "unidad": clean(row.get("nombre de la uc")),
        "entidad": clean(row.get("entidad federativa")),
        "orden_gobierno": clean(row.get("orden de gobierno")),
        "tipo_procedimiento": clean(row.get("tipo procedimiento")),
        "ley": clean(row.get("ley")),
        "tipo_contratacion": tipo_contratacion,
        "caracter": clean(row.get("caracter del anuncio")),
        "forma": clean(row.get("forma de participacion")),
        "estatus_fuente": estatus_fuente,
        "estatus": normalize_status("comprasmx", estatus_fuente),
        "publicado": from_local(row.get("fecha publicacion"))
        or from_local(row.get("fecha expediente")),
        "aclaraciones": from_local(row.get("fecha y hora junta de aclaraciones")),
        "apertura": from_local(row.get("fecha apertura")),
        "fallo": from_local(row.get("fecha de fallo")),
        "categoria": categorize(f"{titulo or ''} {descripcion or ''}", tipo_contratacion),
        "motivo_alcance": motivo,
        "url": clean(row.get("direccion del anuncio")),
    }


def parse_contrato(row: dict[str, str]) -> dict[str, Any] | None:
    codigo = clean(row.get("codigo del contrato"))
    if not codigo:
        return None
    titulo = _title(row, "titulo del contrato", "descripcion del contrato", "titulo del expediente")
    descripcion = clean(row.get("descripcion del contrato"))
    institucion = clean(row.get("institucion"))
    siglas = clean(row.get("siglas de la institucion"))
    motivo = scope_reason(institucion, siglas, f"{titulo or ''} {descripcion or ''}")
    rfc = clean(row.get("rfc"))
    tipo_contratacion = clean(row.get("tipo de contratacion"))
    expediente = clean(row.get("codigo del expediente"))
    return {
        "id": f"cmx:c:{codigo}",
        "fuente": "comprasmx",
        "fuente_id": codigo,
        "procedimiento_id": f"cmx:{expediente}" if expediente else None,
        "numero_procedimiento": clean(row.get("numero de procedimiento")),
        "numero_contrato": clean(row.get("num. del contrato")),
        "titulo": titulo or codigo,
        "descripcion": descripcion if descripcion and descripcion != titulo else None,
        "comprador": institucion,
        "siglas": siglas,
        "unidad": clean(row.get("nombre de la uc")),
        "entidad": clean(row.get("entidad federativa")),
        "tipo_procedimiento": clean(row.get("tipo procedimiento")),
        "ley": clean(row.get("ley")),
        "tipo_contratacion": tipo_contratacion,
        "proveedor": clean(row.get("proveedor o contratista")),
        "proveedor_rfc": public_rfc(rfc),
        "proveedor_tipo": rfc_kind(rfc),
        "estratificacion": clean(row.get("estratificacion")),
        "monto": _amount(row.get("monto sin imp./maximo")) or _amount(row.get("importe drc")),
        "monto_min": _amount(row.get("monto sin imp./minimo")),
        "moneda": clean(row.get("moneda")) or "MXN",
        "publicado": from_local(row.get("fecha de publicacion")),
        "fallo": from_local(row.get("fecha de fallo")),
        "firma": from_local(row.get("fecha de firma del contrato"))
        or from_local(row.get("fecha firma contrato")),
        "inicio": from_local(row.get("fecha de inicio del contrato")),
        "fin": from_local(row.get("fecha de fin del contrato")),
        "estatus_contrato": clean(row.get("estatus contrato")),
        "categoria": categorize(f"{titulo or ''} {descripcion or ''}", tipo_contratacion),
        "motivo_alcance": motivo,
        "url": clean(row.get("direccion del anuncio")),
    }


def parse_file(path: Path, kind: str) -> list[dict[str, Any]]:
    parser = parse_expediente if kind == "expedientes" else parse_contrato
    return [rec for rec in (parser(row) for row in read_rows(path, kind)) if rec]
