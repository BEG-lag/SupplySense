import pytest

from supplysense.rules import categorize, match_buyer, normalize_status, scope_reason


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("SERVICIO DE SUMINISTRO DE DIÉSEL Y GASOLINA", "combustibles"),
        ("Adquisición de válvulas de compuerta para la refinería", "valvulas"),
        ("Suministro de transformadores de distribución", "equipo_electrico"),
        ("Arrendamiento de grúa para maniobras en plataforma", "gruas_izaje"),
        ("Terminación y reparación de pozos petroleros", "perforacion"),
        ("Rehabilitación de pozo de visita en colonia centro", "mantenimiento"),
        ("Servicio de limpieza de oficinas", "limpieza"),
        ("Adquisición de medicamentos oncológicos", "medicamentos"),
        ("Monederos electrónicos para vales de despensa", "servicios_financieros"),
        ("Reactivos de laboratorio para hospital", "material_curacion"),
        ("Arrendamiento de vehículos para supervisión", "vehiculos"),
        ("Póliza de seguro de vida", "seguros"),
        ("Algo totalmente distinto", "otros"),
    ],
)
def test_categorize(title, expected):
    assert categorize(title) == expected


def test_categorize_falls_back_to_contract_type():
    assert categorize("Paquete 3 zona norte", "Contratación de Obras") == "obra_construccion"


def test_scope_by_buyer_and_by_context_word():
    assert (
        scope_reason("CENTRO NACIONAL DE CONTROL DEL GAS NATURAL", "CENAGAS", "x")
        == "comprador:CENAGAS"
    )
    assert (
        scope_reason("INSTITUTO MEXICANO DEL SEGURO SOCIAL", "IMSS", "Construcción de gasoducto")
        == "palabra:gasoducto"
    )
    assert (
        scope_reason("INSTITUTO MEXICANO DEL SEGURO SOCIAL", "IMSS", "Material de curación") is None
    )


def test_match_buyer_by_siglas():
    assert match_buyer("PETRÓLEOS MEXICANOS").siglas == "PEMEX"
    assert match_buyer("", "IMP").siglas == "IMP"


def test_normalize_status():
    assert normalize_status("cfe", "Vigente") == "abierta"
    assert normalize_status("comprasmx", "EN ACLARACIONES") == "abierta"
    assert normalize_status("comprasmx", "ADJUDICADO PARCIAL") == "adjudicada"
    assert normalize_status("comprasmx", "ALGO NUEVO") == "otro"
    assert normalize_status("cfe", None) is None
