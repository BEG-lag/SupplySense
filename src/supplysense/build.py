"""Del almacén ``data/`` a los archivos que lee el sitio (``web/public/data``).

* Las reglas (alcance, categorías, correcciones) se aplican aquí, no al descargar: cambiar una
  regla no exige volver a bajar nada.
* Los agregados de precios se calculan con DuckDB (percentiles por categoría, año, comprador).
* Todo es determinista: mismo ``data/`` y misma fecha producen los mismos archivos.

Salida:
  meta.json                 totales, fuentes, catálogos
  abiertas.json             convocatorias abiertas (filas completas para la tabla)
  indice/AAAA.json          índice compacto de búsqueda por año de publicación
  detalle/xx.json           registro completo por id, en 256 fragmentos
  precios.json              resumen por categoría
  precios/<categoria>.json  percentiles, serie anual, ganadores y adjudicaciones recientes
  ganadores.json            adjudicaciones recientes y empresas con más contratos
  empresas.json             índice de empresas; empresas/xx.json, su detalle
  compradores.json          compradores con su resumen
  feed.xml, feeds/*.xml     Atom con las convocatorias nuevas
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb

from . import feeds, rules, store
from .dates import day_of
from .sources import pemex
from .text import company_key, fold, slug

MIN_AMOUNT = 10_000
RECENT_MONTHS = 36
INDEX_FIELDS = (
    "id",
    "numero",
    "titulo",
    "fuente",
    "comprador_id",
    "entidad",
    "categoria",
    "estatus",
    "publicado",
    "apertura",
    "monto",
    "ganador",
    "primera_vez",
    "estatus_estimado",
)
STATUS_LABELS = {
    "abierta": "Abierta",
    "en_evaluacion": "En evaluación",
    "adjudicada": "Adjudicada",
    "desierta": "Desierta",
    "cancelada": "Cancelada",
    "suspendida": "Suspendida",
    "concluida": "Concluida",
    "aviso": "Aviso publicado",
    "otro": "Otro",
}
SOURCE_LABELS = {"cfe": "CFE", "pemex": "PEMEX", "comprasmx": "ComprasMX"}
_WORD = re.compile(r"[a-z0-9]{4,}")
_STOP = {
    "para",
    "servicio",
    "servicios",
    "suministro",
    "adquisicion",
    "contratacion",
    "diversos",
    "diversas",
    "material",
    "materiales",
    "equipo",
    "equipos",
    "conforme",
    "anexo",
    "tecnico",
    "partida",
    "partidas",
    "general",
    "trabajos",
    "entre",
    "otros",
    "sobre",
    "segun",
    "durante",
}


# Nombres de estado unificados entre fuentes ("VERACRUZ" y "Veracruz de Ignacio de la Llave"
# son el mismo filtro). "México" en ComprasMX y CFE es el Estado de México.
STATES = {
    fold(name): name
    for name in (
        "Aguascalientes",
        "Baja California",
        "Baja California Sur",
        "Campeche",
        "Chiapas",
        "Chihuahua",
        "Ciudad de México",
        "Coahuila",
        "Colima",
        "Durango",
        "Estado de México",
        "Guanajuato",
        "Guerrero",
        "Hidalgo",
        "Jalisco",
        "Michoacán",
        "Morelos",
        "Nayarit",
        "Nuevo León",
        "Oaxaca",
        "Puebla",
        "Querétaro",
        "Quintana Roo",
        "San Luis Potosí",
        "Sinaloa",
        "Sonora",
        "Tabasco",
        "Tamaulipas",
        "Tlaxcala",
        "Veracruz",
        "Yucatán",
        "Zacatecas",
    )
}
STATE_ALIASES = {
    "mexico": "Estado de México",
    "coahuila de zaragoza": "Coahuila",
    "michoacan de ocampo": "Michoacán",
    "veracruz de ignacio de la llave": "Veracruz",
    "distrito federal": "Ciudad de México",
    "cdmx": "Ciudad de México",
}


def state_name(value: str | None) -> str | None:
    if not value:
        return None
    key = re.sub(r"\s+", " ", fold(value)).strip()
    return STATE_ALIASES.get(key) or STATES.get(key) or value.strip().title()


# ── utilidades ────────────────────────────────────────────────────────────────


def shard(key: str) -> str:
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:2]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def fx_rate(fix: dict[str, float], day: str | None) -> float | None:
    if not fix:
        return None
    if day:
        for back in range(0, 15):
            key = (date.fromisoformat(day[:10]) - timedelta(days=back)).isoformat()
            if key in fix:
                return fix[key]
    return fix[max(fix)]


def tokens(text: str | None) -> set[str]:
    return {w for w in _WORD.findall(fold(text)) if w not in _STOP}


def apply_corrections(records: dict[str, dict[str, Any]]) -> list[str]:
    """Aplica ``reglas/correcciones.csv``; devuelve las que ya no coinciden con la fuente."""
    stale = []
    for corr in rules.corrections():
        rec = records.get(corr.id)
        if rec is None:
            continue
        if str(rec.get(corr.campo)) != corr.valor_original:
            stale.append(corr.id)
            continue
        value: Any = corr.valor_corregido
        if isinstance(rec.get(corr.campo), float):
            value = float(value)
        rec[corr.campo] = value
        rec.setdefault("correcciones", []).append(
            {"campo": corr.campo, "original": corr.valor_original, "motivo": corr.motivo}
        )
    return stale


# ── normalización final de registros ─────────────────────────────────────────


def cfe_companies(procs: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Clave de empresa de CFE (``CFE-0100-...``) → nombre, aprendida de los detalles."""
    seen: dict[str, Counter[str]] = defaultdict(Counter)
    for rec in procs.values():
        if rec["fuente"] == "cfe" and rec.get("empresa"):
            code = rec["numero"].split("-")[1] if rec["numero"].count("-") >= 2 else None
            if code:
                seen[code][rec["empresa"]] += 1
    return {code: names.most_common(1)[0][0] for code, names in seen.items()}


