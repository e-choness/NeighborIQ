# 0001 — One API and two workers

**Status:** Accepted (2026-09)

## Context

NeighborIQ had seven HTTP services (gateway, auth, house, search, portfolio, AI insights, scraper). They all
shared one PostgreSQL database and a `shared/` Python package, and they were released together. The split
cost a lot and bought little:

- Services trusted `X-User-*` headers set by the gateway. Any service reachable directly could be
  impersonated.
- Port and route wiring drifted: containers listened on different ports than Compose and the gateway
  expected, and some routes were shadowed.
- Every request took an extra proxy hop, and there were seven images, seven test setups and seven sets of
  docs.
- Nothing could be deployed on its own, because the schema and `shared/` were common.

The components were ranked by how likely each is to need independent scaling (see
[architecture overview](../architecture/overview.md#why-one-api-and-two-workers)). Ingestion is bursty,
network-bound and handles large files. Insights compute is CPU and memory heavy with large dependencies. Every
request/response domain is light per request.

## Decision

- Merge auth, listings, search, portfolio, insights reads, open-data reads and admin into one FastAPI app
  (`services/api`), one router per domain. JWTs are verified in-process on every protected route. There is
  no gateway.
- Keep two Celery workers as separate deployables: `ingestion-worker` and `insights-worker`.
- Share code only through `shared/` (models, database sessions, analytics), so a router can later be
  extracted without untangling imports.

## Consequences

- One image and one test suite for all HTTP code; the API scales by replicas.
- The identity-header trust problem is gone by construction.
- A failure in a heavy job cannot take the API down, because jobs run in other processes.
- Extracting a domain later (search is the most likely candidate, see [0002](0002-search-in-postgres.md))
  means moving a router and giving it its own deployable. Any schema split would be a separate decision.
