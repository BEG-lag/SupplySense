import pytest

from supplysense.sources import cfe, comprasmx, pemex

CFE_ROW = {
    "Id": 220413,
    "Numero": "CFE-0100-CASAN-0214-2026",
    "Descripcion": "SERVICIO DE SUMINISTRO DE DIÉSEL Y GASOLINA",
    "EstadoProcedimiento": "Adjudicado",
    "EntidadFederativa": "Ciudad de México",
    "TipoProcedimientoClave": "Concurso abierto",
    "TestimonioSocial": False,
    "TipoContratacionClave": "Servicio por Abastecimiento",
    "FechaPublicacion": "/Date(1795623289860)/",
    "NombProveedorAdjudicado": "EMPRESA UNO SA DE CV,EMPRESA DOS SA DE CV,",
    "MONTO": 1500000.5,
    "FechaLimiteOfertas": None,
    "FechaFallo": None,
}

CFE_DETAIL = """<html><body><script>var x = 1;</script>
<div>Empresa</div><div>0100 - CFE Distribución</div>
<div>Área Contratante</div><div>0100 - CFE Distribución</div>
<span>Fecha de Apertura de Ofertas Técnicas</span><span>04/12/2026 09:00 hrs</span>
<span>Fecha de Apertura de Ofertas Económicas</span><span>11/12/2026 09:00 hrs</span>
<span>Fecha de Fallo</span><span>18/12/2026 09:00 hrs</span></body></html>"""


def test_cfe_parse_row():
    rec = cfe.parse_row(CFE_ROW)
    assert rec["id"] == "cfe:220413"
    assert rec["estatus"] == "adjudicada"
    assert rec["publicado"] == "2026-11-25T10:14:49"
    assert rec["ganadores"] == ["EMPRESA UNO SA DE CV", "EMPRESA DOS SA DE CV"]
    assert rec["monto"] == 1500000.5
    assert rec["categoria"] == "combustibles"


def test_cfe_parse_row_without_amount():
    rec = cfe.parse_row(
        {**CFE_ROW, "MONTO": 0.0, "NombProveedorAdjudicado": "", "EstadoProcedimiento": "Vigente"}
    )
    assert rec["monto"] is None
    assert rec["moneda"] is None
    assert rec["estatus"] == "abierta"


def test_cfe_parse_detail():
    detail = cfe.parse_detail(CFE_DETAIL)
    assert detail == {
        "empresa": "CFE Distribución",
        "unidad": "CFE Distribución",
        "apertura": "2026-12-04T09:00:00",
        "apertura_economica": "2026-12-11T09:00:00",
        "fallo": "2026-12-18T09:00:00",
    }


def test_pemex_parse_item_keeps_no_contact_data():
    item = {
        "Id": 2166,
        "Title": "DEE-CAI-B-GCEE-802-105009-26-2",
        "descripcion": "Suministro de gas para operación de cromatógrafos",
        "inicio": "2026-11-19T06:00:00Z",
        "vencimiento": "2027-11-19T06:00:00Z",
        "tipoevento": "Internacional",
        "tiposuministro": "Bienes",
        "areacontratante": "Producción",
        "ID_SISCEP": "WS5986277030",
        "contacto": {"Description": "alguien@pemex.com"},
    }
    rec = pemex.parse_item("Concursos-Abiertos-PEP", item)
    assert rec["id"] == "pemex:Concursos-Abiertos-PEP:2166"
    assert rec["segmento"] == "Exploración y Producción"
    assert rec["publicado"] == "2026-11-19T00:00:00"
    assert rec["url"].startswith(pemex.SITE)
    assert "contacto" not in rec
    assert all("pemex.com" not in str(v) or k == "url" for k, v in rec.items())


EXP_HEADER = [
    "Orden de gobierno",
    "Siglas de la Institución",
    "Institución",
    "Nombre de la UC",
    "Código del expediente",
    "Título del expediente",
    "Tipo Procedimiento",
    "Número de procedimiento/proyecto",
    "Nombre anuncio",
    "Descripción anuncio",
    "Operador anuncio",
    "Correo anuncio",
    "Tipo de contratación",
    "Entidad Federativa",
    "Fecha publicación",
    "Estatus procedimiento",
    "Fecha apertura",
    "Fecha y hora junta de aclaraciones",
    "Fecha de fallo",
    "Dirección del anuncio",
]


def _csv(rows):
    lines = [",".join(f'"{c}"' for c in row) for row in rows]
    return ("\n".join(lines) + "\n").encode("latin-1", errors="replace")


def test_comprasmx_expedientes_filters_scope_and_drops_officials(tmp_path):
    rows = [
        EXP_HEADER,
        [
            "APF",
            "CENAGAS",
            "CENTRO NACIONAL DE CONTROL DEL GAS NATURAL",
            "UC 1",
            "E-2026-1",
            "MANTENIMIENTO DE GASODUCTO",
            "LICITACIÓN PÚBLICA",
            "LA-1",
            "",
            "",
            "Juan Pérez",
            "juan@gob.mx",
            "SERVICIOS",
            "CAMPECHE",
            "2026-11-20 19:17:22",
            "VIGENTE",
            "2026-11-30 11:00:00",
            "2026-11-26 11:00:00",
            "2026-12-07 11:00:00",
            "https://comprasmx/x",
        ],
        [
            "APF",
            "IMSS",
            "INSTITUTO MEXICANO DEL SEGURO SOCIAL",
            "UC 2",
            "E-2026-2",
            "MATERIAL DE CURACIÓN",
            "LICITACIÓN PÚBLICA",
            "LA-2",
            "",
            "",
            "",
            "",
            "ADQUISICIONES",
            "JALISCO",
            "2026-11-20 10:00:00",
            "VIGENTE",
            "",
            "",
            "",
            "",
        ],
    ]
    path = tmp_path / "Expedientes_ComprasMX_2026.csv"
    path.write_bytes(_csv(rows))
    recs = comprasmx.parse_file(path, "expedientes")
    assert [r["id"] for r in recs] == ["cmx:E-2026-1"]
    rec = recs[0]
    assert rec["estatus"] == "abierta"
    assert rec["apertura"] == "2026-11-30T11:00:00"
    assert rec["motivo_alcance"] == "comprador:CENAGAS"
    assert "Juan" not in str(rec)
    assert "juan@" not in str(rec)


def test_comprasmx_missing_columns_fail_loudly(tmp_path):
    path = tmp_path / "x.csv"
    path.write_bytes(_csv([["Algo", "Otro"], ["1", "2"]]))
    with pytest.raises(ValueError, match="faltan columnas"):
        comprasmx.parse_file(path, "expedientes")
