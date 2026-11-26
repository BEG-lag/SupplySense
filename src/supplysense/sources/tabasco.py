"""Tabasco: Compranet 3.0 de la Secretaría Anticorrupción y Buen Gobierno del estado
(portalanticorrupcion.tabasco.gob.mx:85/compranet/Publico), licitaciones con normatividad estatal.

Es ASP.NET WebForms con tablas DevExpress: la primera visita crea la sesión y la segunda ya trae
la tabla del ejercicio en curso, agrupada por convocante. Se pagina con POST de los campos ocultos
de la página. Tres pantallas por materia (adquisiciones y obra pública):

* ``Vigentes``: en periodo de venta de bases (abiertas).
* ``Seguimiento``: todas las del año con su estatus (SEGUIMIENTO, TERMINADA, DESIERTA, CANCELADA)
  y la liga a la convocatoria y a las actas.
* ``Contratos``: número de licitación, proveedor, fecha e importe (con IVA).

El objeto, la ley y las fechas solo vienen en la convocatoria, casi siempre un PDF escaneado sin
texto. El objeto y la fecha de publicación salen entonces del Periódico Oficial del Estado
(``tabasco.gob.mx/PeriodicoOficial/resultado/LICITACI/0?page=N``), que resume cada convocatoria
con su convocante y, casi siempre, el número de licitación o su consecutivo. El prefijo del número
(``5627D901``) identifica al convocante. El iframe viejo (187.157.9.81) ya no responde.
"""

from __future__ import annotations

import html
import io
import logging
import re
import unicodedata
from typing import Any

from pypdf import PdfReader

from ..dates import from_dmy, from_loose
from ..http import PoliteClient
from ..text import clean, split_winners, title_name