def buyer_of(rec: dict[str, Any], cfe_names: dict[str, str]) -> tuple[str, str]:
    """(id, nombre) del comprador para agrupar y mostrar."""
    if rec["fuente"] == "cfe":
        code = rec["numero"].split("-")[1] if rec["numero"].count("-") >= 2 else ""
        name = rec.get("empresa") or cfe_names.get(code) or "CFE"
        name = re.sub(r"\s+-\s+", " ", name)
        if not name.upper().startswith("CFE"):
            name = f"CFE {name}"
        return slug(name), name
    if rec["fuente"] == "pemex":
        name = f"PEMEX {rec.get('segmento', '')}".strip()
        return slug(name), name
    siglas = rec.get("siglas") or ""
    buyer = rules.match_buyer(rec.get("comprador"), siglas)
    if buyer:
        return slug(buyer.siglas), buyer.nombre
    name = rec.get("comprador") or siglas or "Sin comprador"
    return slug(siglas or name), name


def final_status(rec: dict[str, Any], today: date) -> tuple[str, bool]:
    """Estatus para el sitio y si es estimado. PEMEX no publica estatus: un aviso se trata
    como abierto ``pemex.OPEN_DAYS`` días tras su publicación. Una convocatoria abierta cuya
    apertura de propuestas ya pasó se muestra en evaluación."""
    if rec["fuente"] == "pemex":
        published = day_of(rec.get("publicado"))
        if published and (today - date.fromisoformat(published)).days <= pemex.OPEN_DAYS:
            return "abierta", True
        return "aviso", True
    status = rec.get("estatus") or "otro"
    if status == "abierta" and rec.get("apertura") and rec["apertura"][:10] < today.isoformat():
        return "en_evaluacion", True
    return status, False


# ── construcción ─────────────────────────────────────────────────────────────


