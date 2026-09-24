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
gateway; Vue frontend; CI/CD. Superseded by 0.3.0. Its plan is kept in
[docs/history](docs/history/MODERNIZATION_PLAN.md).

