# Testing

| Suite | Location | Needs |
|---|---|---|
| API | `services/api/tests` | Postgres (PostGIS), Redis optional |
| Ingestion | `services/ingestion-worker/tests` | Postgres; network-free (fixtures and local files) |
| Insights | `services/insights-worker/tests` | Postgres |
| Shared | `shared/tests` | Postgres; a second database for migration tests |
| Frontend | `frontend` | `npm run build` (type check + build) |
| Docs | `docs` | `npm run build`: cash-flow parity check, dead-link check, build |

## In Docker

```bash
docker compose --profile test up --build --abort-on-container-exit \
  test-api test-ingestion-worker test-insights-worker test-shared test-frontend-build
```

## On the host

With Postgres running and migrated (see [Getting started](getting-started.md)):

```bash
export DATABASE_URL=postgresql+asyncpg://root:root@localhost:5432/house_discovery
export MIGRATIONS_DATABASE_URL=postgresql+asyncpg://root:root@localhost:5432/neighboriq_migration_test
export SECURE_COOKIES=0 REDIS_URL=redis://localhost:6379/1 CELERY_BROKER_URL=redis://localhost:6379/2

(cd services/api              && PYTHONPATH=../..:. pytest -q)
(cd services/ingestion-worker && PYTHONPATH=../..:. DATA_DIR=../../data pytest -q)
(cd services/insights-worker  && PYTHONPATH=../..:. pytest -q)
PYTHONPATH=. pytest -q shared/tests
```

The migration tests run `alembic downgrade base` and `upgrade head` only against `MIGRATIONS_DATABASE_URL`
(default `neighboriq_migration_test`, which they create if it is missing). They never touch the application
database.

## Lint, format, API contract

```bash
pip install ruff
ruff check . && ruff format --check .          # config in pyproject.toml
python scripts/export_openapi.py --check       # fails if services/api/openapi.json is stale
python scripts/export_openapi.py               # regenerate after changing endpoints
```

CI ([`.github/workflows/ci-cd.yml`](../../.github/workflows/ci-cd.yml)) runs the same steps: lint and
OpenAPI check, the three service suites and the shared suite against PostGIS, the frontend build, and a
dependency audit (`pip-audit` on every requirements file, `npm audit` for the frontend and docs). Images are pushed to GHCR only from `main`. [`docs.yml`](../../.github/workflows/docs.yml) builds the
documentation site on pull requests and deploys it to GitHub Pages from `main`.

## Calculator parity

The docs site runs the cash-flow calculator in the browser, using a JavaScript port of
`shared/analytics/cashflow.py`. `docs/.vitepress/theme/lib/cashflow.fixtures.json` pins both implementations:

- `shared/tests/test_cashflow_fixtures.py` fails if the Python output changes;
- `docs/scripts/check-cashflow.mjs` (run by `npm run build` in `docs/`) fails if the JavaScript disagrees.

After an intended change to the maths, update the JavaScript port, then regenerate the fixtures with
`python scripts/export_cashflow_fixtures.py`.

## Browser tests

Playwright drives a production build (`vite build --mode e2e`, served by `vite preview`) with the API mocked
from demo-data fixtures in `frontend/e2e/fixtures`, at 1440×900 and on an iPhone 14 viewport:

```bash
docker compose --profile test run --rm test-frontend-e2e
CI_NETWORK=1 docker compose --profile test run --rm test-frontend-e2e   # also load the hosted basemap
```

The suites cover the map (full-bleed canvas, hex layer, camera refit after a listing), Home → best yield →
Listing → Cash flow slider → Save → Portfolio, and Explore → Listing → back with the filters kept. The HTML
report and failure traces land in `frontend/playwright-report/` and `frontend/test-results/`.

## Screenshots and walkthrough

Everything visual lives in `docs/public/media` (the docs site serves it as `/media/*`, the README links to it). The screenshots and walkthrough are generated from a running stack with demo data
(`docker compose up -d`), in the browser-test image:

```bash
# Screenshots: docs/public/media/{home,explore,listing,analyze}.png plus -light / -phone variants
docker run --rm -v "$PWD:/repo" -w /repo/frontend -e BASE_URL=http://host.docker.internal \
  neighboriq-test-frontend-e2e node scripts/docs-screenshots.mjs

# Walkthrough video (REDUCED_MOTION=1 for the README GIF: a still camera keeps it small)
docker run --rm -v "$PWD:/repo" -w /repo/frontend -e BASE_URL=http://host.docker.internal \
  neighboriq-test-frontend-e2e node scripts/walkthrough.mjs
docker run --rm -v "$PWD:/repo" -w /repo --entrypoint ffmpeg jrottenberg/ffmpeg:7.1-alpine -y \
  -i frontend/test-results/walkthrough/walkthrough.webm -vf scale=1280:-2 -c:v libx264 -crf 26 \
  -pix_fmt yuv420p -movflags +faststart -an docs/public/media/walkthrough.mp4
docker run --rm -v "$PWD:/repo" -w /repo --entrypoint ffmpeg jrottenberg/ffmpeg:7.1-alpine -y \
  -i frontend/test-results/walkthrough/walkthrough.webm -fps_mode vfr -loop 0 \
  -vf "fps=8,mpdecimate=hi=64*24:lo=64*8:frac=0.2,scale=840:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" \
  docs/public/media/walkthrough.gif
```

The banners, social card (animated SVG, plus the still `og.png` crawlers use) and the logo come from `docs/scripts/banner.mjs` (`npm run banner` in `docs/`); it also writes the app's favicon from the same mark.

## Writing tests

- API tests use FastAPI's `TestClient`. Fixtures in `services/api/tests/conftest.py` sign up users and admins
  and return their bearer headers.
- Test behaviour through public interfaces: HTTP for the API, the CLI or the task functions for the
  workers, and plain functions for `shared/analytics`.
- Open-data loaders are tested with small files in the portal's real column layout, including a
  wrong-column case that must raise `SchemaError`.
- Tests clean up the rows they create. Only the migration tests may drop tables, and only in their own
  database.
