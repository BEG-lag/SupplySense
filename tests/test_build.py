import json
from datetime import date

from supplysense import store
from supplysense.build import build_site, final_status, state_name

TODAY = date(2026, 11, 25)


def _awarded(i, monto, cat_title="SUMINISTRO DE VÁLVULAS DE COMPUERTA"):
    return {
        "id": f"cfe:{i}",
        "fuente": "cfe",
        "numero": f"CFE-0100-CA-{i}-2025",
        "titulo": cat_title,
        "estatus": "adjudicada",
        "publicado": f"2025-0{1 + i % 9}-10T10:00:00",
        "monto": monto,
        "ganadores": [f"EMPRESA {i % 3} SA DE CV"],
        "entidad": "Veracruz de Ignacio de la Llave",
        "tipo_contratacion": "Adquisición por Abastecimientos",
        "primera_vez": "2025-01-10",
    }


def _fixture(root):
    procs = {f"cfe:{i}": _awarded(i, 100_000 * (i + 1)) for i in range(40)}
    procs["cfe:900"] = {
        "id": "cfe:900",
        "fuente": "cfe",
        "numero": "CFE-0100-CA-900-2026",
        "titulo": "SUMINISTRO DE VÁLVULAS DE COMPUERTA PARA SUBESTACIÓN",
        "estatus": "abierta",
        "publicado": "2026-11-24T09:00:00",
        "apertura": "2026-12-04T09:00:00",
        "empresa": "CFE Distribución",
        "entidad": "CAMPECHE",
        "primera_vez": "2026-11-24",
    }
    procs["cfe:901"] = {**procs["cfe:900"], "id": "cfe:901", "apertura": "2026-11-20T09:00:00"}
    procs["pemex:L:1"] = {
        "id": "pemex:L:1",
        "fuente": "pemex",
        "numero": "P-1",
        "titulo": "Tubería de acero",
        "segmento": "Logística",
        "publicado": "2026-11-20T00:00:00",
        "primera_vez": "2026-11-20",
    }
    contracts = {
        "cmx:c:1": {
            "id": "cmx:c:1",
            "fuente": "comprasmx",
            "procedimiento_id": "cmx:E-1",
            "titulo": "Mantenimiento de gasoducto",
            "comprador": "CENTRO NACIONAL DE CONTROL DEL GAS NATURAL",
            "siglas": "CENAGAS",
            "proveedor": "DUCTOS DEL GOLFO SA DE CV",
            "proveedor_rfc": "DGO0101019A1",
            "monto": 100_000,
            "moneda": "USD",
            "firma": "2026-06-01",
            "primera_vez": "2026-06-01",
        },
    }
    store.save("procedimientos", procs, root)
    store.save("contratos", contracts, root)
    store.save_json(root / "externos" / "fix.json", {"2026-05-29": 19.5, "2026-06-01": 19.6})
    store.save_json(root / "estado_fuentes.json", {"cfe": {"ultima_ok": "2026-11-25"}})


def test_build_site_end_to_end(tmp_path):
    root, out = tmp_path / "data", tmp_path / "site"
    _fixture(root)
    summary = build_site(
        root, out, today=TODAY, cache_dir=tmp_path / "cache", raw_dir=tmp_path / "raw"
    )
    assert summary["procedimientos"] == 43
    meta = json.loads((out / "meta.json").read_text())
    fields = meta["indice_campos"]
    abiertas = [
        dict(zip(fields, row, strict=True))
        for row in json.loads((out / "abiertas.json").read_text())
    ]
    ids = {r["id"] for r in abiertas}
    assert "cfe:900" in ids
    assert "pemex:L:1" in ids
    assert "cfe:901" not in ids  # la apertura ya pasó: en evaluación
    cfe900 = next(r for r in abiertas if r["id"] == "cfe:900")
    assert cfe900["entidad"] == "Campeche"
    assert cfe900["comprador_id"] == "cfe-distribucion"
    precios = json.loads((out / "precios" / "valvulas.json").read_text())
    assert precios["n"] == 40
    assert precios["percentiles"]["50"] > 0
    ganadores = json.loads((out / "ganadores.json").read_text())
    usd = next(a for a in ganadores["recientes"] if a["id"] == "cmx:c:1")
    assert usd["monto_mxn"] == 1_960_000.0  # 100,000 USD x FIX del 1 de junio
    assert (out / "feed.xml").read_text().count("<entry>") == 2


