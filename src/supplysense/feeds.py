"""Feeds Atom 1.0 de convocatorias abiertas: uno general, uno por fuente y uno por categoría.

Deterministas: ``<updated>`` es la fecha de la entrada más nueva, nunca la hora del build.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import quote
from xml.sax.saxutils import escape, quoteattr

SITE_URL = "https://beg-lag.github.io/SupplySense/"
TAG_PREFIX = "tag:beg-lag.github.io,2026:SupplySense/"
MAX_ENTRIES = 100
SOURCES = {
    "comprasmx": "ComprasMX",
    "cfe": "CFE",
    "pemex": "PEMEX",
    "jalisco": "Jalisco",
    "cdmx": "CDMX",
    "campeche": "Campeche",
}


def _updated(rec: dict[str, Any]) -> str:
    value = rec.get("publicado") or "2026-11-25"
    if len(value) == 10:
        value += "T00:00:00"
    return f"{value}-06:00"


def render(
    items: Iterable[dict[str, Any]],
    *,
    title: str,
    subtitle: str,
    path: str,
    names: dict[str, str],
    buyers: dict[str, str],
) -> str:
    entries = sorted(items, key=lambda r: (r.get("publicado") or "", r["id"]), reverse=True)
    entries = entries[:MAX_ENTRIES]
    self_url = SITE_URL + path
    updated = max((_updated(r) for r in entries), default="2026-11-25T00:00:00-06:00")
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="es-MX">',
        f"  <title>{escape(title)}</title>",
        f"  <subtitle>{escape(subtitle)}</subtitle>",
        f'  <link rel="self" type="application/atom+xml" href={quoteattr(self_url)}/>',
        f'  <link rel="alternate" type="text/html" href="{SITE_URL}"/>',
        f"  <id>{escape(self_url)}</id>",
        f"  <updated>{updated}</updated>",
        "  <author><name>Benjamín Esponda García · PIVOTEK</name>"
        "<uri>https://pivotek.mx</uri></author>",
        '  <generator uri="https://github.com/BEG-lag/SupplySense">SupplySense</generator>',
        "  <rights>Información pública de CFE, PEMEX y ComprasMX. No constituye opinión legal;"
        " valida bases y fechas en la fuente oficial.</rights>",
    ]
    for rec in entries:
        link = f"{SITE_URL}licitacion/{quote(rec['id'], safe='')}"
        summary = ". ".join(
            p
            for p in (
                f"{SOURCES[rec['fuente']]} · {buyers.get(rec['comprador_id'], '')}",
                rec.get("numero") or "",
                names.get(rec["categoria"], ""),
                f"Apertura: {rec['apertura'][:16].replace('T', ' ')}"
                if rec.get("apertura")
                else "",
                rec.get("entidad") or "",
            )
            if p
        )
        lines += [
            "  <entry>",
            f"    <title>{escape(rec['titulo'])}</title>",
            f'    <link rel="alternate" href={quoteattr(link)}/>',
            f"    <id>{TAG_PREFIX}{escape(rec['id'])}</id>",
            f"    <updated>{_updated(rec)}</updated>",
            f"    <category term={quoteattr(rec['categoria'])} "
            f"label={quoteattr(names.get(rec['categoria'], rec['categoria']))}/>",
            f"    <summary>{escape(summary)}.</summary>",
            "  </entry>",
        ]
    lines.append("</feed>")
    return "\n".join(lines) + "\n"


def all_feeds(
    open_recs: list[dict[str, Any]], names: dict[str, str], buyers: dict[str, str]
) -> dict[str, str]:
    feeds = {
        "feed.xml": render(
            open_recs,
            title="SupplySense · convocatorias abiertas",
            subtitle="Compras públicas de México: ComprasMX, CFE y PEMEX, con liga a la fuente.",
            path="data/feed.xml",
            names=names,
            buyers=buyers,
        )
    }
    feeds["feeds/energia.xml"] = render(
        [r for r in open_recs if r.get("sector") == "energia"],
        title="SupplySense · energía y O&G",
        subtitle="Convocatorias abiertas de CFE, PEMEX y el sector energía.",
        path="data/feeds/energia.xml",
        names=names,
        buyers=buyers,
    )
    for fuente, label in SOURCES.items():
        feeds[f"feeds/{fuente}.xml"] = render(
            [r for r in open_recs if r["fuente"] == fuente],
            title=f"SupplySense · {label}",
            subtitle=f"Convocatorias abiertas de {label}.",
            path=f"data/feeds/{fuente}.xml",
            names=names,
            buyers=buyers,
        )
    for codigo, nombre in names.items():
        feeds[f"feeds/{codigo}.xml"] = render(
            [r for r in open_recs if r["categoria"] == codigo],
            title=f"SupplySense · {nombre}",
            subtitle=f"Convocatorias abiertas de {nombre.lower()}.",
            path=f"data/feeds/{codigo}.xml",
            names=names,
            buyers=buyers,
        )
    return feeds
