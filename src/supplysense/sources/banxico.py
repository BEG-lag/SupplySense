"""Banco de México: Portal de Proveedores (www.banxico.org.mx/PortalProveedores).

Banxico compra con sus propias normas y no publica en ComprasMX. El portal responde JSON a
formularios POST sin sesión: ``ConsultaProcedimientos`` (en curso) y
``ConsultaProcedimientosCerrados`` (histórico desde 2021), por materia (1 adquisiciones,
2 enajenaciones, 3 obra). ``ConsultaEtapas`` da las fechas de cada etapa. El JSON viene en
ISO-8859-1 sin declararlo. Ganador y monto solo están en las actas en PDF y no se leen.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..dates import from_dmy
from ..http import PoliteClient
from ..rules import categorize
from ..text import clean

BASE = "https://www.banxico.org.mx/PortalProveedores/"
MATERIAS = (1, 2, 3)
STATUS = {"A": "abierta", "L": "en_evaluacion", "F": "concluida", "C": "concluida"}
STAGES = {
    "aclaraciones a la convocatoria": "aclaraciones",
    "acto de presentación y apertura de proposiciones": "apertura",
    "publicación de fallo": "fallo",
}
_NUMERO = re.compile(r"No\.?\s*([A-Z]{2}-[A-Z0-9-]+)")
_FORM = {"BMXC_filtro": "", "BMXC_tipo": "", "BMXC_fecha_inicial": "", "BMXC_fecha_final": ""}


def _json(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("latin-1"))


def parse_row(row: dict[str, Any]) -> dict[str, Any] | None:
    pid = str(row.get("procedimiento") or "").strip()
    if not pid:
        return None
    titulo_fuente = clean(row.get("titulo")) or ""
    m = _NUMERO.search(titulo_fuente)
    numero = m.group(1) if m else clean(row.get("numProcedimiento")) or pid
    objeto = clean(row.get("descProcedimiento") or row.get("descripcion")) or titulo_fuente
    estatus = STATUS.get(row.get("status") or "", "otro")
    if clean(row.get("motivoCancelacion")):
        estatus = "cancelada"
    caracter = (
        "Internacional"
        if "internacional" in titulo_fuente.lower()
        else ("Nacional" if "nacional" in titulo_fuente.lower() else None)
    )
    return {
        "id": f"bmx:{pid}",
        "fuente": "banxico",
        "fuente_id": int(pid) if pid.isdigit() else pid,
        "numero": numero,
        "titulo": objeto,
        "comprador": "Banco de México",
        "entidad": "Ciudad de México",
        "orden_gobierno": "Autónomo",
        "tipo_procedimiento": clean(row.get("descTipoProc")),
        "tipo_contratacion": clean(row.get("descMateria")),
        "caracter": caracter,
        "estatus_fuente": clean(row.get("descStatus")),
        "estatus": estatus,
        "publicado": from_dmy(row.get("fechaPublicacion")),
        "categoria": categorize(objeto),
        "url": BASE,
    }


def parse_stages(rows: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        key = STAGES.get((row.get("descripcion") or "").strip().lower())
        when = from_dmy(f"{row.get('fechaProgramada') or ''} {row.get('horaProgramada') or ''}")
        if key and when:
            out[key] = when
    return out


def fetch_list(client: PoliteClient, history: bool = True) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    endpoints = ["ConsultaProcedimientos"] + (["ConsultaProcedimientosCerrados"] if history else [])
    for endpoint in endpoints:
        for materia in MATERIAS:
            raw = client.post_ok(BASE + endpoint, data={"BMXC_materia": materia, **_FORM}).content
            for row in _json(raw).get("data") or []:
                rec = parse_row(row)
                if rec:
                    records.setdefault(rec["id"], rec)
    return list(records.values())


def fetch_stages(client: PoliteClient, pid: int | str) -> dict[str, str]:
    raw = client.post_ok(BASE + "ConsultaEtapas", data={"BMXC_idProcedimiento": pid}).content
    return parse_stages(_json(raw).get("data") or [])
