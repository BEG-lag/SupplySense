"""Reglas versionadas en ``reglas/*.csv``: compradores de energía, palabras de contexto
energético, categorías, estatus y correcciones manuales.

SupplySense cubre todos los giros de las compras federales. ``scope_reason`` marca qué
registros forman la vertical de energía y O&G (por comprador o por palabras de contexto).

Las reglas viven en CSV para que cualquiera pueda leerlas y discutirlas sin leer código. Los
patrones de alcance y categorías se aplican sobre texto sin acentos y en minúsculas.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from .text import fold

RULES_DIR = Path(__file__).resolve().parents[2] / "reglas"

OTROS = ("otros", "Otros")
CATEGORY_FALLBACK_BY_TYPE = (("obra", "obra_construccion"),)


@dataclass(frozen=True)
class Buyer:
    siglas: str
    patron: re.Pattern[str]
    nombre: str


@dataclass(frozen=True)
class Category:
    codigo: str
    nombre: str
    grupo: str
    incluir: re.Pattern[str]
    excluir: re.Pattern[str] | None


@dataclass(frozen=True)
class Correction:
    id: str
    campo: str
    valor_original: str
    valor_corregido: str
    motivo: str
    evidencia_url: str


def _rows(name: str, root: Path) -> list[dict[str, str]]:
    with (root / name).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


@cache
def buyers(root: Path = RULES_DIR) -> tuple[Buyer, ...]:
    return tuple(
        Buyer(r["siglas"], re.compile(r["patron"], re.I), r["nombre"])
        for r in _rows("compradores_energia.csv", root)
    )


@cache
def scope_words(root: Path = RULES_DIR) -> tuple[tuple[re.Pattern[str], str], ...]:
    return tuple(
        (re.compile(r["patron"]), r["motivo"]) for r in _rows("alcance_palabras.csv", root)
    )


@cache
def categories(root: Path = RULES_DIR) -> tuple[Category, ...]:
    return tuple(
        Category(
            r["codigo"],
            r["nombre"],
            r["grupo"],
            re.compile(r["incluir"]),
            re.compile(r["excluir"]) if r["excluir"] else None,
        )
        for r in _rows("categorias.csv", root)
    )


def category_groups(root: Path = RULES_DIR) -> dict[str, str]:
    groups = {c.codigo: c.grupo for c in categories(root)}
    groups[OTROS[0]] = "general"
    return groups


def category_names(root: Path = RULES_DIR) -> dict[str, str]:
    names = {c.codigo: c.nombre for c in categories(root)}
    names[OTROS[0]] = OTROS[1]
    return names


@cache
def statuses(root: Path = RULES_DIR) -> dict[tuple[str, str], str]:
    return {(r["fuente"], r["estatus_fuente"]): r["estatus"] for r in _rows("estatus.csv", root)}


@cache
def corrections(root: Path = RULES_DIR) -> tuple[Correction, ...]:
    return tuple(Correction(**r) for r in _rows("correcciones.csv", root))


def match_buyer(institucion: str | None, siglas: str | None = None) -> Buyer | None:
    text = " ".join(x for x in (siglas, institucion) if x)
    for buyer in buyers():
        if (siglas and siglas.strip().upper() == buyer.siglas) or buyer.patron.search(text):
            return buyer
    return None


def scope_reason(institucion: str | None, siglas: str | None, texto: str | None) -> str | None:
    """Por qué un registro pertenece a la vertical de energía y O&G, o None si no."""
    buyer = match_buyer(institucion, siglas)
    if buyer:
        return f"comprador:{buyer.siglas}"
    folded = fold(texto)
    for pattern, motivo in scope_words():
        if pattern.search(folded):
            return f"palabra:{motivo}"
    return None


def sector_of(motivo: str | None) -> str:
    return "energia" if motivo else "general"


def categorize(texto: str | None, tipo_contratacion: str | None = None) -> str:
    """Primera categoría cuyo patrón aparece (y cuyo patrón de exclusión no); si ninguna,
    se intenta por el tipo de contratación; si tampoco, ``otros``."""
    folded = fold(texto)
    for cat in categories():
        if cat.incluir.search(folded) and not (cat.excluir and cat.excluir.search(folded)):
            return cat.codigo
    tipo = fold(tipo_contratacion)
    for needle, codigo in CATEGORY_FALLBACK_BY_TYPE:
        if needle in tipo:
            return codigo
    return OTROS[0]


def normalize_status(fuente: str, estatus_fuente: str | None) -> str | None:
    if not estatus_fuente:
        return None
    return statuses().get((fuente, estatus_fuente.strip()), "otro")
