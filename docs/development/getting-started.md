# Getting started (development)

## Everything in Docker

```bash
cp .env.example .env
docker compose up -d --build
```

- App: http://localhost (nginx serving the built SPA)
- API docs: http://localhost:8000/docs
- Postgres on `localhost:5432`, Redis on `localhost:6379` (bound to localhost only)

The first start migrates the schema and loads rent benchmarks plus about 800 synthetic listings. Sign up with
the email in `ADMIN_EMAILS` to see the Admin page.

## Frontend with hot reload

Run the backend in Docker and the frontend with Vite (Node ≥ 20.19):

```bash
docker compose up -d api ingestion-worker insights-worker
cd frontend && npm install && npm run dev      # http://localhost:5173, proxies /api to :8000
```

Set `VITE_API_PROXY` to point the dev proxy at another API. `npm run typecheck` runs `vue-tsc`.

## Python services on the host

Python 3.11. The services import `shared/` from the repository root, so put both on `PYTHONPATH`:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r services/api/requirements.txt          # includes shared/requirements.txt
docker compose up -d postgres redis
export DATABASE_URL=postgresql+asyncpg://root:root@localhost:5432/house_discovery
export CELERY_BROKER_URL=redis://localhost:6379/2 SECURE_COOKIES=0
alembic -c migrations/alembic.ini upgrade head

cd services/api
PYTHONPATH=../..:. uvicorn app.main:app --reload --port 8000
```

Workers (each needs its own `requirements.txt` installed):

```bash
cd services/ingestion-worker
PYTHONPATH=../..:. python -m ingestion bootstrap --if-empty
PYTHONPATH=../..:. celery -A tasks.celery_app worker -Q scraper -l info

cd services/insights-worker
PYTHONPATH=../..:. celery -A tasks.celery_app worker -Q insights,narratives -l info
```

## Documentation site

The docs are a VitePress site built from `docs/` and published to GitHub Pages by
[`.github/workflows/docs.yml`](../../.github/workflows/docs.yml) (enable it once under **Settings → Pages →
Source: GitHub Actions**).

```bash
cd docs && npm install
npm run dev        # http://localhost:5173/NeighborIQ/ with hot reload
npm run build      # checks the calculator against the Python fixtures, then builds to .vitepress/dist
npm run banner     # regenerate the README banners and social card
```

Write pages as plain Markdown that also reads on GitHub. Link to source files with relative paths
(`../../services/api`); the build turns links that leave `docs/` into GitHub links. Two pages are generated:
the [API reference](../reference/api.md) from `services/api/openapi.json`, and the
[calculator](../guide/calculator.md) from `docs/.vitepress/theme/lib/cashflow.js`.

## Repository layout

```
services/api/                FastAPI app: app/routers/*, app/security.py, tests/
services/ingestion-worker/   ingestion/ (CLI, seed, writer, OSM, opendata/), scraper/ (feed spider), tasks/
services/insights-worker/    insights/ (features, model, narrative), tasks/
shared/                      models, database sessions, analytics (valuation, cash flow), utils
migrations/                  Alembic revisions
frontend/                    Vue 3 + Vite SPA
data/reference/              rent benchmarks CSV
docs/                        documentation site (VitePress); docs/adr/ for decisions
```

## Where to change things

| Change | Place |
|---|---|
| New endpoint | `services/api/app/routers/<domain>.py`; then `python scripts/export_openapi.py` |
| Valuation or cash-flow maths | `shared/analytics/` (used by both the API and the insights worker) |
| New open-data source | `ingestion/opendata/sources.py` (registry entry + column mapping) |
| Table or column | New Alembic revision in `migrations/alembic/versions/` and the ORM model in `shared/models/` |
| Colours | `frontend/src/theme/palette.ts` and `frontend/src/styles/app.css` |

Next: [Testing](testing.md).