def test_no_personal_rfc_in_outputs(tmp_path):
    root, out = tmp_path / "data", tmp_path / "site"
    _fixture(root)
    build_site(root, out, today=TODAY, cache_dir=tmp_path / "cache", raw_dir=tmp_path / "raw")
    import re

    for path in out.rglob("*.json"):
        assert not re.search(r"\b[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}\b", path.read_text()), path


def test_final_status_rules():
    assert final_status({"fuente": "pemex", "publicado": "2026-11-10T00:00:00"}, TODAY) == (
        "abierta",
        True,
    )
    assert final_status({"fuente": "pemex", "publicado": "2026-09-01T00:00:00"}, TODAY) == (
        "aviso",
        True,
    )
    assert final_status(
        {"fuente": "cfe", "estatus": "abierta", "apertura": "2026-11-01T09:00:00"}, TODAY
    ) == ("en_evaluacion", True)
    assert final_status({"fuente": "cfe", "estatus": "desierta"}, TODAY) == ("desierta", False)


def test_state_names_unified():
    assert state_name("VERACRUZ") == state_name("Veracruz de Ignacio de la Llave") == "Veracruz"
    assert state_name("MÉXICO") == "Estado de México"
    assert state_name("CAMPECHE") == "Campeche"


def test_comprasmx_is_read_from_raw_cache_with_seen_dates(tmp_path):
    from supplysense.build import load_comprasmx

    raw = tmp_path / "raw"
    raw.mkdir()
    header = [
        "Orden de gobierno",
        "Siglas de la Institución",
        "Institución",
        "Nombre de la UC",
        "Código del expediente",
        "Título del expediente",
        "Tipo Procedimiento",
        "Número de procedimiento/proyecto",
        "Tipo de contratación",
        "Entidad Federativa",
        "Fecha publicación",
        "Estatus procedimiento",
        "Fecha apertura",
        "Dirección del anuncio",
    ]
    row = [
        "APF",
        "IMSS",
        "INSTITUTO MEXICANO DEL SEGURO SOCIAL",
        "UC",
        "E-2026-9",
        "ADQUISICIÓN DE MEDICAMENTOS ONCOLÓGICOS",
        "LICITACIÓN PÚBLICA",
        "LA-9",
        "ADQUISICIONES",
        "JALISCO",
        "2026-11-20 10:00:00",
        "VIGENTE",
        "2026-12-01 10:00:00",
        "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/detalle/"
        "0123456789abcdef0123456789abcdef/procedimiento",
    ]
    text = "\n".join(",".join(f'"{c}"' for c in r) for r in (header, row)) + "\n"
    (raw / "Expedientes_ComprasMX_2026.csv").write_bytes(text.encode("latin-1"))
    procs, contracts, missing = load_comprasmx(raw, {"cmx:E-2026-9": "2026-11-21"}, TODAY)
    assert [p["id"] for p in procs] == ["cmx:E-2026-9"]
    assert procs[0]["primera_vez"] == "2026-11-21"
    assert procs[0]["motivo_alcance"] is None  # no es del sector energía
    assert contracts == []
    assert "Contratos_ComprasMX_2026.csv" in missing


def test_public_record_shrinks_links():
    from supplysense.build import public_record

    rec = {
        "id": "cmx:E-1",
        "fuente": "comprasmx",
        "comprador": "X",
        "comprador_nombre": "X",
        "url": "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/detalle/"
        "0123456789abcdef0123456789abcdef/procedimiento",
        "estatus_estimado": False,
    }
    out = public_record(rec)
    assert out["anuncio"] == "0123456789abcdef0123456789abcdef"
    assert "url" not in out
    assert "comprador" not in out
    assert "estatus_estimado" not in out
