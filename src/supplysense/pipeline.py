"""Actualización diaria: lee cada fuente, la une con lo guardado y escribe ``data/``.

Cada fuente corre aislada: si falla, se registra en ``data/estado_fuentes.json`` y lo que ya
estaba guardado queda intacto. Un freno evita sustituir datos buenos por una respuesta
recortada: si una fuente trae menos del 70% de los registros que ya teníamos, se rechaza.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from . import store
from .dates import day_of
from .http import FetchError, PoliteClient
from .sources import cfe, comprasmx, fix, pemex

log = logging.getLogger(__name__)

CACHE_DIR = Path(".cache/raw")
MIN_RATIO = 0.7
# Campos que solo trae el detalle de CFE: si la lista no los trae, se conservan.
KEEP_FROM_PREVIOUS = (
    "empresa",
    "unidad",
    "apertura",
    "apertura_economica",
    "fallo",
    "detalle_leido",
)


@dataclass
class Report:
    ok: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    changed: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def run(self, name: str, func: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            result = func(*args, **kwargs)
        except (FetchError, ValueError, KeyError) as exc:
            log.warning("%s falló: %s", name, exc)
            self.failed[name] = str(exc)[:300]
            return None
        except Exception as exc:  # las pilas de red lanzan muchos tipos; nunca abortar la corrida
            log.warning("%s falló inesperadamente: %r", name, exc)
            self.failed[name] = repr(exc)[:300]
            return None
        self.ok.append(name)
        return result


def first_seen(prev: dict[str, Any] | None, rec: dict[str, Any], today: date) -> str:
    if prev and prev.get("primera_vez"):
        return prev["primera_vez"]
    published = day_of(rec.get("publicado"))
    return min(published, today.isoformat()) if published else today.isoformat()


def merge(
    stored: dict[str, dict[str, Any]],
    fresh: list[dict[str, Any]],
    *,
    scope: Any,
    today: date,
    keep: tuple[str, ...] = (),
) -> dict[str, dict[str, Any]]:
    """Sustituye los registros guardados que cumplen ``scope`` por ``fresh``, conservando
    ``primera_vez`` y los campos de ``keep`` cuando la versión nueva no los trae."""
    previous = {k: v for k, v in stored.items() if scope(v)}
    old_n, new_n = len(previous), len(fresh)
    if old_n >= 50 and new_n < old_n * MIN_RATIO:
        raise ValueError(f"freno: llegaron {new_n} registros y había {old_n}")
    result = {k: v for k, v in stored.items() if not scope(v)}
    for rec in fresh:
        prev = previous.get(rec["id"])
        if prev:
            for key in keep:
                if rec.get(key) in (None, "") and prev.get(key) not in (None, ""):
                    rec[key] = prev[key]
        rec["primera_vez"] = first_seen(prev, rec, today)
        result[rec["id"]] = rec
    return result


def update_cfe(
    client: PoliteClient, procs: dict[str, dict[str, Any]], today: date, max_details: int
) -> dict[str, dict[str, Any]]:
    session = cfe.Session(client)
    fresh = cfe.parse_list(session.search())
    merged = merge(
        procs, fresh, scope=lambda r: r["fuente"] == "cfe", today=today, keep=KEEP_FROM_PREVIOUS
    )
    pending = [
        r
        for r in merged.values()
        if r["fuente"] == "cfe" and r.get("estatus") == "abierta" and not r.get("detalle_leido")
    ]
    pending.sort(key=lambda r: r.get("publicado") or "", reverse=True)
    for rec in pending[:max_details]:
        try:
            detail = cfe.parse_detail(session.detail(rec["fuente_id"]))
        except FetchError as exc:
            log.warning("CFE detalle %s: %s", rec["numero"], exc)
            continue
        for key, value in detail.items():
            if value:
                rec[key] = value
        rec["detalle_leido"] = today.isoformat()
    return merged


def update_pemex(
    client: PoliteClient, procs: dict[str, dict[str, Any]], today: date
) -> dict[str, dict[str, Any]]:
    return merge(procs, pemex.fetch(client), scope=lambda r: r["fuente"] == "pemex", today=today)


def raw_path(cache_dir: Path, kind: str, year: int) -> Path:
    return cache_dir / comprasmx.FILES[kind].format(year=year)


def update_comprasmx(
    client: PoliteClient,
    seen: dict[str, str],
    counts: dict[str, int],
    today: date,
    year: int,
    kind: str,
    cache_dir: Path,
) -> int:
    """Baja el archivo del año, lo valida (columnas y volumen) y solo entonces sustituye al
    anterior en la caché. Registra en ``seen`` los ids que no habíamos visto."""
    dest = raw_path(cache_dir, kind, year)
    tmp = dest.with_name(dest.name + ".nuevo")
    client.download(comprasmx.url(kind, year), tmp)
    try:
        records = comprasmx.parse_file(tmp, kind)
        previous = counts.get(dest.name, 0)
        if previous >= 1000 and len(records) < previous * MIN_RATIO:
            raise ValueError(f"freno: {dest.name} trae {len(records)} registros y había {previous}")
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(dest)
    for rec in records:
        if rec["id"] not in seen:
            seen[rec["id"]] = first_seen(None, rec, today)
    counts[dest.name] = len(records)
    return len(records)


def ensure_raw(client: PoliteClient, today: date, cache_dir: Path) -> list[str]:
    """Descarga los archivos de ComprasMX que falten en la caché (para el build)."""
    got = []
    for year in (today.year - 1, today.year):
        for kind in ("expedientes", "contratos"):
            dest = raw_path(cache_dir, kind, year)
            if not dest.exists():
                client.download(comprasmx.url(kind, year), dest)
                got.append(dest.name)
    return got


def update(
    today: date,
    *,
    root: Path = store.DATA_DIR,
    cache_dir: Path = CACHE_DIR,
    client: PoliteClient | None = None,
    sources: tuple[str, ...] = ("cfe", "pemex", "comprasmx", "fix"),
    years: tuple[int, ...] | None = None,
    max_details: int = 150,
) -> Report:
    report = Report()
    own_client = client is None
    client = client or PoliteClient()
    procs = store.load("procedimientos", root)
    contracts = store.load("contratos", root)
    seen = store.load_seen(root)
    # Migración: ComprasMX ya no se guarda completo; se conserva su primera_vez en "vistos".
    for collection in (procs, contracts):
        for key in [k for k, r in collection.items() if r["fuente"] == "comprasmx"]:
            seen.setdefault(key, collection.pop(key).get("primera_vez") or today.isoformat())
    estado_path = root / "estado_fuentes.json"
    estado: dict[str, Any] = store.load_json(estado_path, {})
    estado.pop("_validadores", None)
    cmx_state = estado.setdefault("comprasmx", {})
    counts: dict[str, int] = cmx_state.setdefault("archivos", {})
    if not years:
        # El año anterior casi no cambia: se relee los lunes o si falta en la caché.
        previous_cached = all(
            raw_path(cache_dir, kind, today.year - 1).exists()
            for kind in ("expedientes", "contratos")
        )
        weekly = today.weekday() == 0 or not previous_cached
        years = (today.year - 1, today.year) if weekly else (today.year,)
    try:
        if "cfe" in sources:
            result = report.run("cfe", update_cfe, client, procs, today, max_details)
            if result is not None:
                procs = result
        if "pemex" in sources:
            result = report.run("pemex", update_pemex, client, procs, today)
            if result is not None:
                procs = result
        if "comprasmx" in sources:
            for year in years:
                for kind in ("expedientes", "contratos"):
                    report.run(
                        f"comprasmx:{kind}:{year}",
                        update_comprasmx,
                        client,
                        seen,
                        counts,
                        today,
                        year,
                        kind,
                        cache_dir,
                    )
        if "fix" in sources:
            series = report.run("fix", fix.fetch, client)
            if series and store.save_json(root / "externos" / "fix.json", series):
                report.changed.append("externos/fix.json")
    finally:
        if own_client:
            client.close()

    report.changed += store.save("procedimientos", procs, root)
    report.changed += store.save("contratos", contracts, root)
    report.changed += store.save_seen(seen, root)

    for name in {n.split(":")[0] for n in (*report.ok, *report.failed)}:
        entry = estado.setdefault(name, {})
        errors = {k: v for k, v in report.failed.items() if k.split(":")[0] == name}
        if errors:
            entry.setdefault("falla_desde", today.isoformat())
            entry["error"] = "; ".join(f"{k}: {v}" for k, v in errors.items())[:500]
        else:
            entry.pop("falla_desde", None)
            entry.pop("error", None)
            entry["ultima_ok"] = today.isoformat()
    for fuente in ("cfe", "pemex"):
        report.counts[fuente] = sum(1 for r in procs.values() if r["fuente"] == fuente)
        estado.setdefault(fuente, {})["registros"] = report.counts[fuente]
    report.counts["comprasmx"] = sum(counts.values())
    cmx_state.pop("registros", None)
    cmx_state.pop("contratos", None)
    if store.save_json(estado_path, estado):
        report.changed.append("estado_fuentes.json")
    return report


def stale_sources(root: Path, today: date, days: int = 3) -> list[str]:
    """Fuentes que llevan ``days`` días o más fallando (para que el workflow avise)."""
    estado = store.load_json(root / "estado_fuentes.json", {})
    out = []
    for name, entry in estado.items():
        since = entry.get("falla_desde") if isinstance(entry, dict) else None
        if since and (today - date.fromisoformat(since)).days >= days:
            out.append(name)
    return out
