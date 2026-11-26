"""Portales propios agregados en la tercera ronda: Guanajuato, subastas de Nuevo León, Banxico,
OAJ y resúmenes de convocatoria del DOF. Las muestras son reales, recortadas y sin nombres de
servidores públicos."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from supplysense.build import final_status, number_key
from supplysense.sources import banxico, dof, guanajuato, nuevo_leon, oaj

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 11, 26)


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


def test_guanajuato_list_status_and_federal_filter():
    rows = json.loads(read("guanajuato_lista.json"))["rows"]
    recs = {r["id"]: r for r in guanajuato.parse_rows(rows)}
    assert len(recs) == len(rows) - 1  # la "Licitación Pública Federal" ya está en ComprasMX
    assert all(r["fuente"] == "guanajuato" and r["entidad"] == "Guanajuato" for r in recs.values())
    by_status = {r["estatus"] for r in recs.values()}
    assert {"abierta", "en_evaluacion", "concluida"} <= by_status
    direct = [r for r in recs.values() if r["tipo_procedimiento"] == "Adjudicación Directa"]
    assert direct
    assert all(r["estatus"] == "concluida" for r in direct)
    assert any(r["tipo_procedimiento"] == "Invitación a cuando menos tres" for r in recs.values())


def test_guanajuato_convocatoria_dates_and_law():
    out = guanajuato.parse_text(read("guanajuato_convocatoria.txt"))
    assert out["aclaraciones"] == "2026-12-03T15:00:00"
    assert out["apertura"] == "2026-12-11T09:00:00"
    assert out["fallo"] == "2026-12-23T12:00:00"
    assert out["recursos"] == "Estatal"
    assert out["ley"] == "Ley de Contrataciones Públicas para el Estado de Guanajuato"


def test_nuevo_leon_list_and_detail():
    page = nuevo_leon.decode((FIXTURES / "nuevo_leon_lista.html").read_bytes())
    recs = {r["fuente_id"]: r for r in nuevo_leon.parse_list(page)}
    open_one = recs[1292]
    assert open_one["numero"] == "DGCNL-DC-SEIN-029/2026"
    assert open_one["comprador"] == "Secretaría de Economía"
    assert open_one["apertura"] == "2026-11-30T08:00:00"
    assert not open_one["titulo"].upper().startswith("DGCNL")
    assert nuevo_leon.status(open_one) == "abierta"
    # Números antiguos con "NO." delante también se separan del objeto.
    assert all(not r["titulo"].upper().startswith("NO.") for r in recs.values())

    detail = nuevo_leon.parse_detail(
        nuevo_leon.decode((FIXTURES / "nuevo_leon_subasta.html").read_bytes())
    )
    assert detail["estatus_fuente"] == "Cerrada"
    assert detail["fallo"] == "2026-11-11T13:00:00"  # 01:00 p.m.
    assert detail["ganadores"] == ["Seguros el Potosi, S.A."]
    assert detail["monto"] == 47091300.0
    assert detail["precio_base"] == 47241379.31
    assert len(detail["participantes"]) == 6
    assert nuevo_leon.status({**recs[1291], **detail}) == "adjudicada"


def test_banxico_rows_and_stages():
    rows = banxico._json((FIXTURES / "banxico_lista.json").read_bytes())["data"]
    recs = [banxico.parse_row(r) for r in rows]
    assert [r["estatus"] for r in recs] == ["abierta", "en_evaluacion", "concluida", "concluida"]
    assert recs[0]["numero"].startswith("BM-")
    assert recs[0]["caracter"] in ("Nacional", "Internacional")
    stages = banxico.parse_stages(
        banxico._json((FIXTURES / "banxico_etapas.json").read_bytes())["data"]
    )
    assert stages == {
        "aclaraciones": "2026-12-03T23:59:00",
        "apertura": "2026-12-10T11:30:00",
        "fallo": "2026-12-30",
    }


def test_oaj_rows_fallo_and_cancelled():
    dgrm = oaj.parse_list(read("oaj_dgrm.html"), "dgrm", 2026)
    dgim = oaj.parse_list(read("oaj_dgim.html"), "dgim", 2026)
    assert dgrm
    assert dgim
    assert all(r["numero"].startswith("OAJ") and r["publicado"] for r in dgrm + dgim)
    assert any(r["estatus"] == "concluida" for r in dgim)  # con acta de fallo
    cancelled = [r for r in dgrm + dgim if r["estatus"] == "cancelada"]
    assert cancelled
    assert all("CANCEL" not in r["numero"].upper() for r in cancelled)
    assert all(not r["url"].endswith(".zip") for r in dgrm + dgim)


def test_dof_notes_formats_and_dedup():
    notes = dof.list_notes(json.loads(read("dof_notas.json")))
    assert notes
    assert all(n["codOrgaUno"] == "CV" for n in notes)

    ine = dof.parse_note(
        read("dof_ine.html"), 5805465, "INSTITUTO NACIONAL ELECTORAL - REF:582831", "2026-11-26"
    )
    assert len(ine) == 1
    assert ine[0]["numero"] == "INE-LPN-OP/004/2026"
    assert ine[0]["aclaraciones"] == "2026-12-04T12:00:00"  # "diciembr e" cortado en el DOF
    assert ine[0]["apertura"] == "2026-12-14T12:00:00"
    assert ine[0]["comprador"] == "INSTITUTO NACIONAL ELECTORAL"
    assert ine[0]["url"].startswith("https://www.dof.gob.mx/nota_detalle.php?codigo=5805465")

    dip = dof.parse_note(
        read("dof_diputados.html"), 5805467, "h. CAMARA DE DIPUTADOS - REF:1", "2026-11-26"
    )
    assert dip[0]["numero"] == "HCD/LXVI/LPN/10/2027"
    assert dip[0]["registro"] == "2026-12-02"
    assert dip[0]["apertura"] == "2026-12-14T12:30:00"

    # Con número de ComprasMX ya lo tenemos: se descarta.
    assert (
        dof.parse_note(
            read("dof_comprasmx.html"), 1, "SERVICIOS DE SALUD DE VERACRUZ - REF:2", "2026-11-26"
        )
        == []
    )
    assert (
        dof.convocante("070Q94 - UNIVERSIDAD DE GUANAJUATO - REF:582726")
        == "UNIVERSIDAD DE GUANAJUATO"
    )
    assert dof.convocante("h. CAMARA DE DIPUTADOS - REF:582866") == "H. CAMARA DE DIPUTADOS"
    assert dof.entidad("UNIVERSIDAD AUTONOMA DE NUEVO LEON") == "Nuevo León"
    assert dof.entidad("UNIVERSIDAD NACIONAL AUTONOMA DE MEXICO") is None
    assert dof.parse_when("24/11/20 26") == "2026-11-24"


def test_portal_status_from_dates_and_stale_rules():
    base = {"estatus": "abierta", "numero": "X-1/2026"}
    # DOF y Guanajuato: sin fecha de apertura, abiertas 30 días desde la publicación.
    assert final_status({**base, "fuente": "dof", "publicado": "2026-11-10"}, TODAY) == (
        "abierta",
        True,
    )
    assert final_status({**base, "fuente": "dof", "publicado": "2026-10-01"}, TODAY) == (
        "concluida",
        True,
    )
    # Banxico y Nuevo León dan el estatus oficial: no es estimado.
    assert final_status(
        {**base, "fuente": "banxico", "apertura": "2026-12-10T11:30:00"}, TODAY
    ) == ("abierta", False)
    # En evaluación por meses: ya terminó.
    old = {"fuente": "oaj", "estatus": "en_evaluacion", "apertura": "2026-06-01"}
    assert final_status(old, TODAY) == ("concluida", True)
    assert number_key("OAJ/SEA/DGRM/LPN/001/2027") == number_key("oaj sea dgrm lpn 001 2027")


def test_tabasco_grid_contracts_and_pdf():
    from supplysense.sources import tabasco

    recs = tabasco.parse_procedures(read("tabasco_seguimiento.html"), "adq")
    assert recs
    assert all(r["id"].startswith("tab:") and r["entidad"] == "Tabasco" for r in recs)
    assert all(r["comprador"] for r in recs)
    assert {r["estatus"] for r in recs} <= {"en_evaluacion", "concluida", "desierta", "cancelada"}
    assert all(r["url"] and "Archivos_Adjuntos" in r["url"] for r in recs)
    vigentes = tabasco.parse_procedures(read("tabasco_seguimiento.html"), "obra", vigente=True)
    assert all(r["estatus"] == "abierta" for r in vigentes)

    contracts = tabasco.parse_contracts(read("tabasco_contratos.html"))
    assert contracts["5627D051-001-2025"]["ganadores"] == ["ONT NETWORKS SA DE CV"]
    assert contracts["5627D051-001-2025"]["monto"] == 7874996.4
    assert len(contracts["5627D051-002-2025"]["ganadores"]) == 3

    out = tabasco.parse_text(read("tabasco_convocatoria.txt"), 2026)
    assert out["titulo"].startswith("Adquisición de vales de despensa")
    assert out["registro"] == "2026-11-05T15:00:00"
    assert out["aclaraciones"] == "2026-11-10T10:00:00"  # "1 O de noviembre" en el OCR
    assert out["apertura"] == "2026-11-17T10:00:00"
    assert out["apertura_economica"] == "2026-11-19T10:00:00"
    assert out["ley"].startswith("Ley de Adquisiciones, Arrendamientos y Prestación")


def test_edomex_central_and_others():
    from supplysense.sources import edomex

    rows = json.loads(read("edomex_filas.json"))
    central = edomex.parse_central(rows["central"])
    assert [r["estatus"] for r in central] == ["abierta", "abierta", "en_evaluacion", "concluida"]
    assert all(r["estatus_oficial"] and r["entidad"] == "Estado de México" for r in central)
    assert central[0]["numero"].startswith("LPNP-")

    aux = {r["numero"]: r for r in edomex.parse_other(rows["auxiliares"], "3")}
    assert "LPE-005-2026" in aux
    assert aux["LPE-005-2026"]["titulo"].startswith("CONTRATACION DEL SERVICIO DE VIGILANCIA")
    assert any(r["comprador"].startswith("Colegio de Bachilleres") for r in aux.values())
    # Actas, adjudicaciones directas y números cortados no entran.
    assert not any(n.startswith(("ACTA", "AD")) or "IMPERMEABILIZACI" in n for n in aux)

    # "UNIFORMES - JUNTA ACLARACIONES" (una palabra tras quitar el documento) y una lista de
    # números sin objeto no son convocatorias útiles.
    assert edomex.parse_other(rows["municipios"], "1") == []

    assert len(edomex.rows(read("edomex_pagina.xml"))) == 9
    assert edomex.buyer("LPN/ISSEMYM/049/2026", "3").startswith("Instituto de Seguridad Social")
    assert edomex.buyer("XYZ-001-2026", "1") == "Municipio del Estado de México"


def test_official_status_without_dates_stays_open():
    rec = {
        "fuente": "edomex",
        "estatus": "abierta",
        "estatus_oficial": True,
        "publicado": "2026-10-01",
    }
    assert final_status(rec, TODAY) == ("abierta", False)
    rec = {"fuente": "edomex", "estatus": "abierta", "publicado": "2026-10-01"}
    assert final_status(rec, TODAY) == ("concluida", True)


def test_tabasco_periodico_oficial_enrichment():
    from supplysense.sources import tabasco

    poe = tabasco.parse_poe(read("tabasco_periodico.html"))
    assert poe[0]["fecha"] == "2026-11-04"
    assert poe[0]["descripcion"].startswith("COBATAB")
    recs = [
        {"numero": "5627D051-003-2026", "titulo": "Licitación 5627D051-003-2026",
         "comprador": "COLEGIO DE BACHILLERES DE TABASCO"},
        {"numero": "5627A122-001-2026", "titulo": "Licitación 5627A122-001-2026",
         "comprador": "H. AYUNTAMIENTO DE MACUSPANA"},
        {"numero": "5627D051-009-2026", "titulo": "Licitación 5627D051-009-2026",
         "comprador": None},
    ]  # fmt: skip
    tabasco.enrich(recs, poe)
    # Por siglas y consecutivo: COBATAB, licitación 003 de 2026.
    assert recs[0]["titulo"].startswith("ADQUISICIÓN DE VALES DE DESPENSA")
    assert recs[0]["publicado"] == "2026-11-04"
    # La nota de Macuspana trae el número pero no dice qué se compra: queda con su convocante.
    assert recs[1]["titulo"] == "Licitación 5627A122-001-2026 de H. Ayuntamiento de Macuspana"
    # El convocante que falta se toma del prefijo del número.
    assert recs[2]["comprador"] == "COLEGIO DE BACHILLERES DE TABASCO"
