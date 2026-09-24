# 0002 — Search stays in PostgreSQL until a measured need

**Status:** Accepted. The choice of external engine is open, pending the triggers below.

## Context

Investors search mostly by structure, not by text: city, type, bedrooms, price, yield, price cut, map
bounds. Those are indexed SQL filters and sorts. Free-text search covers only titles, neighbourhoods,
streets and postal codes (`GET /houses/search`, `ILIKE`). The old design had a separate search service with
no engine behind it: the same Postgres queries, plus an extra hop.

## Decision

Search runs in the API against PostgreSQL. The steps below are taken in order, each only when a trigger fires.

1. **Now:** B-tree indexes on the filter columns, PostGIS/bounding-box filters, `ILIKE` for the text box.
2. **Typo tolerance or ranking needed, or `ILIKE` slower than ~50 ms at p95:** `pg_trgm` GIN indexes on
   address and neighbourhood (fuzzy matching), plus a generated `tsvector` column with a GIN index for
   ranked full-text search. No new infrastructure.
3. **Facets with counts on every keystroke, instant search, synonyms, or several million documents:** add a
   dedicated engine fed from Postgres (outbox table or periodic sync from the ingestion worker). Postgres
   stays the source of truth. Candidates, all single-binary and self-hostable:
   - **Meilisearch** — simplest to operate, strong typo tolerance and facets, built-in geo filter and sort.
   - **Typesense** — similar ergonomics, in-memory, built-in HA clustering, geo search.
   - **ParadeDB `pg_search`** — BM25 inside Postgres, so there is no sync to maintain. It requires the
     extension on the database server, which rules out some managed providers.
   - **OpenSearch** — only if analytics or log search also need a cluster.

## Consequences

- No extra service to deploy or keep in sync today.
- Search is behind one router, so moving it to an engine changes one module and adds a sync job.
- Step 3 is a product decision (what users actually type) as much as a scaling one. Record the engine
  chosen in a new ADR.
