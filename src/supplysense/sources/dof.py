"""Diario Oficial de la Federación: resúmenes de convocatoria (sección "Convocatorias para
concursos de adquisiciones, arrendamientos, obras y servicios del sector público").

La API pública del SIDOF da las notas de cada edición (``/dof/sidof/notas/DD-MM-AAAA``) y el
HTML de cada una (``/notas/docFuente/{codNota}``). Las licitaciones públicas de quien no publica
en ComprasMX también deben salir aquí: universidades, poderes, organismos autónomos, estados y
municipios. Lo que trae número de ComprasMX (LA-, LO-, IA-…) ya lo tenemos y se descarta, igual
que CFE y PEMEX. Las notas vienen en tres formas: tabla de dos columnas (dato y valor), tabla con
encabezados en un renglón y valores en el siguiente, o texto corrido.
"""

from __future__ import annotations

import html
import re
from datetime import date, timedelta
from typing import Any

from ..dates import MONTHS
from ..http import PoliteClient
from ..rules import categorize
from ..text import clean, fold

API = "https://sidof.segob.gob.mx/dof/sidof/notas/{day}"
NOTE_URL = "https://sidof.segob.gob.mx/notas/docFuente/{cod}"
PUBLIC_URL = "https://www.dof.gob.mx/nota_detalle.php?codigo={cod}&fecha={day}"
SECTION = "CV"
_COVERED = re.compile(
    r"COMISION FEDERAL DE ELECTRICIDAD|PETROLEOS MEXICANOS|\bPEMEX\b|\bCFE\b", re.I
)
_COMPRASMX = re.compile(r"\b(?:LA|LO|IA|IO|AA|AO)-\d{2,3}-[A-Z0-9]{2,4}-\d", re.I)
_REF = re.compile(r"\s*-\s*REF:\s*\d+\s*$", re.I)
_CODE = re.compile(r"^\s*[0-9A-Z]{5,6}\s*-\s*")
_LABELS = (
    (
        "numero",
        re.compile(
            r"^(n[uú]mero|no\.?)\b.*(licitaci|procedimiento|concurso|convocatoria)"
            r"|^licitaci[oó]n\s+(p[uú]blica\s+)?(no|n[uú]m)",
            re.I,
        ),
    ),
    ("titulo", re.compile(r"descripci[oó]n|objeto", re.I)),
    ("aclaraciones", re.compile(r"junta.*aclaraci", re.I)),
    ("fallo", re.compile(r"fallo", re.I)),
    ("apertura", re.compile(r"apertura|presentaci[oó]n\s+(y|de)", re.I)),
    ("registro", re.compile(r"l[ií]mite.*(bases|inscrip|registro)", re.I)),
    ("publicado", re.compile(r"publicaci[oó]n", re.I)),
    ("caracter", re.compile(r"car[aá]cter", re.I)),
)
_NUM_TEXT = re.compile(
    r"(?:licitaci[oó]n|concurso|procedimiento)[^.:]{0,80}?(?:No\.?|n[uú]mero)\s*:?\s*"
    r"([A-Z0-9][A-Z0-9][A-Z0-9\-/.]{4,}[A-Z0-9])",
    re.I,
)
# El objeto entre comillas se toma completo (puede traer "H. Cámara"); sin comillas, hasta el punto.
_OBJ_QUOTED = re.compile(
    r"relativ[ao]s?\s+a(?:l|\s+la|\s+los|\s+las)?\s+[“\"«]([^”\"»]{12,300})[”\"»]", re.I
)
_OBJ_TEXT = re.compile(r"relativ[ao]s?\s+a(?:l|\s+la|\s+los|\s+las)?\s+([^”\"».]{12,240})", re.I)
_DATE_WORDS = re.compile(r"(\d{1,2})de([a-zñ]+?)de(\d{4})")
_DATE_NUM = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_TIME = re.compile(r"(\d{1,2}):(\d{2})")
STATES = {
    "aguascalientes": "Aguascalientes",
    "baja california sur": "Baja California Sur",
    "baja california": "Baja California",
    "campeche": "Campeche",
    "chiapas": "Chiapas",
    "chihuahua": "Chihuahua",
    "ciudad de mexico": "Ciudad de México",
    "coahuila": "Coahuila",
    "colima": "Colima",
    "durango": "Durango",
    "estado de mexico": "México",
    "guanajuato": "Guanajuato",
    "guerrero": "Guerrero",
    "hidalgo": "Hidalgo",
    "jalisco": "Jalisco",
    "michoacan": "Michoacán",
    "morelos": "Morelos",
    "nayarit": "Nayarit",
    "nuevo leon": "Nuevo León",
    "oaxaca": "Oaxaca",
    "puebla": "Puebla",
    "queretaro": "Querétaro",
    "quintana roo": "Quintana Roo",
    "san luis potosi": "San Luis Potosí",
    "sinaloa": "Sinaloa",
    "sonora": "Sonora",
    "tabasco": "Tabasco",
    "tamaulipas": "Tamaulipas",
    "tlaxcala": "Tlaxcala",
    "veracruz": "Veracruz",
    "yucatan": "Yucatán",
    "zacatecas": "Zacatecas",
}


def _text(fragment: str) -> str:
    return clean(html.unescape(re.sub(r"<[^>]+>", " ", fragment))) or ""


