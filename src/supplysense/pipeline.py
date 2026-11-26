"""Actualización diaria: lee cada fuente, la une con lo guardado y escribe ``data/``.

Cada fuente corre aislada: si falla, se registra en ``data/estado_fuentes.json`` y lo que ya
estaba guardado queda intacto. Un freno evita sustituir datos buenos por una respuesta
recortada: si una fuente trae menos del 70% de los registros que ya teníamos, se rechaza.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from . import store
from .dates import day_of
from .http import FetchError, PoliteClient
from .sources import (
    banxico,
    campeche,
    cdmx,
    cfe,
    comprasmx,
    dof,
    fix,
    guanajuato,
    jalisco,
    nuevo_leon,
    oaj,
    pemex,
)

log = logging.getLogger(__name__)

CACHE_DIR = Path(".cache/raw")
# Fuentes guardadas en data/procedimientos (ComprasMX vive en la caché) y orden de lectura.
PORTAL_SOURCES = (
    "cfe",
    "pemex",
    "jalisco",
    "cdmx",
    "campeche",
    "guanajuato",
    "nuevo_leon",
    "banxico",
    "oaj",
    "dof",
)
SOURCES = ("cfe", "pemex", "comprasmx", *PORTAL_SOURCES[2:], "fix")
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


def upsert(
    procs: dict[str, dict[str, Any]],
    fresh: list[dict[str, Any]],
    today: date,
    keep: tuple[str, ...] = (),
) -> None:
    """Agrega o actualiza sin borrar: lo que sale de un listado estatal se conserva con su
    último estado (los portales estatales solo muestran lo vigente)."""
    for rec in fresh:
        prev = procs.get(rec["id"])
        if prev:
            for key in keep:
                if rec.get(key) in (None, "") and prev.get(key) not in (None, ""):
                    rec[key] = prev[key]
        rec["primera_vez"] = first_seen(prev, rec, today)
        procs[rec["id"]] = rec


STATE_KEEP = ("aclaraciones", "apertura", "fallo", "detalle_leido")


def update_jalisco(
    client: PoliteClient, procs: dict[str, dict[str, Any]], today: date, max_details: int = 120
) -> dict[str, dict[str, Any]]:
    fresh = jalisco.fetch_list(client)
    if not fresh:
        raise ValueError("Jalisco: el listado vino vacío")
    upsert(procs, fresh, today, STATE_KEEP)
    stale = (today - timedelta(days=7)).isoformat()
    pending = [
        procs[r["id"]]
        for r in fresh
        if r["estatus"] in ("abierta", "en_evaluacion")
        and (procs[r["id"]].get("detalle_leido") or "") < stale
    ]
    for rec in pending[:max_details]:
        rec.update(
            {k: v for k, v in jalisco.parse_detail(client.get_ok(rec["url"]).text).items() if v}
        )
        rec["detalle_leido"] = today.isoformat()
    return procs


def update_cdmx(
    client: PoliteClient, procs: dict[str, dict[str, Any]], today: date, backfill: int = 0
) -> dict[str, dict[str, Any]]:
    listed = cdmx.list_ids(client.get_ok(cdmx.LIST_URL).text)
    known = {r["fuente_id"] for r in procs.values() if r["fuente"] == "cdmx"}
    top = max([*known, *listed, 0])
    wanted = list(listed)  # las vigentes se releen: sus fechas pueden cambiar
    wanted += [n for n in range(max(1, top - backfill), top) if n not in known]
    misses, n = 0, top + 1
    while misses < 3 and n <= top + 60:  # ids consecutivos: avanzar hasta dejar de encontrar
        page = cdmx.fetch_detail(client, n)
        if page and (rec := cdmx.parse_detail(page, n)):
            upsert(procs, [rec], today, STATE_KEEP)
            misses = 0
        else:
            misses += 1
        n += 1
    for n in sorted(set(wanted)):
        page = cdmx.fetch_detail(client, n)
        if page and (rec := cdmx.parse_detail(page, n)):
            upsert(procs, [rec], today, STATE_KEEP)
    return procs


def update_campeche(
    client: PoliteClient, procs: dict[str, dict[str, Any]], today: date, max_new: int = 100
) -> dict[str, dict[str, Any]]:
    items = campeche.fetch_list(client)
    if not items:
        raise ValueError("Campeche: el listado vino vacío")
    known = {str(r["fuente_id"]) for r in procs.values() if r["fuente"] == "campeche"}
    new = sorted((i for i in items if i["id"] not in known), key=lambda i: -int(i["id"]))
    for item in new[:max_new]:
        text = campeche.pdf_text(campeche.fetch_pdf(client, item))
        rec = campeche.parse_text(text, item["id"], item["titulo"], item["href"])
        if rec:
            upsert(procs, [rec], today)
    return procs


NL_KEEP = (
    *STATE_KEEP,
    "estatus_fuente",
    "ganadores",
    "monto",
    "moneda",
    "precio_base",
    "participantes",
)


def update_nuevo_leon(
    client: PoliteClient, procs: dict[str, dict[str, Any]], today: date, backfill: int = 0
) -> dict[str, dict[str, Any]]:
    """Subastas: la lista completa cada día; el detalle (estatus, ganador, participantes) de las
    recientes que no han terminado, o de todas en la carga inicial."""
    fresh = nuevo_leon.fetch_list(client)
    if not fresh:
        raise ValueError("Nuevo León: el listado de subastas vino vacío")
    upsert(procs, fresh, today, NL_KEEP)
    recent = (today - timedelta(days=45)).isoformat()
    for rec in (procs[r["id"]] for r in fresh):
        done = rec.get("ganadores") or rec.get("estatus_fuente", "").lower().startswith("cerr")
        if (backfill and not rec.get("detalle_leido")) or (
            not done and (rec.get("apertura") or "") >= recent
        ):
            rec.update(nuevo_leon.fetch_detail(client, rec["fuente_id"]))
            rec["detalle_leido"] = today.isoformat()
        rec["estatus"] = nuevo_leon.status(rec)
    return procs


GTO_KEEP = (*STATE_KEEP, "registro", "ley", "recursos")


def update_guanajuato(
    client: PoliteClient,
    procs: dict[str, dict[str, Any]],
    today: date,
    backfill: int = 0,
    max_pdfs: int = 30,
) -> dict[str, dict[str, Any]]:
    """Lista JSON (la página más reciente; todo el histórico en la carga inicial) y fechas de la
    convocatoria de las que siguen sin acta de apertura ni fallo."""
    fresh = guanajuato.fetch_list(client, pages=8 if backfill else 1)
    if not fresh:
        raise ValueError("Guanajuato: el listado vino vacío")
    upsert(procs, fresh, today, GTO_KEEP)
    recent = (today - timedelta(days=45)).isoformat()
    pending = [
        procs[r["id"]]
        for r in fresh
        if r["estatus"] == "abierta"
        and (r.get("publicado") or "") >= recent
        and not procs[r["id"]].get("detalle_leido")
    ]
    for rec in pending[:max_pdfs]:
        rec["detalle_leido"] = today.isoformat()
        try:
            data = guanajuato.fetch_convocatoria(client, rec)
        except FetchError:
            continue
        if data:
            rec.update(guanajuato.parse_text(guanajuato.pdf_text(data)))
    # Con recursos federales el procedimiento también está en ComprasMX.
    for key in [
        k
        for k, r in procs.items()
        if r["fuente"] == "guanajuato" and r.get("recursos") == "Federal"
    ]:
        del procs[key]
    return procs


def update_banxico(
    client: PoliteClient, procs: dict[str, dict[str, Any]], today: date
) -> dict[str, dict[str, Any]]:
    fresh = banxico.fetch_list(client)
    if not fresh:
        raise ValueError("Banxico: el listado vino vacío")
    upsert(procs, fresh, today, STATE_KEEP)
    stale = (today - timedelta(days=3)).isoformat()
    for rec in (procs[r["id"]] for r in fresh if r["estatus"] in ("abierta", "en_evaluacion")):
        if (rec.get("detalle_leido") or "") < stale:
            rec.update(banxico.fetch_stages(client, rec["fuente_id"]))
            rec["detalle_leido"] = today.isoformat()
    return procs


def update_oaj(
    client: PoliteClient, procs: dict[str, dict[str, Any]], today: date, backfill: int = 0
) -> dict[str, dict[str, Any]]:
    first = 2018 if backfill else today.year - 1
    fresh = oaj.fetch_list(client, tuple(range(first, today.year + 2)))
    if not fresh:
        raise ValueError("OAJ: el listado vino vacío")
    upsert(procs, fresh, today, STATE_KEEP)
    return procs


def update_dof(
    client: PoliteClient, procs: dict[str, dict[str, Any]], today: date, backfill: int = 0
) -> dict[str, dict[str, Any]]:
    """Resúmenes de convocatoria de los últimos días (o ``backfill`` días hacia atrás)."""
    known = {r["fuente_id"] for r in procs.values() if r["fuente"] == "dof"}
    for day in dof.days_back(today, max(3, backfill)):
        upsert(procs, dof.fetch_day(client, day, known), today, STATE_KEEP)
    return procs


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
    sources: tuple[str, ...] = SOURCES,
    years: tuple[int, ...] | None = None,
    max_details: int = 150,
    backfill: int = 0,
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
        for name, func, extra in (
            ("jalisco", update_jalisco, {}),
            ("cdmx", update_cdmx, {"backfill": backfill}),
            ("campeche", update_campeche, {"max_new": max(100, backfill)}),
            ("guanajuato", update_guanajuato, {"backfill": backfill}),
            ("nuevo_leon", update_nuevo_leon, {"backfill": backfill}),
            ("banxico", update_banxico, {}),
            ("oaj", update_oaj, {"backfill": backfill}),
            ("dof", update_dof, {"backfill": backfill}),
        ):
            if name in sources:
                result = report.run(name, func, client, procs, today, **extra)
                if result is not None:
                    procs = result
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
    for fuente in PORTAL_SOURCES:
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
