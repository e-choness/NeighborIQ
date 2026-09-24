<p align="center">
  <a href="https://e-choness.github.io/NeighborIQ/">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="images/banner-dark.svg">
      <img alt="NeighborIQ — rental-property analysis for small investors in Canadian cities" src="images/banner-light.svg" width="100%">
    </picture>
  </a>
</p>

<p align="center">
  <a href="https://github.com/e-choness/NeighborIQ/actions/workflows/ci-cd.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/e-choness/NeighborIQ/ci-cd.yml?branch=main&label=CI&style=flat-square"></a>
  <a href="https://github.com/e-choness/NeighborIQ/actions/workflows/docs.yml"><img alt="Docs" src="https://img.shields.io/github/actions/workflow/status/e-choness/NeighborIQ/docs.yml?branch=main&label=docs&style=flat-square"></a>
  <a href="https://e-choness.github.io/NeighborIQ/reference/api"><img alt="API version" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fe-choness%2FNeighborIQ%2Fmain%2Fservices%2Fapi%2Fopenapi.json&query=%24.info.version&label=API&color=0d9488&style=flat-square"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-0d9488?style=flat-square"></a>
  <a href="https://github.com/astral-sh/ruff"><img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square"></a>
  <a href="https://github.com/e-choness/NeighborIQ/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/e-choness/NeighborIQ?style=flat-square"></a>
  <br>
  <img alt="Python 3.11" src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="PostgreSQL + PostGIS" src="https://img.shields.io/badge/PostgreSQL_+_PostGIS-15-4169E1?style=flat-square&logo=postgresql&logoColor=white">
  <img alt="Celery" src="https://img.shields.io/badge/Celery-Redis-37814A?style=flat-square&logo=celery&logoColor=white">
  <img alt="Vue 3.5" src="https://img.shields.io/badge/Vue-3.5-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white">
  <img alt="MapLibre GL" src="https://img.shields.io/badge/MapLibre_GL-6-396CB2?style=flat-square&logo=maplibre&logoColor=white">
</p>

<p align="center">
  <a href="https://e-choness.github.io/NeighborIQ/"><b>Documentation</b></a> ·
  <a href="https://e-choness.github.io/NeighborIQ/guide/calculator">Try the cash-flow calculator</a> ·
  <a href="https://e-choness.github.io/NeighborIQ/reference/api">API reference</a> ·
  <a href="#quick-start">Quick start</a>
</p>

---

**NeighborIQ helps a small investor screen a rental property in a Canadian city.** For any listing, or any
property you found elsewhere, it answers three questions:

| | Question | How |
|---|---|---|
| 1 | **Is the price fair?** | Asking price against the median $/sq ft of the nearest comparable listings, with the comps on a map and a confidence level |
| 2 | **Will it cash-flow?** | Monthly cash flow under Canadian rules (semi-annual compounding, CMHC insurance, land transfer tax), with every assumption editable |
| 3 | **What is the neighbourhood like?** | Census income and tenure, transit frequency, crime, new supply and assessed values, from public open data, each with source and date |

![3D map of gross rental yield across Toronto](docs/images/home.png)

<table>
  <tr>
    <td width="50%"><img src="docs/images/listing.png" alt="Listing: fair value against comparables, cash flow, price history"><br><sub><b>Listing</b>: fair value with its comps, editable cash flow, price history</sub></td>
    <td width="50%"><img src="docs/images/analyze.png" alt="Analyze any property"><br><sub><b>Analyze</b>: the same analysis for any address, pre-filled from the assessment roll</sub></td>
  </tr>
</table>

