# 0004 — Keep Celery and Redis for background jobs

**Status:** Accepted (2026-09)

## Context

Alternatives considered: Dramatiq, arq, Taskiq (asyncio-native), Hatchet and Temporal (durable workflows),
and Postgres-backed queues (Procrastinate, PGMQ). The existing jobs are coarse (loads, recomputes,
retraining, nightly summaries) and idempotent. The team already runs Celery, and its failure modes are
well documented.

## Decision

Keep Celery with Redis as the broker. Fix what was broken instead of switching:

- register tasks explicitly (`include=[…]`), because autodiscovery had registered none;
- route by name to per-worker queues (`scraper`, `insights`, `narratives`);
- run one beat per worker type;
- set `worker_max_tasks_per_child=1` on the ingestion worker (Scrapy/Twisted reactor);
- have the API send jobs by task name, never importing worker code.

## Consequences

- No migration cost, and the tooling is mature (Flower, retries, rate limits).
- Redis is one more service, but it only holds queued jobs, so losing it loses no user data.
- Since 0.4 the broker runs Valkey, the BSD-licensed Redis fork; Celery talks to it over the same protocol.
- If workflows grow multi-step with long waits (e.g. multi-day feed reconciliation), revisit with a durable
  workflow engine rather than chaining Celery tasks.
