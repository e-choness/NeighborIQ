# Changelog

Notable changes to NeighborIQ. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
the API version is the one in [`services/api/openapi.json`](services/api/openapi.json).

## [Unreleased]

### Added
- Documentation site (VitePress) published to GitHub Pages. It includes an interactive cash-flow
  calculator, kept in sync with the Python implementation by shared fixtures, and an HTTP API reference
  generated from the OpenAPI snapshot.
- Animated README banner in light and dark variants, and a social preview card.
- Issue and pull-request templates, security policy, Dependabot configuration.
- `scripts/smoke-test.sh` checks a running stack (web app, API health, listings, markets, calculator
  defaults, data sources).

### Changed
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

The project was re-scoped from a Chinese-market demo to a rental-analysis tool for small investors in
Canada.

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
- Seven HTTP services and a gateway consolidated into one API plus two Celery workers
  ([ADR 0001](docs/adr/0001-one-api-two-workers.md)).
- Alembic owns the schema, applied by a one-shot `migrate` service.
- XGBoost estimates are backtested and hidden unless `ML_PREDICTIONS_ENABLED=1`.
- Market narratives only use computed statistics.
- License file updated (MIT, 2025–2026), with a NOTICE file for third-party data licences.

### Removed
- The Lianjia scraper and Chinese-market data
  ([ADR 0003](docs/adr/0003-open-data-and-synthetic-listings.md)).

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