def prepare(root: Path, today: date) -> dict[str, Any]:
    procs = store.load("procedimientos", root)
    contracts = store.load("contratos", root)
    stale = apply_corrections(procs) + apply_corrections(contracts)

    # Alcance y categorías con las reglas vigentes.
    for collection in (procs, contracts):
        for key in list(collection):
            rec = collection[key]
            text = f"{rec.get('titulo') or ''} {rec.get('descripcion') or ''}"
            if rec["fuente"] == "comprasmx":
                motivo = rules.scope_reason(rec.get("comprador"), rec.get("siglas"), text)
                if not motivo:
                    del collection[key]
                    continue
                rec["motivo_alcance"] = motivo
            rec["categoria"] = rules.categorize(text, rec.get("tipo_contratacion"))

    for collection in (procs, contracts):
        for rec in collection.values():
            rec["entidad"] = state_name(rec.get("entidad"))

    cfe_names = cfe_companies(procs)
    buyers: dict[str, str] = {}
    for collection in (procs, contracts):
        for rec in collection.values():
            bid, bname = buyer_of(rec, cfe_names)
            rec["comprador_id"], rec["comprador_nombre"] = bid, bname
            buyers.setdefault(bid, bname)
    for rec in procs.values():
        rec["estatus"], rec["estatus_estimado"] = final_status(rec, today)

    fix = {k: float(v) for k, v in store.load_json(root / "externos" / "fix.json", {}).items()}
    awards = build_awards(procs, contracts, fix)
    return {
        "procs": procs,
        "contracts": contracts,
        "awards": awards,
        "buyers": buyers,
        "fix": fix,
        "stale_corrections": stale,
        "estado": store.load_json(root / "estado_fuentes.json", {}),
    }


def build_awards(
    procs: dict[str, dict[str, Any]], contracts: dict[str, dict[str, Any]], fix: dict[str, float]
) -> list[dict[str, Any]]:
    """Adjudicaciones con monto en pesos: procedimientos adjudicados de CFE (un monto por
    procedimiento) y contratos de ComprasMX (un monto por contrato, en dólares → FIX)."""
    awards: list[dict[str, Any]] = []
    for rec in procs.values():
        if rec["fuente"] != "cfe" or rec.get("estatus") != "adjudicada" or not rec.get("monto"):
            continue
        awards.append(
            {
                "id": rec["id"],
                "procedimiento_id": rec["id"],
                "fuente": "cfe",
                "titulo": rec["titulo"],
                "numero": rec["numero"],
                "categoria": rec["categoria"],
                "comprador_id": rec["comprador_id"],
                "entidad": rec.get("entidad"),
                "tipo_contratacion": rec.get("tipo_contratacion"),
                "tipo_procedimiento": rec.get("tipo_procedimiento"),
                "fecha": day_of(rec.get("fallo") or rec.get("publicado")),
                "monto_mxn": rec["monto"],
                "moneda": "MXN",
                "ganadores": rec.get("ganadores") or [],
            }
        )
    for rec in contracts.values():
        if not rec.get("monto"):
            continue
        fecha = day_of(rec.get("firma") or rec.get("fallo") or rec.get("publicado"))
        moneda = (rec.get("moneda") or "MXN").upper()
        if moneda == "MXN":
            mxn = rec["monto"]
        elif moneda == "USD" and (rate := fx_rate(fix, fecha)):
            mxn = round(rec["monto"] * rate, 2)
        else:
            continue
        awards.append(
            {
                "id": rec["id"],
                "procedimiento_id": rec.get("procedimiento_id"),
                "fuente": "comprasmx",
                "titulo": rec["titulo"],
                "numero": rec.get("numero_contrato") or rec.get("numero_procedimiento"),
                "categoria": rec["categoria"],
                "comprador_id": rec["comprador_id"],
                "entidad": rec.get("entidad"),
                "tipo_contratacion": rec.get("tipo_contratacion"),
                "tipo_procedimiento": rec.get("tipo_procedimiento"),
                "fecha": fecha,
                "monto_mxn": mxn,
                "moneda": moneda,
                "monto_original": rec["monto"],
                "ganadores": [rec["proveedor"]] if rec.get("proveedor") else [],
                "proveedor_rfc": rec.get("proveedor_rfc"),
            }
        )
    # Montos atípicos: arriba del P99 de su categoría o debajo del mínimo útil.
    by_cat: dict[str, list[float]] = defaultdict(list)
    for a in awards:
        by_cat[a["categoria"]].append(a["monto_mxn"])
    p99 = {}
    for cat, values in by_cat.items():
        values.sort()
        p99[cat] = values[min(len(values) - 1, math.floor(0.99 * len(values)))]
    for a in awards:
        a["atipico"] = a["monto_mxn"] < MIN_AMOUNT or a["monto_mxn"] > p99[a["categoria"]]
        a["empresas"] = [k for k in (company_key(g) for g in a["ganadores"]) if k]
    awards.sort(key=lambda a: (a["fecha"] or "", a["id"]), reverse=True)
    return awards


