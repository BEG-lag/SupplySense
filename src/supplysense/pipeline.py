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


def update_comprasmx(
    client: PoliteClient,
    procs: dict[str, dict[str, Any]],
    contracts: dict[str, dict[str, Any]],
    today: date,
    year: int,
    kind: str,
    validators: dict[str, dict[str, str]],
    cache_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    name = comprasmx.FILES[kind].format(year=year)
    dest = cache_dir / name
    new_validators = client.download(comprasmx.url(kind, year), dest, validators.get(name))
    target = procs if kind == "expedientes" else contracts
    already = any(r["fuente"] == "comprasmx" and r.get("archivo") == year for r in target.values())
    if new_validators is None and already:
        log.info("%s sin cambios (304)", name)
        return procs, contracts
    if new_validators is not None and any(new_validators.values()):
        validators[name] = new_validators
    fresh = comprasmx.parse_file(dest, kind)
    for rec in fresh:
        rec["archivo"] = year
    scope = lambda r: r["fuente"] == "comprasmx" and r.get("archivo") == year  # noqa: E731
    if kind == "expedientes":
        return merge(procs, fresh, scope=scope, today=today), contracts
    return procs, merge(contracts, fresh, scope=scope, today=today)


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
    estado_path = root / "estado_fuentes.json"
    estado: dict[str, Any] = store.load_json(estado_path, {})
    validators: dict[str, dict[str, str]] = estado.setdefault("_validadores", {})
    if not years:
        # El año anterior casi no cambia: se relee los lunes o si aún no está guardado.
        have_previous = any(
            r["fuente"] == "comprasmx" and r.get("archivo") == today.year - 1
            for r in procs.values()
        )
        weekly = today.weekday() == 0 or not have_previous
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
                    result = report.run(
                        f"comprasmx:{kind}:{year}",
                        update_comprasmx,
                        client,
                        procs,
                        contracts,
                        today,
                        year,
                        kind,
                        validators,
                        cache_dir,
                    )
                    if result is not None:
                        procs, contracts = result
        if "fix" in sources:
            series = report.run("fix", fix.fetch, client)
            if series and store.save_json(root / "externos" / "fix.json", series):
                report.changed.append("externos/fix.json")
    finally:
        if own_client:
            client.close()

    report.changed += store.save("procedimientos", procs, root)
    report.changed += store.save("contratos", contracts, root)

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
    for fuente in ("cfe", "pemex", "comprasmx"):
        report.counts[fuente] = sum(1 for r in procs.values() if r["fuente"] == fuente)
        estado.setdefault(fuente, {})["registros"] = report.counts[fuente]
    estado.setdefault("comprasmx", {})["contratos"] = len(contracts)
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
