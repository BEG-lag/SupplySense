from datetime import date

import pytest

from supplysense import store
from supplysense.pipeline import merge, stale_sources

TODAY = date(2026, 11, 25)


def test_merge_keeps_first_seen_and_detail_fields():
    stored = {
        "cfe:1": {
            "id": "cfe:1",
            "fuente": "cfe",
            "primera_vez": "2026-11-01",
            "empresa": "CFE Distribución",
        },
        "pemex:1": {"id": "pemex:1", "fuente": "pemex", "primera_vez": "2026-10-01"},
    }
    fresh = [
        {"id": "cfe:1", "fuente": "cfe", "empresa": None, "publicado": "2026-10-30"},
        {"id": "cfe:2", "fuente": "cfe", "publicado": "2026-11-20T09:00:00"},
    ]
    out = merge(stored, fresh, scope=lambda r: r["fuente"] == "cfe", today=TODAY, keep=("empresa",))
    assert out["cfe:1"]["primera_vez"] == "2026-11-01"
    assert out["cfe:1"]["empresa"] == "CFE Distribución"
    assert out["cfe:2"]["primera_vez"] == "2026-11-20"
    assert "pemex:1" in out


def test_merge_brake_rejects_truncated_source():
    stored = {f"cfe:{i}": {"id": f"cfe:{i}", "fuente": "cfe"} for i in range(100)}
    fresh = [{"id": "cfe:1", "fuente": "cfe"}]
    with pytest.raises(ValueError, match="freno"):
        merge(stored, fresh, scope=lambda r: r["fuente"] == "cfe", today=TODAY)


def test_stale_sources(tmp_path):
    store.save_json(
        tmp_path / "estado_fuentes.json",
        {
            "cfe": {"falla_desde": "2026-11-20"},
            "pemex": {"falla_desde": "2026-11-24"},
            "fix": {"ultima_ok": "2026-11-25"},
        },
    )
    assert stale_sources(tmp_path, TODAY) == ["cfe"]
