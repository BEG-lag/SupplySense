"""Valida el dataset real de ``data/`` antes de cada commit del workflow diario."""

import re
from pathlib import Path

import pytest

from supplysense import store

DATA = Path(__file__).resolve().parents[1] / "data"
PERSONAL_RFC = re.compile(r"\b[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}\b")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?$")

pytestmark = pytest.mark.skipif(not (DATA / "procedimientos").exists(), reason="sin data/")


@pytest.fixture(scope="module")
def procs():
    return store.load("procedimientos", DATA)


@pytest.fixture(scope="module")
def contracts():
    return store.load("contratos", DATA)


def test_ids_match_source(procs, contracts):
    for rec in list(procs.values()) + list(contracts.values()):
        prefix = {"cfe": "cfe:", "pemex": "pemex:", "comprasmx": "cmx:"}[rec["fuente"]]
        assert rec["id"].startswith(prefix), rec["id"]


def test_required_fields(procs):
    for rec in procs.values():
        assert rec.get("numero"), rec["id"]
        assert rec.get("titulo"), rec["id"]
        assert rec.get("primera_vez"), rec["id"]


def test_dates_are_iso(procs, contracts):
    for rec in list(procs.values()) + list(contracts.values()):
        for key in ("publicado", "apertura", "fallo", "aclaraciones", "firma", "primera_vez"):
            if rec.get(key):
                assert ISO.match(rec[key]), (rec["id"], key, rec[key])


def test_no_personal_rfc_stored():
    """Ningún RFC de persona física (13 caracteres, trae fecha de nacimiento) en data/."""
    for path in DATA.rglob("*.jsonl"):
        match = PERSONAL_RFC.search(path.read_text(encoding="utf-8"))
        assert match is None, (path, match.group() if match else None)


def test_volumes_are_plausible(procs):
    by_source = {}
    for rec in procs.values():
        by_source[rec["fuente"]] = by_source.get(rec["fuente"], 0) + 1
    assert by_source.get("cfe", 0) > 50_000
    assert by_source.get("pemex", 0) > 5_000
    # ComprasMX no se guarda completo: solo su índice de "vistos".
    assert by_source.get("comprasmx", 0) == 0
    assert len(store.load_seen(DATA)) > 50_000
