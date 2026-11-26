"""Línea de comandos: ``supplysense update | descargar | build | stats | check``."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from . import __version__, store
from .dates import today_mx


def _date(text: str) -> date:
    return date.fromisoformat(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="supplysense", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--data", type=Path, default=store.DATA_DIR, help="carpeta de datos")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    upd = sub.add_parser("update", help="lee las fuentes oficiales y actualiza data/")
    upd.add_argument("--today", type=_date, default=None, help="fecha de hoy (AAAA-MM-DD)")
    upd.add_argument(
        "--solo",
        nargs="*",
        default=None,
        help="solo estas fuentes (cfe pemex comprasmx jalisco cdmx campeche guanajuato "
        "nuevo_leon banxico oaj dof tabasco edomex fix)",
    )
    upd.add_argument("--anios", nargs="*", type=int, default=None, help="años de ComprasMX")
    upd.add_argument(
        "--detalles", type=int, default=150, help="máximo de detalles de CFE a leer en esta corrida"
    )
    upd.add_argument(
        "--historico",
        type=int,
        default=0,
        help="carga inicial de portales propios: ids previos de CDMX, PDFs de Campeche, días "
        "del DOF; con cualquier valor, el histórico de Guanajuato, OAJ y Nuevo León",
    )

    build = sub.add_parser("build", help="genera los JSON y feeds del sitio")
    build.add_argument("--out", type=Path, default=Path("web/public/data"))
    build.add_argument("--today", type=_date, default=None)

    desc = sub.add_parser("descargar", help="baja los archivos de ComprasMX que falten en caché")
    desc.add_argument("--today", type=_date, default=None)

    sub.add_parser("stats", help="resumen de los datos guardados")

    chk = sub.add_parser("check", help="falla si una fuente lleva 3 días o más sin leerse")
    chk.add_argument("--today", type=_date, default=None)
    chk.add_argument("--dias", type=int, default=3)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.command == "update":
        from .pipeline import SOURCES, update

        today = args.today or today_mx()
        sources = tuple(args.solo) if args.solo else SOURCES
        years = tuple(args.anios) if args.anios else None
        report = update(
            today,
            root=args.data,
            sources=sources,
            years=years,
            max_details=args.detalles,
            backfill=args.historico,
        )
        print(f"update {today}: {len(report.ok)} fuentes ok")
        for name, error in report.failed.items():
            print(f"  falló {name}: {error}")
        print(f"  registros: {report.counts}")
        print(f"  archivos cambiados: {len(report.changed)}")
        return 1 if report.failed and not report.ok else 0

    if args.command == "descargar":
        from .http import PoliteClient
        from .pipeline import CACHE_DIR, ensure_raw

        with PoliteClient() as client:
            got = ensure_raw(client, args.today or today_mx(), CACHE_DIR)
        print(f"descargados: {', '.join(got) or 'ninguno (ya estaban en caché)'}")
        return 0

    if args.command == "build":
        from .build import build_site

        summary = build_site(args.data, args.out, today=args.today or today_mx())
        print(f"build {args.out}: {summary}")
        return 0

    if args.command == "stats":
        from collections import Counter

        procs = store.load("procedimientos", args.data)
        contracts = store.load("contratos", args.data)
        print(f"procedimientos: {len(procs)}")
        print("  por fuente:", dict(Counter(r["fuente"] for r in procs.values())))
        print("  por estatus:", dict(Counter(r.get("estatus") for r in procs.values())))
        print(f"contratos: {len(contracts)}")
        return 0

    if args.command == "check":
        from .pipeline import stale_sources

        stale = stale_sources(args.data, args.today or today_mx(), args.dias)
        if stale:
            print(f"fuentes con {args.dias}+ días fallando: {', '.join(stale)}")
            return 1
        print("todas las fuentes se leyeron en los últimos días")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
