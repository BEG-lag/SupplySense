"""Jalisco: portal de compras de la Secretaría de Administración (compras.jalisco.gob.mx).

La lista es HTML del servidor con celdas identificadas (``stage-cell``, ``code-cell``…) y se
filtra por etapa con GET. El detalle trae el "Calendario de Actividades" con junta, apertura y
fallo. Lo que sale de las listas abiertas se conserva con su último estado (no se borra).
"""

from __future__ import annotations

import html
import re
from typing import Any

from ..dates import from_dmy
from ..http import PoliteClient
from ..rules import categorize
from ..text import clean

BASE = "https://compras.jalisco.gob.mx"
LIST_URL = BASE + "/requisition/tree"
STAGES = {
    "posted": "abierta",
    "in_clarification_meeting": "abierta",
    "in_evaluation": "en_evaluacion",
    "cancelled": "cancelada",
}
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r'<t[hd][^>]*id="([a-z-]+)-cell"[^>]*>(.*?)</t[hd]>', re.S)
_VIEW = re.compile(r"/requisition/view/(\d+)")


def _text(fragment: str) -> str | None:
    text = clean(html.unescape(re.sub(r"<[^>]+>", " ", fragment)))
    return clean(text.strip('"“” ')) if text else None


def parse_list(page: str, stage: str) -> list[dict[str, Any]]:
    if "<tbody>" not in page:
        return []
    body = page.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    records = []
    for row in _ROW.findall(body):
        cells = {k: _text(v) for k, v in _CELL.findall(row)}
        m = _VIEW.search(row)
        if not m or not cells.get("code"):
            continue
        rid = m.group(1)
        titulo = cells.get("description") or cells["code"]
        tipo = cells.get("process-type")
        records.append(
            {
                "id": f"jal:{rid}",
                "fuente": "jalisco",
                "fuente_id": int(rid),
                "numero": cells["code"],
                "titulo": titulo,
                "comprador": cells.get("responsible-unit"),
                "entidad": "Jalisco",
                "orden_gobierno": "GEM",
                "tipo_procedimiento": tipo,
                "caracter": cells.get("character"),
                "estatus_fuente": cells.get("stage"),
                "estatus": STAGES.get(stage, "otro"),
                "publicado": from_dmy(cells.get("published")),
                "categoria": categorize(titulo),
                "url": f"{BASE}/requisition/view/{rid}",
            }
        )
    return records


def fetch_list(client: PoliteClient) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for stage in STAGES:
        page = client.get_ok(LIST_URL, params={"tender_stage": stage, "step": 500}).text
        for rec in parse_list(page, stage):
            records.setdefault(rec["id"], rec)
    return list(records.values())


def _lines(page: str) -> list[str]:
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", page)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", text))
    return [line.strip() for line in text.split("\n") if line.strip()]


def parse_detail(page: str) -> dict[str, Any]:
    """Fechas del "Calendario de Actividades" (se toma el "Desde" de cada acto)."""
    lines = _lines(page)
    out: dict[str, Any] = {}
    for i, line in enumerate(lines[:-1]):
        name = line.lower()
        start = from_dmy(lines[i + 1])
        if not start:
            continue
        if name == "acto de junta aclaratoria":
            out["aclaraciones"] = start
        elif "apertura de propuestas" in name and not name.startswith("registro"):
            out["apertura"] = start
        elif name == "fallo":
            out["fallo"] = start
    return out
