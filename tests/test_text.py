from supplysense.text import (
    clean,
    company_key,
    decode_mixed,
    fold,
    public_rfc,
    rfc_kind,
    split_winners,
    strip_rfcs,
    title_name,
)


def test_decode_mixed_reads_latin1_with_stray_utf8():
    raw = "ADQUISICIÓN ".encode("latin-1") + "CLÁSICA".encode() + " PEMEX".encode("latin-1")
    assert decode_mixed(raw) == "ADQUISICIÓN CLÁSICA PEMEX"


def test_decode_mixed_maps_cp1252_quotes():
    assert decode_mixed(b"\x93hola\x94") == "“hola”"


def test_clean_repairs_known_corruption_and_spaces():
    assert clean("  VELADORA   MONSEÃOR ") == "VELADORA MONSEÑOR"
    assert clean("   ") is None


def test_fold():
    assert fold("Válvulas de Compuerta Ñ") == "valvulas de compuerta n"


def test_company_key_ignores_legal_form():
    assert company_key("AVALTEC, S.A. DE C.V.") == company_key("Avaltec SA de CV") == "avaltec"


def test_rfc_privacy():
    assert rfc_kind("AAA0003232I9") == "moral"
    assert rfc_kind("GOMA800101AB1") == "fisica"
    assert rfc_kind("XEXX010101000") == "generico"
    assert public_rfc("AAA0003232I9") == "AAA0003232I9"
    assert public_rfc("GOMA800101AB1") is None


def test_split_winners_keeps_legal_suffix_together():
    assert split_winners("ELECTROMECANICOS MONTERREY SA DE CV,L Y F INGENIERIA SA DE CV,") == [
        "ELECTROMECANICOS MONTERREY SA DE CV",
        "L Y F INGENIERIA SA DE CV",
    ]
    assert split_winners(
        "GLENCORE INTERNATIONAL,A.G.,SOLUCIONES PETRONAVALES, S. DE R.L. DE C.V.,"
    ) == [
        "GLENCORE INTERNATIONAL, A.G.",
        "SOLUCIONES PETRONAVALES, S. DE R.L. DE C.V.",
    ]
    assert split_winners("") == []


def test_winner_rfcs_are_removed():
    assert strip_rfcs("9132069176735 - ENTIA DE MEXICO SA DE CV") == "ENTIA DE MEXICO SA DE CV"
    assert strip_rfcs("3M MEXICO SA DE CV") == "3M MEXICO SA DE CV"
    assert (
        strip_rfcs("GOPR6102065R0/DMC0310209U4 - RAYMUNDO GONZALEZ PEREZ")
        == "RAYMUNDO GONZALEZ PEREZ"
    )
    assert (
        strip_rfcs("TIN170908SZ5/SEPA890216L25 - TESLA INNOVATION SA DE CV")
        == "TESLA INNOVATION SA DE CV"
    )
    assert split_winners(
        "COM120924MW7/SASD8108171M1/OCO200806KN5 - COMACAM SA DE CV,LICSA SA DE CV,"
    ) == ["COMACAM SA DE CV", "LICSA SA DE CV"]


def test_title_name():
    assert (
        title_name("INSTITUTO MEXICANO DEL SEGURO SOCIAL") == "Instituto Mexicano del Seguro Social"
    )
    assert title_name("SECRETARÍA DE INFRAESTRUCTURA, COMUNICACIONES Y TRANSPORTES") == (
        "Secretaría de Infraestructura, Comunicaciones y Transportes"
    )
    assert (
        title_name("SERVICIOS DE SALUD (IMSS-BIENESTAR)") == "Servicios de Salud (IMSS-BIENESTAR)"
    )
    assert title_name("ALIMENTACIÓN PARA EL BIENESTAR, S.A. DE C.V.") == (
        "Alimentación para el Bienestar, S.A. de C.V."
    )
    assert title_name("Ya en formato") == "Ya en formato"