def price_tables(awards: list[dict[str, Any]], today: date, cache: Path) -> dict[str, Any]:
    """Percentiles por categoría (recientes), serie anual y por tipo, con DuckDB."""
    cache.mkdir(parents=True, exist_ok=True)
    rows = cache / "adjudicaciones.jsonl"
    with rows.open("w", encoding="utf-8") as fh:
        for a in awards:
            if not a["atipico"] and a["fecha"]:
                fh.write(
                    json.dumps(
                        {
                            "categoria": a["categoria"],
                            "fecha": a["fecha"],
                            "monto": a["monto_mxn"],
                            "tipo": a.get("tipo_contratacion") or "Sin dato",
                            "comprador": a["comprador_id"],
                            "fuente": a["fuente"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    since = (today.replace(day=1) - timedelta(days=RECENT_MONTHS * 30)).isoformat()
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE adj AS SELECT categoria, CAST(fecha AS DATE) AS fecha,"
        " monto::DOUBLE AS monto, tipo, comprador, fuente"
        " FROM read_json(?, format='newline_delimited',"
        " columns={categoria:'VARCHAR', fecha:'VARCHAR', monto:'DOUBLE', tipo:'VARCHAR',"
        " comprador:'VARCHAR', fuente:'VARCHAR'})",
        [str(rows)],
    )
    qs = [round(x / 100, 2) for x in range(5, 100, 5)]
    recent = con.execute(
        "SELECT categoria, count(*), quantile_cont(monto, ?), avg(monto), min(fecha), max(fecha)"
        " FROM adj WHERE fecha >= ? GROUP BY 1",
        [qs, since],
    ).fetchall()
    yearly = con.execute(
        "SELECT categoria, year(fecha) AS anio, count(*),"
        " quantile_cont(monto, [0.25, 0.5, 0.75]) FROM adj GROUP BY 1, 2 ORDER BY 1, 2"
    ).fetchall()
    by_type = con.execute(
        "SELECT categoria, tipo, count(*), quantile_cont(monto, [0.25, 0.5, 0.75])"
        " FROM adj WHERE fecha >= ? GROUP BY 1, 2 HAVING count(*) >= 10 ORDER BY 1, 3 DESC",
        [since],
    ).fetchall()
    con.close()
    out: dict[str, Any] = defaultdict(lambda: {"anual": [], "por_tipo": []})
    for cat, n, qvals, mean, first, last in recent:
        out[cat].update(
            {
                "n": n,
                "percentiles": {
                    str(int(q * 100)): round(v, 2) for q, v in zip(qs, qvals, strict=True)
                },
                "promedio": round(mean, 2),
                "desde": str(first),
                "hasta": str(last),
            }
        )
    for cat, anio, n, q in yearly:
        out[cat]["anual"].append(
            {
                "anio": anio,
                "n": n,
                "p25": round(q[0], 2),
                "p50": round(q[1], 2),
                "p75": round(q[2], 2),
            }
        )
    for cat, tipo, n, q in by_type:
        out[cat]["por_tipo"].append(
            {
                "tipo": tipo,
                "n": n,
                "p25": round(q[0], 2),
                "p50": round(q[1], 2),
                "p75": round(q[2], 2),
            }
        )
    return dict(out)


def hhi(shares: list[float]) -> int:
    total = sum(shares)
    return round(sum((s / total * 100) ** 2 for s in shares)) if total else 0


def similar_awards(
    procs: dict[str, dict[str, Any]], awards: list[dict[str, Any]], today: date
) -> dict[str, list[dict[str, Any]]]:
    """Para cada convocatoria abierta, hasta 5 adjudicaciones parecidas de los últimos 5 años
    (misma categoría y palabras en común, ponderadas por rareza)."""
    since = (today - timedelta(days=5 * 365)).isoformat()
    pool = [a for a in awards if (a["fecha"] or "") >= since and not a["atipico"]]
    postings: dict[str, list[int]] = defaultdict(list)
    for i, a in enumerate(pool):
        for t in tokens(a["titulo"]):
            postings[t].append(i)
    n = len(pool) or 1
    idf = {t: math.log(n / len(ids)) for t, ids in postings.items() if len(ids) <= 4000}
    result: dict[str, list[dict[str, Any]]] = {}
    for rec in procs.values():
        if rec["estatus"] not in ("abierta", "en_evaluacion"):
            continue
        scores: Counter[int] = Counter()
        for t in tokens(rec["titulo"]):
            weight = idf.get(t)
            if weight:
                for i in postings[t]:
                    scores[i] += weight
        best = []
        for i, score in scores.most_common(60):
            a = pool[i]
            if a["procedimiento_id"] == rec["id"]:
                continue
            bonus = 1.5 if a["categoria"] == rec["categoria"] else 1.0
            best.append((score * bonus, i))
        best.sort(reverse=True)
        if best and best[0][0] >= 4:
            result[rec["id"]] = [
                {
                    k: pool[i][k]
                    for k in (
                        "id",
                        "procedimiento_id",
                        "titulo",
                        "fecha",
                        "monto_mxn",
                        "ganadores",
                        "comprador_id",
                        "fuente",
                    )
                }
                for score, i in best[:5]
                if score >= 3
            ]
    return result


def compact_row(rec: dict[str, Any]) -> list[Any]:
    return [
        rec["id"],
        rec.get("numero"),
        (rec.get("titulo") or "")[:160],
        rec["fuente"],
        rec["comprador_id"],
        rec.get("entidad"),
        rec["categoria"],
        rec["estatus"],
        day_of(rec.get("publicado")),
        day_of(rec.get("apertura")),
        rec.get("monto"),
        (rec.get("ganadores") or [None])[0],
        rec.get("primera_vez"),
        1 if rec.get("estatus_estimado") else 0,
    ]


PUBLIC_DROP = {"archivo", "detalle_leido", "fuente_id"}


def public_record(rec: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in rec.items() if k not in PUBLIC_DROP and v not in (None, "", [], {})}
    if rec.get("ganadores"):
        out["ganadores_ids"] = [company_key(g) for g in rec["ganadores"]]
    if rec.get("proveedor"):
        out["proveedor_id"] = company_key(rec["proveedor"])
    return out


def build_site(
    root: Path, out: Path, *, today: date, cache_dir: Path = Path(".cache/build")
) -> dict[str, Any]:
    data = prepare(root, today)
    procs, contracts, awards = data["procs"], data["contracts"], data["awards"]
    buyers, estado = data["buyers"], data["estado"]
    names = rules.category_names()

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # Abiertas y similares.
    similar = similar_awards(procs, awards, today)
    open_recs = sorted(
        (r for r in procs.values() if r["estatus"] == "abierta"),
        key=lambda r: (r.get("publicado") or "", r["id"]),
        reverse=True,
    )
    write_json(out / "abiertas.json", [compact_row(r) for r in open_recs])

    # Índice por año.
    by_year: dict[str, list[list[Any]]] = defaultdict(list)
    for rec in sorted(
        procs.values(), key=lambda r: (r.get("publicado") or "", r["id"]), reverse=True
    ):
        by_year[(rec.get("publicado") or "0000")[:4]].append(compact_row(rec))
    for year, rows in by_year.items():
        write_json(out / "indice" / f"{year}.json", rows)

    # Detalle por fragmentos (procedimientos y contratos).
    contracts_by_proc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in contracts.values():
        if c.get("procedimiento_id"):
            contracts_by_proc[c["procedimiento_id"]].append(public_record(c))
    shards: dict[str, dict[str, Any]] = defaultdict(dict)
    for rec in procs.values():
        item = public_record(rec)
        item["tipo"] = "procedimiento"
        if rec["id"] in similar:
            item["similares"] = similar[rec["id"]]
        if rec["id"] in contracts_by_proc:
            item["contratos"] = sorted(contracts_by_proc[rec["id"]], key=lambda c: c["id"])
        shards[shard(rec["id"])][rec["id"]] = item
    for c in contracts.values():
        item = public_record(c)
        item["tipo"] = "contrato"
        shards[shard(c["id"])][c["id"]] = item
    for key, items in shards.items():
        write_json(out / "detalle" / f"{key}.json", items)

    # Precios.
    tables = price_tables(awards, today, cache_dir)
    awards_by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in awards:
        awards_by_cat[a["categoria"]].append(a)
    resumen = []
    since_recent = (today - timedelta(days=RECENT_MONTHS * 30)).isoformat()
    for cat, table in sorted(tables.items()):
        if "n" not in table:
            continue
        cat_awards = [a for a in awards_by_cat[cat] if not a["atipico"]]
        recent = [a for a in cat_awards if (a["fecha"] or "") >= since_recent]
        winners: Counter[str] = Counter()
        winner_names: dict[str, str] = {}
        for a in recent:
            for key, name in zip(a["empresas"], a["ganadores"], strict=False):
                winners[key] += a["monto_mxn"] / max(len(a["empresas"]), 1)
                winner_names.setdefault(key, name)
        top = [
            {"id": k, "nombre": winner_names[k], "monto": round(v, 2)}
            for k, v in winners.most_common(15)
        ]
        detail = {
            "codigo": cat,
            "nombre": names.get(cat, cat),
            **table,
            "concentracion_hhi": hhi(list(winners.values())),
            "ganadores": top,
            "recientes": [
                {
                    k: a[k]
                    for k in (
                        "id",
                        "procedimiento_id",
                        "titulo",
                        "fecha",
                        "monto_mxn",
                        "ganadores",
                        "comprador_id",
                        "fuente",
                    )
                }
                for a in cat_awards[:60]
            ],
        }
        write_json(out / "precios" / f"{cat}.json", detail)
        resumen.append(
            {
                "codigo": cat,
                "nombre": names.get(cat, cat),
                "n": table["n"],
                "p25": table["percentiles"]["25"],
                "p50": table["percentiles"]["50"],
                "p75": table["percentiles"]["75"],
            }
        )
    write_json(out / "precios.json", resumen)

    # Empresas.
    companies: dict[str, dict[str, Any]] = {}
    for a in awards:
        share = a["monto_mxn"] / max(len(a["empresas"]), 1)
        for key, name in zip(a["empresas"], a["ganadores"], strict=False):
            c = companies.setdefault(
                key,
                {
                    "id": key,
                    "nombres": Counter(),
                    "n": 0,
                    "monto": 0.0,
                    "categorias": Counter(),
                    "compradores": Counter(),
                    "adjudicaciones": [],
                    "rfc": None,
                },
            )
            c["nombres"][name] += 1
            c["n"] += 1
            c["monto"] += share
            c["categorias"][a["categoria"]] += 1
            c["compradores"][a["comprador_id"]] += 1
            if a.get("proveedor_rfc"):
                c["rfc"] = a["proveedor_rfc"]
            if len(c["adjudicaciones"]) < 40:
                c["adjudicaciones"].append(
                    {
                        k: a[k]
                        for k in (
                            "id",
                            "procedimiento_id",
                            "titulo",
                            "fecha",
                            "monto_mxn",
                            "comprador_id",
                            "fuente",
                            "categoria",
                        )
                    }
                    | {"compartida": len(a["empresas"]) > 1}
                )
    company_index = []
    company_shards: dict[str, dict[str, Any]] = defaultdict(dict)
    for key, c in companies.items():
        nombre = c["nombres"].most_common(1)[0][0]
        fechas = [x["fecha"] for x in c["adjudicaciones"] if x["fecha"]]
        company_index.append(
            [
                key,
                nombre,
                c["n"],
                round(c["monto"], 2),
                c["categorias"].most_common(1)[0][0],
                fechas[0] if fechas else None,
            ]
        )
        company_shards[shard(key)][key] = {
            "id": key,
            "nombre": nombre,
            "otros_nombres": [n for n, _ in c["nombres"].most_common(5)][1:],
            "rfc": c["rfc"],
            "n": c["n"],
            "monto": round(c["monto"], 2),
            "categorias": c["categorias"].most_common(8),
            "compradores": c["compradores"].most_common(8),
            "adjudicaciones": c["adjudicaciones"],
        }
    company_index.sort(key=lambda r: (-r[3], r[0]))
    write_json(out / "empresas.json", company_index)
    for key, items in company_shards.items():
        write_json(out / "empresas" / f"{key}.json", items)

    # Compradores.
    buyer_stats: dict[str, dict[str, Any]] = {
        bid: {
            "id": bid,
            "nombre": name,
            "procedimientos": 0,
            "abiertas": 0,
            "adjudicado": 0.0,
            "categorias": Counter(),
            "proveedores": Counter(),
            "entidades": Counter(),
        }
        for bid, name in buyers.items()
    }
    for rec in procs.values():
        b = buyer_stats[rec["comprador_id"]]
        b["procedimientos"] += 1
        b["abiertas"] += rec["estatus"] == "abierta"
        b["categorias"][rec["categoria"]] += 1
        if rec.get("entidad"):
            b["entidades"][rec["entidad"]] += 1
    for a in awards:
        b = buyer_stats[a["comprador_id"]]
        b["adjudicado"] += a["monto_mxn"]
        for key in a["empresas"]:
            b["proveedores"][key] += 1
    company_names = {row[0]: row[1] for row in company_index}
    buyer_list = []
    for b in sorted(buyer_stats.values(), key=lambda x: -x["procedimientos"]):
        buyer_list.append(
            {
                "id": b["id"],
                "nombre": b["nombre"],
                "procedimientos": b["procedimientos"],
                "abiertas": b["abiertas"],
                "adjudicado": round(b["adjudicado"], 2),
                "categorias": b["categorias"].most_common(6),
                "proveedores": [
                    (k, company_names.get(k, k), n) for k, n in b["proveedores"].most_common(10)
                ],
                "entidades": b["entidades"].most_common(6),
            }
        )
    write_json(out / "compradores.json", buyer_list)

    # Ganadores recientes.
    recientes = [a for a in awards if a["ganadores"]][:400]
    since_year = (today - timedelta(days=365)).isoformat()
    top_year: Counter[str] = Counter()
    for a in awards:
        if (a["fecha"] or "") >= since_year:
            for key in a["empresas"]:
                top_year[key] += a["monto_mxn"] / max(len(a["empresas"]), 1)
    write_json(
        out / "ganadores.json",
        {
            "recientes": [
                {
                    k: a[k]
                    for k in (
                        "id",
                        "procedimiento_id",
                        "titulo",
                        "fecha",
                        "monto_mxn",
                        "ganadores",
                        "empresas",
                        "comprador_id",
                        "fuente",
                        "categoria",
                        "entidad",
                    )
                }
                for a in recientes
            ],
            "top_anual": [
                {"id": k, "nombre": company_names.get(k, k), "monto": round(v, 2)}
                for k, v in top_year.most_common(25)
            ],
        },
    )

    # Feeds.
    for rel, xml in feeds.all_feeds(open_recs, names, buyers).items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(xml, encoding="utf-8")

    # Meta.
    counts = Counter(r["fuente"] for r in procs.values())
    open_counts = Counter(r["fuente"] for r in open_recs)
    new_today = sum(1 for r in open_recs if r.get("primera_vez") == today.isoformat())
    closing = sum(
        1
        for r in open_recs
        if r.get("apertura")
        and today.isoformat() <= r["apertura"][:10] <= (today + timedelta(days=2)).isoformat()
    )
    fix_last = max(data["fix"]) if data["fix"] else None
    meta = {
        "generado": today.isoformat(),
        "totales": {
            "procedimientos": len(procs),
            "contratos": len(contracts),
            "adjudicaciones": len(awards),
            "abiertas": len(open_recs),
            "nuevas_hoy": new_today,
            "cierran_48h": closing,
            "empresas": len(company_index),
            "compradores": len(buyer_list),
            "monto_adjudicado_12m": round(
                sum(
                    a["monto_mxn"]
                    for a in awards
                    if (a["fecha"] or "") >= since_year and not a["atipico"]
                ),
                2,
            ),
        },
        "fuentes": {
            f: {
                "nombre": SOURCE_LABELS[f],
                "procedimientos": counts.get(f, 0),
                "abiertas": open_counts.get(f, 0),
                "ultima_ok": (estado.get(f) or {}).get("ultima_ok"),
                "falla_desde": (estado.get(f) or {}).get("falla_desde"),
            }
            for f in SOURCE_LABELS
        },
        "categorias": [
            {"codigo": c, "nombre": n, "abiertas": sum(1 for r in open_recs if r["categoria"] == c)}
            for c, n in names.items()
        ],
        "compradores": {b["id"]: b["nombre"] for b in buyer_list},
        "estatus": STATUS_LABELS,
        "anios": sorted(by_year, reverse=True),
        "entidades": sorted({r["entidad"] for r in procs.values() if r.get("entidad")}),
        "fix": {"fecha": fix_last, "valor": data["fix"].get(fix_last)} if fix_last else None,
        "pemex_dias_abierta": pemex.OPEN_DAYS,
        "indice_campos": list(INDEX_FIELDS),
        "correcciones_viejas": data["stale_corrections"],
    }
    write_json(out / "meta.json", meta)
    return {
        k: meta["totales"][k] for k in ("procedimientos", "abiertas", "adjudicaciones", "empresas")
    }
