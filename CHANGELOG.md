# Changelog

Notable changes to NeighborIQ. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
the API version is the one in [`services/api/openapi.json`](services/api/openapi.json).

## [Unreleased]

### Changed

- Glass redesign with a map-first shell: one persistent map behind every screen and content in docked glass
  sheets (left: Home, Explore, Analyze; right: Listing; centre: Portfolio, Data). Desktop gets a navigation
  rail and a top bar that holds the city; phones get a tab bar and a three-snap bottom sheet. Listing is
  split into Value / Cash flow / History / Area tabs (`?tab=`), with its comparables highlighted on the map;
  Analyze pins its result in the sheet. New sage palette, Italiana display type for titles.
- Maps show a street basemap by default (OpenFreeMap, OpenStreetMap data), tinted to the palette, with a
  data-only fallback when it can't load. Self-hosted PMTiles still takes precedence (`VITE_PMTILES_URL`);
  `VITE_BASEMAP=none` keeps the plain background.
- `/admin` is now the Admin tab of the Data screen (`/data?tab=admin`).
- README and docs site follow the app's look: an animated walkthrough, new screenshots, banners, social card
  and logo (sage hexagon map, glass panels, Italiana, Geist, Lucide icons), and the docs theme in the same
  tokens. New NeighborIQ mark (a honeycomb of hexagon columns) as the docs logo and the app favicon. All
  media now lives in `docs/public/media`, and the social card is animated like the README banner.
- API tests delete the listings they create, so a test run against the development database no longer
  leaves a "Testville" city on the map.

### Added

- Playwright browser tests (`frontend/e2e`, `docker compose --profile test run --rm test-frontend-e2e`),
  ESLint (`npm run lint`) and a palette validator (`npm run check:palette`).
- CI: read-only token by default, duplicate PR runs cancelled, frontend lint + palette check + Playwright
  (report uploaded on failure), and the missing image scan after `build` (Grype, HIGH/CRITICAL with a fix
  fails the job, SARIF to code scanning). Ruff and pip-audit move to `requirements-dev.txt` so Dependabot
  bumps them; pip and npm caches in lint and audit.
- Dependencies: uvicorn 0.54, PyJWT 2.15.1, openai 3.20, pytest-mock 3.16, @types/node 24.19, mermaid 11.17;
  nginx pinned to 1.30.5-alpine by digest. Held: SQLAlchemy 2.1 (own PR), redis 8 (kombu 5.6.2 still
  requires < 6.5), TypeScript 7 (vue-tsc), VitePress 2 (alpha).
- DigitalOcean App Platform spec (`.do/app.yaml`): static SPA, API, private Valkey, two workers with
  their schedulers, and migrate/bootstrap jobs, on a managed PostgreSQL with PostGIS. Guide in
  docs/DEPLOYMENT.md.
- `DATABASE_URL` accepts any libpq form (`postgres://`, `postgresql://`, with `sslmode`) and is converted for
  asyncpg and psycopg2, as managed platforms provide it.

### Security

- Upgraded every dependency to its latest release. The previous pins carried 33 published advisories:
  python-multipart (12), PyJWT (8), cryptography (7), Scrapy (6). `pip-audit` and `npm audit` now report
  none. Notable pins: FastAPI 0.141, Pydantic 2.13, SQLAlchemy 2.0.54, Celery 5.6, Scrapy 2.19,
  cryptography 50, PyJWT 2.15, XGBoost 3.4, numpy 2.5.
- Passwords are hashed with Argon2id (pwdlib) instead of passlib + bcrypt (passlib is unmaintained and
  held bcrypt at 3.2). Existing bcrypt hashes still verify, with passlib's 72-byte behaviour, and are
  upgraded at the next sign-in.
- CI actions are pinned to commit SHAs. The Trivy job is replaced by `pip-audit` and `npm audit`, after the
  March 2026 compromise of `aquasecurity/trivy-action` tags; the CI referenced that action by tag.
- Images contain no compilers or extra OS packages (wheels only) and run as a non-root user.
- Docs site: Vite forced to 6.4.3 under VitePress 1.6.4, clearing four dev-server advisories.

### Changed

- Runtimes: Python 3.14 (code stays 3.13-compatible), Node 24 LTS, PostgreSQL 18 + PostGIS 3.6
  (**existing databases need a dump/restore**, see docs/operations.md), Valkey 9 as the Celery broker in
  place of Redis 7, TypeScript 6.
