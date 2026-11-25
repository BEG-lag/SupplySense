# SupplySense

<p><b>English</b> · <a href="README.es.md">Español</a></p>

**Mexican government tenders, next to what was already paid for the same thing.** Every
morning SupplySense reads every open federal call for tender on ComprasMX, plus CFE and PEMEX,
and matches them against 300,000+ awards: who won, at what price and for which buyer. Energy
and oil & gas is its featured vertical. Every record links to its official source.

**Site:** [beg-lag.github.io/SupplySense](https://beg-lag.github.io/SupplySense/) (in Spanish) ·
**Feed:** [`feed.xml`](https://beg-lag.github.io/SupplySense/data/feed.xml) ·
**Sources:** [`docs/fuentes.md`](docs/fuentes.md)

## Contents

| # | Section | Status |
|---|---|---|
| 1 | [What it does](#1-what-it-does) | GREEN |
| 2 | [Sources](#2-sources) | GREEN (state-funded purchases: AMBER) |
| 3 | [How it works](#3-how-it-works) | GREEN |
| 4 | [Data and privacy decisions](#4-data-and-privacy-decisions) | GREEN |
| 5 | [Run it locally](#5-run-it-locally) | GREEN |
| 6 | [Limits](#6-limits) | AMBER |
| 7 | [License and notice](#7-license-and-notice) | GREEN |

## 1. What it does

- **Search open tenders** by what you sell, filtering by sector, source, buyer, state,
  category and status. Filters live in the URL, so a search can be shared.
- **Tender detail**: clarification meeting, bid opening and award dates, buyer, link to the
  source and, unique to SupplySense, **what has been paid in its category** and **which similar
  procedures were already awarded, to whom and for how much**.
- **Prices by category** (35, in three groups: energy and oil & gas, health and general):
  percentiles (P5 to P95) of 300,000+ awards, yearly series, market
  concentration (HHI) and a comparator to place an amount. It does not claim a "probability of
  winning".
- **Winners, companies and buyers**: recent awards, each company's history and who each agency
  buys from.
- **Saved searches** in the browser, no account needed, with "new since your last visit", plus
  **Atom feeds** per source and category.

## 2. Sources

| Source | Status | What it adds |
|---|---|---|
| CFE, Micrositio de Concursos | GREEN | ~115,000 procedures since 2015 with status, winner and amount; opening and award dates for open ones |
| PEMEX, open tenders | GREEN | ~12,000 notices by segment; PEMEX publishes no deadline, amount or winner |
| ComprasMX open data | GREEN | Every 2025 and 2026 procedure (~180,000) and contract (~220,000) of the federal government, and of states and municipalities spending federal funds |
| FIX exchange rate | GREEN | From [indicadores-mx](https://github.com/BEG-lag/indicadores-mx), for USD contracts |
| State and municipal purchases with their own funds | AMBER | Local portals not integrated yet |

Endpoints, formats and quirks are documented in [`docs/fuentes.md`](docs/fuentes.md) (Spanish).

## 3. How it works

```
GitHub Actions (06:30 Mexico City)
  → supplysense update   reads CFE, PEMEX, ComprasMX and FIX, each source isolated
  → data/*.jsonl         CFE and PEMEX, monthly, git-versioned
  → data/vistos/*.tsv    ComprasMX: only when each record was first seen (files live in cache)
  → supplysense build    rules, unified state names, DuckDB percentiles
  → web/public/data      JSON for the site and Atom feeds
  → Vite + React         static site on GitHub Pages
```

- **No server or online database.** The site is static: no login, API or keys to protect.
- **Isolated sources with a brake.** A failing source keeps its last good data; a response with
  less than 70% of the stored records is rejected. The workflow fails, and GitHub emails, when a
  source has been failing for 3 days.
- **Readable rules.** Sector buyers, context words, categories, statuses and manual corrections
  live in [`reglas/`](reglas/) as CSV and are applied at build time, so changing a rule never
  requires re-downloading.
- **Tests.** `pytest` for sources (fixtures), normalization, rules, storage, build and the real
  dataset; `vitest` for dates, search and percentiles on the site; `ruff` in CI.

## 4. Data and privacy decisions

- **Winners** are public by law and shown as the source publishes them.
- **RFC (tax ID)** is shown only for companies. An individual's RFC encodes their birth date and
  is never stored; generic RFCs for foreign suppliers are never used as keys.
- **Public officials**: the name and email of the official operating each notice (ComprasMX) and
  PEMEX's contact are not stored.
- **Estimated statuses** are flagged with an asterisk: a PEMEX notice is treated as open for 30
  days, and a "current" CFE tender whose bid opening already passed is shown as under evaluation.
- **Outlier amounts** (above the category's P99 or below MXN 10,000) are excluded from prices. USD
  contracts are converted with the FIX rate of the signing date.

## 5. Run it locally

```bash
uv sync
uv run supplysense update          # reads the sources (about 2 minutes)
uv run supplysense build           # writes web/public/data
cd web && npm install && npm run dev
```

Tests: `uv run pytest`, `uv run ruff check .`, `cd web && npm test`.

## 6. Limits

- Category classification is keyword-based: a guide, not ground truth.
- A CFE amount is per procedure and may cover several line items or winners.
- ComprasMX covers 2025 and 2026; the longest price history is CFE's (since 2015).
- The build reads ~530,000 records: about 4 minutes and 3.5 GB of memory.
- The 30-day "open" window for PEMEX is an assumption; confirm dates in SISCeP.

## 7. License and notice

Code under the [MIT](LICENSE) license. Data is public information from CFE, PEMEX and Mexico's
Ministry for Anti-Corruption and Good Government (ComprasMX), cited with its source.

This project is not legal or tax advice. Before bidding, check the terms, dates and
requirements at the official source.

Made by [Benjamín Esponda García](https://pivotek.mx).
