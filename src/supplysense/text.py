"""Texto: decodificación de los CSV oficiales, limpieza y normalización de nombres.

Los archivos de ComprasMX vienen en latin-1 con secuencias UTF-8 sueltas ("CLÁSICA" escrito
en UTF-8 dentro de un archivo latin-1) y algunas palabras ya corruptas desde el origen
("MONSEÃOR"). ``decode_mixed`` lee cada secuencia UTF-8 válida como UTF-8 y el resto como
cp1252; ``repair`` arregla las corrupciones conocidas.
"""

from __future__ import annotations

import re
import unicodedata

_UTF8_SEQ = re.compile(
    rb"[\xc2-\xdf][\x80-\xbf]|[\xe0-\xef][\x80-\xbf]{2}|[\xf0-\xf4][\x80-\xbf]{3}"
)
# cp1252 deja sin definir 0x81, 0x8d, 0x8f, 0x90 y 0x9d: se descartan.
_CP1252_C1 = {
    code: (bytes([code]).decode("cp1252", errors="ignore") or "") for code in range(0x80, 0xA0)
}

# Corrupciones vistas en los archivos de ComprasMX 2025 y 2026.
_REPAIRS = {
    "MONSEÃOR": "MONSEÑOR",
    "ÃN": "ÓN",
    "Ã‘": "Ñ",
    "Ã“": "Ó",
    "Ã‰": "É",
    "Ãš": "Ú",
}

_SPACES = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_LEGAL_SUFFIX = re.compile(
    r"\b(s\.?\s?a\.?\s?p\.?\s?i\.?|s\.?\s?a\.?\s?b\.?|s\.?\s?de\s?r\.?\s?l\.?|s\.?\s?a\.?|"
    r"s\.?\s?c\.?|de\s?c\.?\s?v\.?|c\.?\s?v\.?|inc\.?|llc|ltd\.?|s\.?\s?r\.?\s?l\.?)\b",
    re.I,
)
_RFC_MORAL = re.compile(r"^[A-ZÑ&]{3}\d{6}[A-Z0-9]{3}$")
_RFC_FISICA = re.compile(r"^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$")
GENERIC_RFC = {"XEXX010101000", "XAXX010101000"}


def decode_mixed(raw: bytes) -> str:
    out: list[str] = []
    pos = 0
    for m in _UTF8_SEQ.finditer(raw):
        out.append(raw[pos : m.start()].decode("latin-1"))
        try:
            out.append(m.group().decode("utf-8"))
        except UnicodeDecodeError:
            out.append(m.group().decode("latin-1"))
        pos = m.end()
    out.append(raw[pos:].decode("latin-1"))
    return "".join(out).translate(_CP1252_C1)


def repair(text: str) -> str:
    for bad, good in _REPAIRS.items():
        if bad in text:
            text = text.replace(bad, good)
    return text


def clean(value: str | None) -> str | None:
    """Espacios colapsados; vacío → None."""
    if value is None:
        return None
    text = _SPACES.sub(" ", repair(str(value))).strip()
    return text or None


def fold(value: str | None) -> str:
    """Minúsculas sin acentos, para buscar y clasificar."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).replace("ñ", "n")


def slug(value: str) -> str:
    return _NON_ALNUM.sub("-", fold(value)).strip("-")


def company_key(name: str | None) -> str | None:
    """Clave estable de una empresa a partir de su nombre (sin régimen societario)."""
    if not name:
        return None
    base = _LEGAL_SUFFIX.sub(" ", fold(name))
    key = _NON_ALNUM.sub("-", base).strip("-")
    return key or None


def rfc_kind(rfc: str | None) -> str | None:
    """``moral``, ``fisica``, ``generico`` o None si no parece RFC."""
    if not rfc:
        return None
    value = rfc.strip().upper()
    if value in GENERIC_RFC:
        return "generico"
    if _RFC_MORAL.match(value):
        return "moral"
    if _RFC_FISICA.match(value):
        return "fisica"
    return None


def public_rfc(rfc: str | None) -> str | None:
    """Solo el RFC de personas morales se publica: el de personas físicas trae su fecha de
    nacimiento y es dato personal; los genéricos de extranjeros no identifican a nadie."""
    return rfc.strip().upper() if rfc_kind(rfc) == "moral" else None


_SUFFIX_ONLY = re.compile(
    r"^(s\.?\s?a\.?|s\.?\s?de\s?r|de\s?c\.?\s?v|c\.?\s?v\.?|s\.?\s?c\.?|s\.?\s?a\.?\s?p\.?\s?i|"
    r"s\.?\s?a\.?\s?b|inc|llc|ltd|s\.?\s?r\.?\s?l|a\.?\s?g\.?|gmbh|b\.?\s?v\.?|s\.?\s?l\.?|"
    r"s\.?\s?a\.?\s?s|plc|limited|corp)\b"
)


_RFC_TOKEN = re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b")
# Identificadores fiscales extranjeros al inicio ("9132069176735 - ENTIA DE MEXICO").
_TAX_ID_PREFIX = re.compile(r"^\s*(?=[A-Z0-9&Ñ/]*\d)[A-Z0-9&Ñ/]{8,}\s+-\s+")
_RFC_PREFIX = re.compile(r"^\s*(?:[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\s*/?\s*)+(?:-\s*)?")


def strip_rfcs(name: str | None) -> str | None:
    """CFE a veces antepone RFCs al nombre ("GOPR6102065R0/DMC0310209U4 - NOMBRE"). Se quitan
    todos: el de una persona física trae su fecha de nacimiento."""
    if not name:
        return name
    text = _RFC_PREFIX.sub("", name)
    text = _RFC_TOKEN.sub("", text)
    text = _TAX_ID_PREFIX.sub("", text)
    return clean(text.strip(" /-"))


def split_winners(value: str | None) -> list[str]:
    """CFE separa a los ganadores con coma y deja una coma al final. Una coma seguida solo del
    régimen societario ("INTEGRALES, S.A. DE C.V.") no separa empresas."""
    if not value:
        return []
    merged: list[str] = []
    for chunk in value.split(","):
        part = strip_rfcs(clean(chunk))
        if not part:
            continue
        if merged and _SUFFIX_ONLY.match(fold(part)):
            merged[-1] = f"{merged[-1]}, {part}"
        else:
            merged.append(part)
    return merged