BASE = "https://portalanticorrupcion.tabasco.gob.mx:85/compranet/Publico/"
SECTIONS = {
    "adq": ("Licitacion_Adquisiciones/Adq_", "Adquisiciones"),
    "obra": ("Licitacion_Obra_Pub/Obra_Pub_", "Obra pública"),
}
STATUS = {
    "SEGUIMIENTO": "en_evaluacion",
    "TERMINADA": "concluida",
    "DESIERTA": "desierta",
    "CANCELADA": "cancelada",
}
FIRST_YEAR = 2022  # índice 0 del selector de ejercicio
GRID = "ctl00$ContentPlaceHolder1$grd_licitaciones"
YEAR_FIELD = "ctl00$ContentPlaceHolder1$chklist_anio"
LAWS = (
    "Ley de Adquisiciones, Arrendamientos y Prestación de Servicios del Estado de Tabasco",
    "Ley de Obras Públicas y Servicios Relacionados con las Mismas del Estado de Tabasco",
)
_ROW = re.compile(r'<tr id="[^"]*_(DXGroupRowExp\d+|DXDataRow\d+)"[^>]*>(.*?)</tr>', re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_LINK = re.compile(r'id="[^"]*?(id_[a-z_]+)"[^>]*href="([^"]+)"')
_GROUP = re.compile(r"Nombre del Convocante:\s*([^<(]+)")
_HIDDEN = re.compile(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"')
_PAGES = re.compile(r"P&#225;gina \d+ de (\d+)")
_NUMBER = re.compile(r"^[0-9A-Z]{4,}-\d{3}-\d{4}$")


def _text(fragment: str) -> str:
    return clean(html.unescape(re.sub(r"<[^>]+>", " ", fragment))) or ""


def grid_rows(page: str) -> list[tuple[str | None, list[str], dict[str, str]]]:
    """(convocante, celdas, ligas por id) de cada renglón de datos de la tabla."""
    rows = []
    convocante = None
    for kind, body in _ROW.findall(page):
        if kind.startswith("DXGroup"):
            m = _GROUP.search(body)
            convocante = clean(html.unescape(m.group(1))) if m else convocante
            continue
        links = {k: html.unescape(v) for k, v in _LINK.findall(body)}
        rows.append((convocante, [_text(c) for c in _CELL.findall(body)], links))
    return rows


def _url(href: str | None) -> str | None:
    if not href:
        return None
    return href if href.startswith("http") else BASE + href.lstrip("./")


def parse_procedures(page: str, kind: str, vigente: bool = False) -> list[dict[str, Any]]:
    records = []
    for convocante, cells, links in grid_rows(page):
        numero = next((c for c in cells if _NUMBER.match(c)), None)
        if not numero:
            continue
        raw = cells[-1].upper() if cells else ""
        estatus = "abierta" if vigente else STATUS.get(raw, "en_evaluacion")
        records.append(
            {
                "id": f"tab:{numero}",
                "fuente": "tabasco",
                "fuente_id": numero,
                "numero": numero,
                "titulo": f"Licitación {numero}",
                "comprador": convocante,
                "entidad": "Tabasco",
                "orden_gobierno": "GEM",
                "tipo_procedimiento": "Licitación pública",
                "tipo_contratacion": SECTIONS[kind][1],
                "estatus_fuente": "VIGENTE" if vigente else raw or None,
                "estatus": estatus,
                "actas": sorted(k for k in links if k.startswith("id_link_")),
                "url": _url(links.get("id_linknum_lic")),
            }
        )
    return records


def parse_contracts(page: str) -> dict[str, dict[str, Any]]:
    """Proveedores e importe total por número de licitación."""
    out: dict[str, dict[str, Any]] = {}
    for _, cells, _ in grid_rows(page):
        cells = [c for c in cells if c]
        if len(cells) < 4 or not _NUMBER.match(cells[0]):
            continue
        amount = re.sub(r"[^\d.]", "", cells[-1])
        entry = out.setdefault(cells[0], {"ganadores": [], "monto": 0.0, "firma": None})
        for name in split_winners(cells[2]) or [cells[2]]:
            if name not in entry["ganadores"]:
                entry["ganadores"].append(name)
        if amount:
            entry["monto"] = round(entry["monto"] + float(amount), 2)
        entry["firma"] = entry["firma"] or from_dmy(cells[3])
    return out


# ── convocatoria ─────────────────────────────────────────────────────────────

_OBJETO = re.compile(
    r"(?:relativ[ao]s?|referente)\s+a(?:l|\s+la|\s+los|\s+las)?\s+(.{12,400}?),?\s+de\s+conformidad",
    re.I | re.S,
)
_WHEN = {
    "aclaraciones": re.compile(
        r"junta de aclaraciones se llevar[áa] a cabo el d[íil]a (.{8,60})", re.I
    ),
    "apertura": re.compile(
        r"(?:acto de )?presentaci[óo]n (?:y apertura )?de (?:las )?(?:proposiciones|propuestas)"
        r"[^.]{0,80}?se llevar[áa] a cabo el d[íil]a (.{8,60})",
        re.I,
    ),
    "fallo": re.compile(
        r"fallo se (?:dar[áa] a conocer|llevar[áa] a cabo) el d[íil]a (.{8,60})", re.I
    ),
}
# Tabla de la convocatoria: el texto sale en orden de columnas (bases, junta, apertura técnica,
# apertura económica), primero las fechas y luego las horas.
_TABLE = re.compile(r"No\.\s*de\s*licitaci[óo]n(.{40,900}?)(?:Anexo|Partida)", re.I | re.S)
_TABLE_DATE = re.compile(r"(\d{1,2}(?:\s?[O0-9])?)\s+de\s+([a-záéíóú]{4,11})\b", re.I)
_YEAR = re.compile(r"\b(20\d{2})\b")
_TABLE_TIME = re.compile(r"(\d{1,2}[:.]\d{2})\s*h")
_TABLE_KEYS = ("registro", "aclaraciones", "apertura", "apertura_economica")


def parse_text(text: str, year: int | None = None) -> dict[str, Any]:
    """Objeto, ley, carácter y fechas. En la tabla, el año sale separado de cada día: se toma
    ``year`` (el del número de licitación) o el primero que aparezca."""
    text = re.sub(r"\s+", " ", text)
    out: dict[str, Any] = {}
    if m := _OBJETO.search(text):
        out["titulo"] = clean(m.group(1).strip(' .,:;"“”'))
    if m := _TABLE.search(text):
        segment = m.group(1)
        found = _YEAR.search(segment) or _YEAR.search(text)
        y = year or (int(found.group(1)) if found else None)
        days = [f"{d} de {mo} de {y}" for d, mo in _TABLE_DATE.findall(segment)]
        days = [d for d in days if from_loose(d)]
        times = _TABLE_TIME.findall(segment)
        for i, (key, day) in enumerate(zip(_TABLE_KEYS, days, strict=False)):
            when = from_loose(f"{day} {times[i]}" if i < len(times) else day)
            if when:
                out[key] = when
    for key, pattern in _WHEN.items():
        if (m := pattern.search(text)) and (when := from_loose(m.group(1))):
            out[key] = when
    folded = text.lower()
    for law in LAWS:
        if law.lower() in folded:
            out["ley"] = law
            break
    if "nacional" in folded[:1500]:
        out["caracter"] = "Nacional"
    if "estatal" in folded[:1500] and "licitación pública estatal" in folded[:1500]:
        out["caracter"] = "Estatal"
    return out


def pdf_text(data: bytes) -> str:
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    return " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages[:6])


# ── lectura ──────────────────────────────────────────────────────────────────


def _fields(page: str) -> dict[str, str]:
    return {name: html.unescape(value) for name, value in _HIDDEN.findall(page)}


def fetch_grid(client: PoliteClient, path: str, year: int | None = None) -> list[str]:
    """Todas las páginas de una pantalla (del ejercicio ``year`` o el en curso)."""
    url = BASE + path
    client.get_ok(url)  # crea la sesión
    page = client.get_ok(url).text
    if year is not None:
        data = _fields(page) | {
            "__EVENTTARGET": YEAR_FIELD,
            "__EVENTARGUMENT": "",
            YEAR_FIELD: str(year - FIRST_YEAR),
        }
        page = client.post_ok(url, data=data).text
    pages = [page]
    m = _PAGES.search(page)
    for k in range(1, int(m.group(1)) if m else 1):
        arg = f"PN{k}"
        data = _fields(page) | {
            "__EVENTTARGET": GRID,
            "__EVENTARGUMENT": f"12|PAGERONCLICK{len(arg)}|{arg}",
        }
        page = client.post_ok(url, data=data).text
        pages.append(page)
    return pages


def fetch_all(client: PoliteClient, year: int | None = None) -> list[dict[str, Any]]:
    """Procedimientos de adquisiciones y obra con su estatus y, si hay, ganadores e importe."""
    records: dict[str, dict[str, Any]] = {}
    for kind, (prefix, _) in SECTIONS.items():
        contracts: dict[str, dict[str, Any]] = {}
        for page in fetch_grid(client, prefix + "Contratos.aspx", year):
            contracts.update(parse_contracts(page))
        for page in fetch_grid(client, prefix + "Seguimiento.aspx", year):
            for rec in parse_procedures(page, kind):
                records[rec["id"]] = rec
        if year is None:
            for page in fetch_grid(client, prefix + "Vigentes.aspx"):
                for rec in parse_procedures(page, kind, vigente=True):
                    records[rec["id"]] = {**records.get(rec["id"], {}), **rec}
        for numero, award in contracts.items():
            rec = records.get(f"tab:{numero}")
            if rec and award["ganadores"]:
                rec.update(
                    ganadores=award["ganadores"],
                    monto=award["monto"] or None,
                    moneda="MXN",
                    monto_nota="con IVA",
                )
                if rec["estatus"] in ("concluida", "en_evaluacion"):
                    rec["estatus"] = "adjudicada"  # con contrato firmado
    return list(records.values())


# ── Periódico Oficial ────────────────────────────────────────────────────────

POE_URL = "https://tabasco.gob.mx/PeriodicoOficial/resultado/LICITACI/0"
_MONTHS = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}  # fmt: skip
_POE_DATE = re.compile(r"(\d{1,2})/([A-Za-z]{3})/(\d{4})")
_POE_NUMBER = re.compile(r"5627\s?[A-Z]\s?\d{3}\s?-\s?(\d{3})\s?-\s?(\d{2,4})")
_POE_SEQ = re.compile(
    r"(?:CONVOCATORIA|LICITACI[ÓO]N)(?:\s+(?:N[OÚ]\.?|P[ÚU]BLICA|NACIONAL|ESTATAL|DE|LA|CAR[ÁA]CTER))*"
    r"\s+(\d{2,3})\b",
    re.I,
)
_POE_OBJECT = re.compile(
    r"(?:REFERENTE|RELATIV[AO]S?|CORRESPONDIENTES?)\s+A(?:L|\s+LA|\s+LOS|\s+LAS)?\s+(.{8,})"
    r"|PARA\s+LA\s+((?:ADQUISICI|CONTRATACI|PRESTACI|ADJUDICACI).{8,})",
    re.I,
)
# Siglas que el Periódico Oficial usa por convocante (se comparan sin acentos).
_ALIASES = {
    "cobatab": "colegio de bachilleres",
    "isset": "instituto de seguridad social",
    "salud": "servicios de salud",
    "dif": "desarrollo integral de la familia",
    "ceas": "comision estatal de agua",
    "sop": "obras publicas",
    "sotop": "obras publicas",
    "subsecretaria de obras publicas": "obras publicas",
    "secretaria de obras publicas": "obras publicas",
    "secretaria de administracion de finanzas": "administracion y finanzas",
    "proteccion civil": "proteccion civil",
}


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", value).strip()


def parse_poe(page: str) -> list[dict[str, Any]]:
    items = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) < 5 or not (m := _POE_DATE.search(cells[0])):
            continue
        month = _MONTHS.get(m.group(2).lower())
        if not month:
            continue
        pdf = re.search(r'href="([^"]+\.pdf)"', row)
        items.append(
            {
                "fecha": f"{m.group(3)}-{month:02d}-{int(m.group(1)):02d}",
                "descripcion": cells[4],
                "pdf": pdf.group(1) if pdf else None,
            }
        )
    return items


