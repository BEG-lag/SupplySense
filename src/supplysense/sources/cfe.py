"""CFE: Micrositio de Concursos (msc.cfe.mx).

El buscador público responde con todo el histórico (desde 2015) en un solo JSON si se mandan
los filtros en su valor por omisión. Necesita el token antifalsificación de la página, en la
misma sesión. El detalle de cada procedimiento (empresa de CFE y fechas de apertura y fallo)
solo se obtiene con un POST; se lee para los vigentes nuevos.
"""

from __future__ import annotations

import html
import re
from typing import Any

from ..dates import from_dmy, from_dotnet
from ..http import FetchError, PoliteClient
from ..rules import categorize, normalize_status
from ..text import clean, split_winners

BASE = "https://msc.cfe.mx/Aplicaciones/NCFE/Concursos/"
SEARCH_URL = BASE + "Procedure/getProcBusqueda"
DETAIL_URL = BASE + "Procedure/Details"
PUBLIC_URL = BASE  # el detalle no tiene URL pública; el sitio muestra el número para buscarlo

_TOKEN = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')
DEFAULT_FILTERS = {
    "TipoProcedimientoClave": "",
    "TipoContratacionClave": "",
    "IdEntidadFederativa": "0",
    "Numero": "",
    "Descripcion": "",
    "EstadoProcedimientoContratacionClave": "0",
    "FechaPublicacion": "",
    "FechaPublicacionIni": "",
    "FechaPublicacionFin": "",
    "TestigoSocial": "2",
    "idCaracterProcedimiento": "0",
    "Modalidad": "0",
}


class Session:
    """Token y cookies de una visita al buscador."""

    def __init__(self, client: PoliteClient) -> None:
        self.client = client
        page = client.get_ok(BASE).text
        tokens = _TOKEN.findall(page)
        if not tokens:
            raise FetchError("CFE: la página no trae el token antifalsificación")
        self.token = tokens[-1]

    def search(self) -> list[dict[str, Any]]:
        data = {"__RequestVerificationToken": self.token, **DEFAULT_FILTERS}
        response = self.client.post_ok(
            SEARCH_URL, data=data, headers={"X-Requested-With": "XMLHttpRequest", "Referer": BASE}
        )
        rows = response.json()
        if not isinstance(rows, list):
            raise FetchError("CFE: el buscador no devolvió una lista")
        return rows

    def detail(self, cfe_id: int | str) -> str:
        response = self.client.post_ok(
            DETAIL_URL,
            data={"__RequestVerificationToken": self.token, "id": str(cfe_id)},
            headers={"Referer": BASE},
        )
        return response.text


def parse_row(row: dict[str, Any]) -> dict[str, Any] | None:
    numero = clean(row.get("Numero"))
    if not numero or row.get("Id") is None:
        return None
    estatus_fuente = clean(row.get("EstadoProcedimiento"))
    titulo = clean(row.get("Descripcion")) or numero
    tipo_contratacion = clean(row.get("TipoContratacionClave"))
    monto = row.get("MONTO")
    ganadores = split_winners(row.get("NombProveedorAdjudicado"))
    return {
        "id": f"cfe:{row['Id']}",
        "fuente": "cfe",
        "fuente_id": int(row["Id"]),
        "numero": numero,
        "titulo": titulo,
        "comprador": "CFE",
        "siglas": "CFE",
        "entidad": clean(row.get("EntidadFederativa")),
        "tipo_procedimiento": clean(row.get("TipoProcedimientoClave")),
        "tipo_contratacion": tipo_contratacion,
        "estatus_fuente": estatus_fuente,
        "estatus": normalize_status("cfe", estatus_fuente),
        "publicado": from_dotnet(row.get("FechaPublicacion")),
        "apertura": from_dotnet(row.get("FechaLimiteOfertas")),
        "fallo": from_dotnet(row.get("FechaFallo")),
        "ganadores": ganadores,
        "monto": round(float(monto), 2) if monto and float(monto) > 0 else None,
        "moneda": "MXN" if monto and float(monto) > 0 else None,
        "testigo_social": bool(row.get("TestimonioSocial")),
        "categoria": categorize(titulo, tipo_contratacion),
        "motivo_alcance": "comprador:CFE",
        "url": PUBLIC_URL,
    }


def parse_list(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [rec for rec in (parse_row(r) for r in rows) if rec]


def _lines(page: str) -> list[str]:
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", page)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", text))
    return [line.strip() for line in text.split("\n") if line.strip()]


def _after(lines: list[str], label: str) -> str | None:
    for i, line in enumerate(lines[:-1]):
        if line.lower() == label.lower():
            return lines[i + 1]
    return None


def parse_detail(page: str) -> dict[str, Any]:
    """Empresa, área y fechas de un procedimiento. Lo que no aparece queda en None."""
    lines = _lines(page)
    empresa = clean(_after(lines, "Empresa"))
    area = clean(_after(lines, "Área Contratante"))
    return {
        "empresa": re.sub(r"^\d+\s*-\s*", "", empresa) if empresa else None,
        "unidad": re.sub(r"^\d+\s*-\s*", "", area) if area else None,
        "apertura": from_dmy(_after(lines, "Fecha de Apertura de Ofertas Técnicas")),
        "apertura_economica": from_dmy(_after(lines, "Fecha de Apertura de Ofertas Económicas")),
        "fallo": from_dmy(_after(lines, "Fecha de Fallo")),
    }
