"""Fechas en hora del centro de México.

Las fuentes mezclan formatos: CFE manda ``/Date(ms)/`` (UTC), PEMEX ISO en UTC y ComprasMX
``AAAA-MM-DD hh:mm:ss`` en hora local. Todo se guarda como texto ISO en hora local, sin zona,
porque así lo publican las dependencias y así se lee en el sitio.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

MX = ZoneInfo("America/Mexico_City")

_DOTNET = re.compile(r"/Date\((-?\d+)\)/")
_DMY = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?")


def today_mx() -> date:
    return datetime.now(MX).date()


def from_dotnet(value: str | None) -> str | None:
    """``/Date(1795623289860)/`` → ``2026-11-25T10:14:49`` (hora del centro)."""
    if not value:
        return None
    m = _DOTNET.search(value)
    if not m:
        return None
    moment = datetime.fromtimestamp(int(m.group(1)) / 1000, tz=UTC).astimezone(MX)
    return moment.replace(tzinfo=None).isoformat(timespec="seconds")


def from_utc_iso(value: str | None) -> str | None:
    """``2026-11-19T06:00:00Z`` → ``2026-11-19T00:00:00`` (hora del centro)."""
    if not value:
        return None
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(MX).replace(tzinfo=None).isoformat(timespec="seconds")


def from_local(value: str | None) -> str | None:
    """``2026-11-20 19:17:22`` o ``2026-11-20`` → ISO local; vacío o ilegible → None."""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt == "%Y-%m-%d":
            return parsed.date().isoformat()
        return parsed.isoformat(timespec="seconds")
    return None


def from_dmy(value: str | None) -> str | None:
    """``04/12/2026 09:00 hrs`` → ``2026-12-04T09:00:00``; ``04/12/2026`` → ``2026-12-04``."""
    if not value:
        return None
    m = _DMY.search(value)
    if not m:
        return None
    day, month, year, hour, minute = m.groups()
    try:
        if hour is None:
            return date(int(year), int(month), int(day)).isoformat()
        return datetime(int(year), int(month), int(day), int(hour), int(minute)).isoformat(
            timespec="seconds"
        )
    except ValueError:
        return None


def day_of(value: str | None) -> str | None:
    """Parte de fecha de un ISO (``2026-11-25T10:14:49`` → ``2026-11-25``)."""
    return value[:10] if value else None


MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
_ES_SLASH = re.compile(
    r"(\d{1,2})\s*/\s*([a-záéíóú]+)\s*/\s*(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", re.I
)
_ES_WORDS = re.compile(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de(?:l)?\s+(\d{4})", re.I)


def from_spanish(value: str | None) -> str | None:
    """``23/noviembre/2026 14:00`` → ``2026-11-23T14:00:00``; ``17 de noviembre de 2026`` →
    ``2026-11-17``."""
    if not value:
        return None
    m = _ES_SLASH.search(value)
    if m:
        day, month, year, hour, minute = m.groups()
        month_n = MONTHS.get(month.lower())
        if not month_n:
            return None
        try:
            if hour is None:
                return date(int(year), month_n, int(day)).isoformat()
            return datetime(int(year), month_n, int(day), int(hour), int(minute)).isoformat(
                timespec="seconds"
            )
        except ValueError:
            return None
    m = _ES_WORDS.search(value)
    if m:
        day, month, year = m.groups()
        month_n = MONTHS.get(month.lower())
        try:
            return date(int(year), month_n, int(day)).isoformat() if month_n else None
        except ValueError:
            return None
    return None


_LOOSE_WORDS = re.compile(r"(\d{1,2})de([a-z]+?)del?(\d{4})")
_LOOSE_NUM = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_LOOSE_TIME = re.compile(r"(\d{1,2})[:.](\d{2})")


def from_loose(value: str | None) -> str | None:
    """Fecha de texto con cortes y ruido de OCR: "04 de diciembr e de 2026, 12:00 horas",
    "1 O de noviembre del2026 a las 10:00", "24/11/20 26". Se compacta antes de leer."""
    if not value:
        return None
    compact = re.sub(r"\s+", "", _fold(value))
    compact = re.sub(r"(?<=\d)o(?=de)", "0", compact)  # "1 O de" leído por OCR
    m = _LOOSE_WORDS.search(compact)
    if m and m.group(2) in MONTHS:
        day, month, year = int(m.group(1)), MONTHS[m.group(2)], int(m.group(3))
    elif m := _LOOSE_NUM.search(compact):
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        return None
    try:
        base = date(year, month, day).isoformat()
    except ValueError:
        return None
    t = _LOOSE_TIME.search(compact[m.end() : m.end() + 20])
    if t and int(t.group(1)) < 24:
        return f"{base}T{int(t.group(1)):02d}:{t.group(2)}:00"
    return base


def _fold(value: str) -> str:
    return unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