def fetch_poe(client: PoliteClient, pages: int = 1) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for page in range(pages):
        found = parse_poe(client.get_ok(POE_URL, params={"page": page} if page else None).text)
        items += found
        if not found:
            break
    return items


def _poe_object(text: str) -> str | None:
    m = _POE_OBJECT.search(text)
    if not m:
        return None
    objeto = (m.group(1) or m.group(2) or "").strip(" .,")
    # "relativa a las personas físicas … inscritas": la nota no dice qué se compra.
    if re.search(r"PERSONAS F[ÍI]SICAS|LICITACIONES?:?\s*5627|LICITACI[ÓO]N NO\.", objeto, re.I):
        return None
    return clean(objeto)


def enrich(records: list[dict[str, Any]], poe: list[dict[str, Any]]) -> int:
    """Pone objeto, publicación y liga del Periódico Oficial a las licitaciones que casan por
    número completo, o por convocante, consecutivo y año. Llena el convocante que falte con el
    de su prefijo. Devuelve cuántas se enriquecieron."""
    names: dict[str, str] = {}
    for rec in records:
        if rec.get("comprador"):
            names.setdefault(rec["numero"][:8], rec["comprador"])
    for rec in records:
        if not rec.get("comprador") and rec["numero"][:8] in names:
            rec["comprador"] = names[rec["numero"][:8]]
    by_number = {(r["numero"][:8], r["numero"][9:12], r["numero"][-4:]): r for r in records}
    matched = 0
    for item in poe:
        text = item["descripcion"]
        objeto = _poe_object(text)
        if not objeto:
            continue
        year = item["fecha"][:4]
        targets = []
        for m in _POE_NUMBER.finditer(text):
            code = re.sub(r"\s", "", m.group(0))[:8]
            y = m.group(2) if len(m.group(2)) == 4 else "20" + m.group(2)
            if rec := by_number.get((code, m.group(1), y)):
                targets.append(rec)
        if not targets and (seq := _POE_SEQ.search(text)):
            who = _fold(text.split(".", 1)[0])
            who = _ALIASES.get(who, who)
            codes = {c for c, n in names.items() if who and (who in _fold(n) or _fold(n) in who)}
            number = f"{int(seq.group(1)):03d}"
            targets = [
                by_number[k] for k in by_number if k[0] in codes and k[1] == number and k[2] == year
            ]
        for rec in targets:
            if rec["titulo"].startswith("Licitación "):
                rec["titulo"] = objeto
                matched += 1
            rec.setdefault("publicado", item["fecha"])
            if item.get("pdf"):
                rec.setdefault("periodico_oficial", item["pdf"])
    # Sin nota que case: al menos se dice quién convoca.
    for rec in records:
        if rec["titulo"] == f"Licitación {rec['numero']}" and rec.get("comprador"):
            rec["titulo"] = f"Licitación {rec['numero']} de {title_name(rec['comprador'])}"
    return matched