- The insights worker uses the CPU-only XGBoost build on Linux, which shrinks its image from 1.55 GB to
  764 MB.
- Dependabot also updates Compose image tags and the shared test requirements.

### Fixed

- nginx now re-resolves the `api` service, so restarting or scaling the API no longer leaves the frontend
  returning 502 until nginx restarts.
- The API container's Compose healthcheck called `curl`, which is no longer in the image.

### Added

- Documentation site (VitePress) published to GitHub Pages. It includes an interactive cash-flow
  calculator, kept in sync with the Python implementation by shared fixtures, and an HTTP API reference
  generated from the OpenAPI snapshot.
- Animated README banner in light and dark variants, and a social preview card.
- Issue and pull-request templates, security policy, Dependabot configuration.
- `scripts/smoke-test.sh` checks a running stack (web app, API health, listings, markets, calculator
  defaults, data sources).

### Changed

- **Licence:** NeighborIQ is now proprietary, all rights reserved. Using, copying, modifying, hosting or
  distributing it requires written permission. Copies obtained under MIT (up to `4c7146f`) or FSL-1.1-ALv2
  (up to `50c9118`) keep those terms.
- Migrations squashed into `0001_baseline` (the same schema, verified column-for-column). Databases
  at the old head `005_open_data` are adopted automatically on the next upgrade.
- `shared/` now holds only code used by more than one deployable: models, database sessions, analytics.
  Token, password and schema code used only by the API moved into `services/api/app`. Shared-layer
  tests and their Docker image moved to `shared/tests` (Compose service `test-shared`).
- Partner feeds are fetched with an honest `NeighborIQ/…` user agent instead of rotating browser strings.

### Fixed

- `0002_integrity` adds the foreign keys the legacy migrations never created: deleting a listing or user now
  removes its price history, amenity links and refresh tokens instead of leaving orphans. Orphans already
  present are removed first.
- `auth_users.email` is now unique in the database, not only in application code.
- Alembic log output (the format string was printed literally) and the missing `script.py.mako` template,
  without which `alembic revision` failed.

### Removed

- Dead code: the unused Redis cache layer, a second session factory and settings class, unused DTOs and
  schemas, the no-op coordinate pipeline, the stale insights-worker OpenAPI file, and the deployment
  script for the retired seven-service stack.
- Redundant indexes that duplicated another index or a unique constraint.
- The retired lavender banners and the old modernisation plan (both remain in git history).

## [0.3.0] — 2026-09

### Added

- Canadian listing model (postal code, property type, sq ft, condo fee, property tax, status, source,
  synthetic flag) and price history.
- Fair value from comparable listings, with comps, a range and a confidence level.
- Cash-flow calculator under Canadian rules: semi-annual compounding, CMHC premiums, land transfer tax
  by province, cap rate, cash-on-cash, DSCR, break-even rent.
- Open-data loaders: neighbourhood boundaries, assessment rolls, 2021 census, GTFS transit, crime,
  building permits, Bank of Canada rates, StatCan new housing price index. Loads are logged with licence
  and attribution.
- Portfolio with notes and saved cash-flow assumptions.
- Redesigned UI: 3D hexagon market map, listing analysis, deal analyzer for any address, explore view,
  data provenance page.
- Production overlay with Caddy (automatic HTTPS); Ruff; CI with API contract check.

### Changed

- Seven HTTP services and a gateway consolidated into one API plus two Celery workers.
- Alembic owns the schema, applied by a one-shot `migrate` service.
- XGBoost estimates are backtested and hidden unless `ML_PREDICTIONS_ENABLED=1`.
- Market narratives only use computed statistics.
- License file updated (MIT at the time, 2025–2026), with a NOTICE file for third-party data licences.

### Removed

- The Lianjia scraper and Chinese-market data.

### Security

- Admin routes require the admin role, verified from the token.
- Services no longer trust identity headers; every protected route verifies the JWT itself.
- Refresh tokens rotate on every use and are stored hashed.
- Partner feed URLs are limited to an allow-list to prevent SSRF.
- Postgres, Redis and the API are no longer published on public interfaces.

## [0.2.0] — 2026-06

Microservices phases 1–7: auth, house, search, portfolio, AI insights and scraper services behind a
gateway; Vue frontend; CI/CD. Superseded by 0.3.0. The plan for that design is in git history
(`docs/history/MODERNIZATION_PLAN.md` as of commit 47c4131).
