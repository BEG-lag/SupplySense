"""Almacén en archivos JSONL por mes: ``data/<tipo>/AAAA/AAAA-MM.jsonl``.

Un registro por línea, ordenados por ``id``, llaves en orden alfabético y sin marcas de hora
de la descarga: una corrida solo produce diff en git cuando una fuente oficial cambió.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

DATA_DIR = Path("data")
KINDS = ("procedimientos", "contratos")
DATE_FIELD = {"procedimientos": "publicado", "contratos": "firma"}


def partition(kind: str, record: dict[str, Any]) -> str:
    value = record.get(DATE_FIELD[kind]) or record.get("publicado") or ""
    if len(value) >= 7 and value[:4].isdigit():
        return f"{value[:4]}/{value[:7]}.jsonl"
    return "sin-fecha.jsonl"


def dumps(record: dict[str, Any]) -> str:
    clean = {k: v for k, v in record.items() if v not in (None, "", [], {})}
    return json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load(kind: str, root: Path = DATA_DIR) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    base = root / kind
    if not base.exists():
        return records
    for path in sorted(base.rglob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    records[rec["id"]] = rec
    return records


def iter_records(kind: str, root: Path = DATA_DIR) -> Iterable[dict[str, Any]]:
    return load(kind, root).values()


def save(kind: str, records: dict[str, dict[str, Any]], root: Path = DATA_DIR) -> list[str]:
    """Escribe todas las particiones; devuelve las que cambiaron (y borra las vacías)."""
    base = root / kind
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records.values():
        groups[partition(kind, rec)].append(rec)
    changed: list[str] = []
    for rel, recs in groups.items():
        path = base / rel
        text = "".join(dumps(r) + "\n" for r in sorted(recs, key=lambda r: r["id"]))
        if path.exists() and path.read_text(encoding="utf-8") == text:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        changed.append(f"{kind}/{rel}")
    if base.exists():
        for path in base.rglob("*.jsonl"):
            if str(path.relative_to(base)) not in groups:
                path.unlink()
                changed.append(f"{kind}/{path.relative_to(base)} (borrado)")
    return sorted(changed)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


# ── Índice de "vistos" de ComprasMX ──────────────────────────────────────────
# Los archivos de ComprasMX son fotos completas del año: no se guardan en git. Solo se guarda
# cuándo vimos cada registro por primera vez, una línea "id<TAB>AAAA-MM-DD", en archivos por
# mes de esa fecha. Una corrida nueva solo agrega líneas al mes en curso.

SEEN_DIR = "vistos"


def load_seen(root: Path = DATA_DIR) -> dict[str, str]:
    seen: dict[str, str] = {}
    base = root / SEEN_DIR
    if not base.exists():
        return seen
    for path in sorted(base.glob("*.tsv")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                key, day = line.split("\t", 1)
                seen[key] = day
    return seen


def save_seen(seen: dict[str, str], root: Path = DATA_DIR) -> list[str]:
    base = root / SEEN_DIR
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key, day in seen.items():
        groups[day[:7]].append((key, day))
    changed: list[str] = []
    for month, items in groups.items():
        path = base / f"{month}.tsv"
        text = "".join(f"{k}\t{d}\n" for k, d in sorted(items))
        if path.exists() and path.read_text(encoding="utf-8") == text:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        changed.append(f"{SEEN_DIR}/{month}.tsv")
    if base.exists():
        for path in base.glob("*.tsv"):
            if path.stem not in groups:
                path.unlink()
                changed.append(f"{SEEN_DIR}/{path.name} (borrado)")
    return sorted(changed)
