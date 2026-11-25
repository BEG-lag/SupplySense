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


def test_synonyms_point_to_existing_categories():
    from supplysense.rules import categories, synonyms

    codes = {c.codigo for c in categories()}
    assert synonyms()
    assert set(synonyms().values()) <= codes


def test_category_patterns_are_portable_to_javascript():
    """El sitio compila estos patrones con RegExp: nada de sintaxis exclusiva de Python."""
    from supplysense.rules import categories

    for c in categories():
        for pattern in (c.incluir.pattern, c.excluir.pattern if c.excluir else ""):
            assert "(?P" not in pattern
            assert "(?i" not in pattern
            assert "\\A" not in pattern
            assert "\\Z" not in pattern
