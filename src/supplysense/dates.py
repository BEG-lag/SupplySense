"""Fechas en hora del centro de México.

Las fuentes mezclan formatos: CFE manda ``/Date(ms)/`` (UTC), PEMEX ISO en UTC y ComprasMX
``AAAA-MM-DD hh:mm:ss`` en hora local. Todo se guarda como texto ISO en hora local, sin zona,
porque así lo publican las dependencias y así se lee en el sitio.
"""

from __future__ import annotations

import re
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