> [!NOTE]
> **What is real.** The app runs on **synthetic demo listings** out of the box. They are labelled everywhere, so
> no data licence is needed. Real listings need a licensed feed (for example CREA's DDF® through a brokerage);
> NeighborIQ does not scrape MLS® or REALTOR.ca. Neighbourhood data, rates and transit come from public open
> data you load with one command. See [Data sources](docs/data-sources.md) and [Methodology](docs/methodology.md).

## Quick start

Requires Docker with Compose v2.

```bash
git clone https://github.com/e-choness/NeighborIQ.git && cd NeighborIQ
cp .env.example .env            # set ADMIN_EMAILS to your email
docker compose up -d            # migrates the schema and loads demo data on first start
```

| URL | What |
|---|---|
| http://localhost | Web app. Sign up with your `ADMIN_EMAILS` address to get the Admin page |
| http://localhost:8000/docs | Interactive API (Swagger) |

Then load open data for a city from the Admin page, or run
`docker compose exec ingestion-worker python -m ingestion opendata --city Vancouver`.

<details>
<summary><b>Production</b>: one server, automatic HTTPS</summary>

```bash
# .env: DOMAIN, POSTGRES_PASSWORD, ADMIN_EMAILS, JWT_PRIVATE_KEY/JWT_PUBLIC_KEY (see docs/DEPLOYMENT.md)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Caddy obtains certificates for `$DOMAIN`; nothing but ports 80/443 is exposed. See
[Deployment](docs/DEPLOYMENT.md) and [Operations](docs/operations.md).

</details>

## How it works

```mermaid
flowchart LR
    Browser --> Web["frontend<br/>Vue SPA + nginx"]
    Web -->|/api| API["api<br/>FastAPI"]
    API --> PG[("PostgreSQL<br/>+ PostGIS")]
    API -->|enqueue| Redis[("Redis")]
    Redis --> IW["ingestion-worker<br/>open data · OSM · feeds"]
    Redis --> AW["insights-worker<br/>yields · model · summaries"]
    IW --> PG
    AW --> PG
```

One HTTP service handles everything request/response. The two Celery workers carry the batch work that
actually needs to scale. The reasoning is in the [architecture overview](docs/architecture/overview.md) and
[ADR 0001](docs/adr/0001-one-api-two-workers.md).

<details>
<summary><b>Stack</b></summary>

| Layer | Choice |
|---|---|
| API | Python 3.11, FastAPI, SQLAlchemy 2, Pydantic 2, RS256 JWT in HttpOnly cookies |
| Data | PostgreSQL 15 + PostGIS, Alembic migrations |
| Jobs | Celery + Redis; Scrapy for licensed partner feeds |
| Analytics | Comparable-listing valuation, Canadian cash flow, XGBoost with a backtested error band (off by default) |
| Frontend | Vue 3.5, Vite 8, Tailwind CSS v4, Reka UI, Pinia Colada, MapLibre GL + Protomaps PMTiles, H3 |
| Docs | VitePress, published to GitHub Pages |
| Tooling | Ruff, pytest, vue-tsc, GitHub Actions, Trivy, Caddy |

</details>

## Documentation

The full documentation is at **[e-choness.github.io/NeighborIQ](https://e-choness.github.io/NeighborIQ/)**. It is
built from [`docs/`](docs/), so every page also reads on GitHub:

- **Use it:** [Introduction](docs/guide/index.md) · [Methodology](docs/methodology.md) · [Data sources](docs/data-sources.md)
- **Run it:** [Deployment](docs/DEPLOYMENT.md) · [Operations](docs/operations.md)
- **Build on it:** [Architecture](docs/architecture/overview.md) · [Data model](docs/architecture/data-models.md) ·
  [Frontend](docs/frontend/overview.md) · [Development setup](docs/development/getting-started.md) ·
  [Testing](docs/development/testing.md) · [Decisions](docs/adr/README.md)

## Status

- [x] Listing search, comparable-listing fair value, Canadian cash flow, portfolio with saved assumptions
- [x] Open-data loaders for boundaries, assessment rolls, census, GTFS transit, crime, permits and rates (6 cities + national)
- [x] Single API + two workers, Alembic-owned schema, CI with lint, tests and an API contract check
- [ ] Verify every open-data source against its live portal (only Bank of Canada is verified so far)
- [ ] Replace placeholder rent benchmarks with the official CMHC table
- [ ] Fuzzy address search (`pg_trgm`), see [ADR 0002](docs/adr/0002-search-in-postgres.md)
- [ ] A licensed listing feed

See the [changelog](CHANGELOG.md) for what changed and when.

## Contributing

Issues and pull requests are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md). To report a security issue,
see [SECURITY.md](SECURITY.md).

## License

Code: [MIT](LICENSE). Third-party data is licensed by its publishers; see [NOTICE](NOTICE).
Estimates rely on asking prices and public data. They are not appraisals or financial advice.