def parse_when(value: str | None) -> str | None:
    """ "04 de diciembr e de 2026, 12:00 horas" o "24/11/20 26 10:00" → ISO. El DOF corta
    palabras y números con espacios; se compacta antes de leer."""
    if not value:
        return None
    compact = re.sub(r"\s+", "", fold(value))
    day = month = year = None
    m = _DATE_WORDS.search(compact)
    if m and m.group(2) in MONTHS:
        day, month, year = int(m.group(1)), MONTHS[m.group(2)], int(m.group(3))
        rest = compact[m.end() :]
    elif m2 := _DATE_NUM.search(compact):
        day, month, year = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        rest = compact[m2.end() :]
    else:
        return None
    try:
        base = date(year, month, day).isoformat()
    except ValueError:
        return None
    t = _TIME.search(rest[:20])
    if t and int(t.group(1)) < 24:
        return f"{base}T{int(t.group(1)):02d}:{t.group(2)}:00"
    return base


def convocante(titulo: str) -> str:
    """ "070Q94 - h. CAMARA DE DIPUTADOS - REF:582866" → "H. CAMARA DE DIPUTADOS" (en mayúsculas
    para que el sitio lo muestre en tipo título aunque el DOF lo escriba con mayúsculas al azar)."""
    return (clean(_CODE.sub("", _REF.sub("", titulo))) or titulo).upper()


def entidad(name: str) -> str | None:
    folded = fold(name)
    for key, state in STATES.items():
        if re.search(rf"\b{key}\b", folded):
            return state
    return None


def _label(text: str) -> str | None:
    for key, pattern in _LABELS:
        if pattern.search(text):
            return key
    return None


def _groups(page: str) -> list[dict[str, str]]:
    """Datos de cada licitación de la nota, de las tablas de dos columnas o de encabezados."""
    rows = [
        [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S)
    ]
    rows = [r for r in rows if any(r)]
    groups: list[dict[str, str]] = []
    current: dict[str, str] = {}
    i = 0
    while i < len(rows):
        row = rows[i]
        labels = [_label(c) for c in row]
        if len(row) > 2 and sum(1 for x in labels if x) >= 2 and i + 1 < len(rows):
            values = rows[i + 1]
            for key, value in zip(labels, values, strict=False):
                if key and value and key not in current:
                    current[key] = value
            i += 2
            continue
        if len(row) >= 2 and (key := _label(row[0])) and row[1]:
            if key == "numero" and "numero" in current:
                groups.append(current)
                current = {}
            current.setdefault(key, row[1])
        i += 1
    if current:
        groups.append(current)
    return groups


def parse_note(page: str, cod: int, titulo: str, day: str) -> list[dict[str, Any]]:
    """Registros de una nota (una por licitación que describa). Vacío si ya la tenemos por
    ComprasMX, CFE o PEMEX, o si no trae ni número ni objeto."""
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    text = _text(page)
    name = convocante(titulo)
    if _COVERED.search(name) or _COMPRASMX.search(text):
        return []
    groups = _groups(page) or [{}]
    if len(groups) == 1:
        g = groups[0]
        if "numero" not in g and (m := _NUM_TEXT.search(text)):
            g["numero"] = m.group(1).rstrip(".,")
        if "titulo" not in g and (m := _OBJ_QUOTED.search(text) or _OBJ_TEXT.search(text)):
            g["titulo"] = m.group(1)
    records = []
    dmy = f"{day[8:10]}/{day[5:7]}/{day[:4]}"
    for i, g in enumerate(groups):
        objeto = clean((g.get("titulo") or "").strip("“”\"' "))
        numero = clean(g.get("numero"))
        if not objeto or not numero:
            continue
        rec: dict[str, Any] = {
            "id": f"dof:{cod}" + (f"-{i + 1}" if len(groups) > 1 else ""),
            "fuente": "dof",
            "fuente_id": cod,
            "numero": numero,
            "titulo": objeto,
            "comprador": name,
            "entidad": entidad(name),
            "tipo_procedimiento": "Licitación pública",
            "caracter": clean(g.get("caracter")),
            "estatus": "abierta",
            "publicado": day,
            "categoria": categorize(objeto),
            "url": PUBLIC_URL.format(cod=cod, day=dmy),
        }
        for key in ("aclaraciones", "apertura", "fallo", "registro"):
            if when := parse_when(g.get(key)):
                rec[key] = when
        records.append(rec)
    return records


def list_notes(data: dict[str, Any]) -> list[dict[str, Any]]:
    notes = []
    for block in ("NotasMatutinas", "NotasVespertinas", "NotasExtraordinarias"):
        for note in data.get(block) or []:
            if note.get("codOrgaUno") == SECTION and note.get("codNota"):
                notes.append(note)
    return notes


def fetch_day(client: PoliteClient, day: date, known: set[int]) -> list[dict[str, Any]]:
    data = client.get_ok(API.format(day=day.strftime("%d-%m-%Y"))).json()
    records = []
    for note in list_notes(data):
        cod = int(note["codNota"])
        if cod in known or _COVERED.search(note.get("titulo") or ""):
            continue
        page = client.get_ok(NOTE_URL.format(cod=cod)).text
        records += parse_note(page, cod, note.get("titulo") or "", day.isoformat())
    return records


def days_back(today: date, n: int) -> list[date]:
    return [today - timedelta(days=k) for k in range(n, -1, -1)]
