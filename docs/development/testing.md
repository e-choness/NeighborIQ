# Testing

| Suite | Location | Needs |
|---|---|---|
| API | `services/api/tests` | Postgres (PostGIS), Redis optional |
| Ingestion | `services/ingestion-worker/tests` | Postgres; network-free (fixtures and local files) |
| Insights | `services/insights-worker/tests` | Postgres |
| Shared | `shared/tests` | Postgres; a second database for migration tests |
| Frontend | `frontend` | `npm run build` (type check + build) |

## In Docker

```bash
docker compose --profile test up --build --abort-on-container-exit \
  test-api test-ingestion-worker test-insights-worker test-data-layer test-frontend-build
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
OpenAPI check, the three service suites and the shared suite against PostGIS, the frontend build, and a Trivy
scan. Images are pushed to GHCR only from `main`.

## Writing tests

- API tests use FastAPI's `TestClient`. Fixtures in `services/api/tests/conftest.py` sign up users and admins
  and return their bearer headers.
- Test behaviour through public interfaces: HTTP for the API, the CLI or the task functions for the
  workers, and plain functions for `shared/analytics`.
- Open-data loaders are tested with small files in the portal's real column layout, including a
  wrong-column case that must raise `SchemaError`.
- Tests clean up the rows they create. Only the migration tests may drop tables, and only in their own
  database.
