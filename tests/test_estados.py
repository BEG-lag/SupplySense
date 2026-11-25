"""Lectores de portales estatales, probados con fragmentos reales (sin datos personales)."""

from datetime import date
from pathlib import Path

from supplysense.build import final_status
from supplysense.dates import from_spanish
from supplysense.pipeline import upsert
from supplysense.sources import campeche, cdmx, jalisco

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 11, 25)


def read(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_from_spanish():
    assert from_spanish("23/noviembre/2026  14:00 horas") == "2026-11-23T14:00:00"
    assert from_spanish("a 17 de noviembre de 2026") == "2026-11-17"
    assert from_spanish("31/febrero/2026") is None


def test_jalisco_list_and_calendar():
    (rec,) = jalisco.parse_list(read("jalisco_lista.html"), "posted")
    assert rec["id"] == "jal:5024"
    assert rec["numero"] == "IA-73-R97-914012998-N58-2026"
    assert not rec["titulo"].startswith('"')
    assert rec["comprador"] == "Secretaría de Educación"
    assert rec["estatus"] == "abierta"
    assert rec["publicado"] == "2026-11-24"
    assert jalisco.parse_detail(read("jalisco_detalle.html")) == {
        "aclaraciones": "2026-11-26T11:00:00",
        "apertura": "2026-12-01T09:30:00",
        "fallo": "2026-12-11T12:00:00",
    }


def test_cdmx_detail_without_personal_data():
    assert cdmx.list_ids(read("cdmx_lista.html")) == [6466, 6467, 6468]
    rec = cdmx.parse_detail(read("cdmx_detalle.html"), 6468)
    assert rec["numero"] == "EA-909007972-I19-26"
    assert rec["comprador"] == "Servicios de Salud Pública"
    assert rec["tipo_procedimiento"] == "Licitación Pública"
    assert rec["apertura"] == "2026-11-30T11:00:00"
    assert rec["fallo"] == "2026-12-01T11:00:00"
    assert rec["url"].endswith("/detalle_convocatoria/NjQ2OA==")
    assert "OMITIDO" not in str(rec)  # el responsable no se guarda


def test_campeche_list_and_pdf_text():
    items = campeche.parse_list(read("campeche_lista.html"))
    assert items[0]["id"] == "2524"
    rec = campeche.parse_text(
        read("campeche_convocatoria.txt"), "2524", items[0]["titulo"], items[0]["href"]
    )
    assert rec["numero"] == "SAFIN-EST-074-2026"
    assert rec["unidad"] == "Secretaría de Turismo"
    assert rec["titulo"].startswith("Contratación del servicio de diseño")
    assert "Estado de Campeche" in rec["ley"]
    assert (rec["registro"], rec["aclaraciones"], rec["apertura"]) == (
        "2026-11-23T14:00:00",
        "2026-11-25T11:00:00",
        "2026-12-01T10:00:00",
    )
    assert rec["publicado"] == "2026-11-17"
    assert "firma" not in str(rec)


def test_state_status_comes_from_dates():
    base = {"fuente": "cdmx", "estatus": "abierta"}
    assert final_status({**base, "apertura": "2026-12-01T10:00:00"}, TODAY) == ("abierta", True)
    assert final_status({**base, "apertura": "2026-11-20T10:00:00"}, TODAY) == (
        "en_evaluacion",
        True,
    )
    assert final_status(
        {**base, "apertura": "2026-11-01T10:00:00", "fallo": "2026-11-10T10:00:00"}, TODAY
    ) == ("concluida", True)
    assert final_status({**base, "publicado": "2026-08-01"}, TODAY) == ("concluida", True)
    jal = {"fuente": "jalisco", "estatus": "abierta", "apertura": "2026-12-01T10:00:00"}
    assert final_status(jal, TODAY) == ("abierta", False)


def test_upsert_keeps_history_and_dates():
    procs = {
        "jal:1": {
            "id": "jal:1",
            "fuente": "jalisco",
            "apertura": "2026-12-01",
            "primera_vez": "2026-11-01",
        }
    }
    upsert(procs, [{"id": "jal:2", "fuente": "jalisco", "publicado": "2026-11-20"}], TODAY)
    upsert(procs, [{"id": "jal:1", "fuente": "jalisco", "apertura": None}], TODAY, ("apertura",))
    assert set(procs) == {"jal:1", "jal:2"}  # lo que no vino en la lista no se borra
    assert procs["jal:1"]["apertura"] == "2026-12-01"
    assert procs["jal:1"]["primera_vez"] == "2026-11-01"


def test_state_records_without_dates_are_never_open():
    assert final_status(
        {"fuente": "campeche", "estatus": "abierta", "numero": "SAFIN-EST-MUE-001-2023"}, TODAY
    ) == (
        "concluida",
        True,
    )
    assert final_status(
        {"fuente": "cdmx", "estatus": "abierta", "numero": "CDMX06PDPA77"}, TODAY
    ) == ("aviso", True)


def test_cdmx_empty_fields_do_not_take_the_next_label():
    page = (
        "<p>Nombre del Procedimiento</p><p>Compra de prueba</p>"
        "<p>Fecha de Publicación</p><p>Tipo de contratación</p><p>Servicios</p>"
        "<p>Carácter</p><p>Número de Procedimiento</p><p>X-1</p>"
    )
    rec = cdmx.parse_detail(page, 1)
    assert rec["publicado"] is None
    assert rec["caracter"] is None
    assert rec["numero"] == "X-1"
