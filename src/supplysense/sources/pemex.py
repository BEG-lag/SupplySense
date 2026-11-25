"""PEMEX: concursos abiertos publicados en su SharePoint, sin login.

PEMEX no publica en ComprasMX ni da montos o ganadores en datos abiertos. Su campo
``vencimiento`` no es la fecha límite del concurso sino el retiro del aviso (un año después de
publicado), así que el estatus "abierta" de PEMEX es estimado: ver ``OPEN_DAYS``.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from ..dates import from_utc_iso
from ..http import PoliteClient
from ..rules import categorize
from ..text import clean

SITE = "https://www.pemex.com/procura/procedimientos-de-contratacion/concursosabiertos"
API = SITE + "/_api/web/lists/getbytitle('{lista}')/items"
FIELDS = (
    "Id,Title,descripcion,inicio,vencimiento,tipoevento,tiposuministro,areacontratante,"
    "ID_SISCEP,Modified"
)
# Días tras la publicación en que tratamos un aviso de PEMEX como abierto [SUPUESTO].
OPEN_DAYS = 30

LISTS: dict[str, tuple[str, str]] = {
    # lista: (segmento, página oficial donde se publica)
    "Concursos-Abiertos-PEP": ("Exploración y Producción", "Paginas/PEP.aspx"),
    "Concursos-Abiertos-PTI": (
        "Transformación Industrial",
        "Paginas/Pemex-Transformación-Industrial.aspx",
    ),
    "Concursos-Abiertos-PL": ("Logística", "Paginas/Pemex-Logística.aspx"),
    "Concursos-e-invitaciones": ("Servicios y bienes de soporte", "Paginas/Pemex.aspx"),
    "Concursos-Abiertos-PE": ("Etileno", "Paginas/default.aspx"),
    "Concursos-Abiertos-PF": ("Fertilizantes", "Paginas/default.aspx"),
    "Concursos-Abiertos-PPS": ("Perforación y Servicios", "Paginas/default.aspx"),
    "Concursos-Abiertos-PCS": ("Cogeneración y Servicios", "Paginas/default.aspx"),
}


def fetch_list(client: PoliteClient, lista: str) -> list[dict[str, Any]]:
    url = API.format(lista=lista) + f"?$select={FIELDS}&$top=5000&$orderby=Id desc"
    items: list[dict[str, Any]] = []
    while url:
        payload = client.get_ok(url, headers={"Accept": "application/json;odata=verbose"}).json()
        data = payload["d"]
        items.extend(data["results"])
        url = data.get("__next")
    return items


def parse_item(lista: str, item: dict[str, Any]) -> dict[str, Any] | None:
    numero = clean(item.get("Title"))
    if not numero or item.get("Id") is None:
        return None
    segmento, page = LISTS[lista]
    titulo = clean(item.get("descripcion")) or numero
    tipo = clean(item.get("tiposuministro"))
    return {
        "id": f"pemex:{lista}:{item['Id']}",
        "fuente": "pemex",
        "fuente_id": int(item["Id"]),
        "numero": numero,
        "titulo": titulo,
        "comprador": "PEMEX",
        "siglas": "PEMEX",
        "segmento": segmento,
        "unidad": clean(item.get("areacontratante")),
        "tipo_procedimiento": clean(item.get("tipoevento")),
        "tipo_contratacion": tipo,
        "publicado": from_utc_iso(item.get("inicio")),
        "retiro_aviso": from_utc_iso(item.get("vencimiento")),
        "siscep": clean(item.get("ID_SISCEP")),
        "categoria": categorize(titulo, tipo),
        "motivo_alcance": "comprador:PEMEX",
        "url": f"{SITE}/{quote(page)}",
    }


def fetch(client: PoliteClient) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for lista in LISTS:
        for item in fetch_list(client, lista):
            rec = parse_item(lista, item)
            if rec:
                records.append(rec)
    return records
