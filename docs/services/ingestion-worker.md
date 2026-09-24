# ingestion-worker

[`services/ingestion-worker`](../../services/ingestion-worker). A Celery worker on queue `scraper`, plus the
`python -m ingestion` CLI. Every piece of external data enters through it. The same image also runs the
one-shot `migrate` and `bootstrap` services and `ingestion-beat`.

## Layout

| Path | Purpose |
|---|---|
| `ingestion/canonical.py` | Canonical listing format: normalise units and names, validate (required fields, ranges, status) |
| `ingestion/writer.py` | Upsert by `url`, append `house_price_history` when the price changes, refresh community aggregates |
| `ingestion/seed.py` | Deterministic synthetic listings for 5 cities / 32 neighbourhoods (`is_synthetic=1`) |
| `ingestion/benchmarks.py` | Rent benchmarks CSV loader |
| `ingestion/osm.py` | Overpass queries for schools, hospitals and stops; nearest-amenity links |
| `ingestion/opendata/` | Source registry, fetch (cache, retries), tabular/GeoJSON parsing with column mapping, and one loader per kind: areas, assessments, permits, incidents, census, gtfs, indicators |
| `scraper/` | Scrapy spider for licensed partner feeds (JSON/CSV over HTTPS). Its pipelines are dedup → validation → Postgres through `writer` |
| `tasks/` | Celery app, `run_ingestion` and `run_feed` tasks, beat schedule |

## Tasks

| Task | Arguments | Triggered by |
|---|---|---|
| `scraper.tasks.run_ingestion` | `command` (`seed`/`rents`/`osm`/`bootstrap`/`opendata`), `cities`, `sources` | Admin page, beat (rates daily, OSM weekly) |
| `scraper.tasks.run_feed` | `feed_url`, `source` | Admin page, beat if `LISTING_FEED_URL` is set |

After writing listings, the worker enqueues `ai_insights.tasks.compute_insights` for the affected IDs.
`worker_max_tasks_per_child=1` gives each Scrapy crawl a fresh Twisted reactor.

## CLI

```bash
python -m ingestion seed [--per-neighbourhood 25] [--cities Toronto,Calgary]
python -m ingestion import FILE.csv|FILE.json [--source NAME]
python -m ingestion rents [PATH]
python -m ingestion osm [--cities …]
python -m ingestion bootstrap [--if-empty]
python -m ingestion opendata --list | --city CITY | --sources KEY[,KEY] [--url URL | --file PATH]
```

## Adding an open-data source

1. Add a `Source` to `ingestion/opendata/sources.py` with a `kind`, licence, attribution, a `url` or
   `resolver`, and a column `mapping` that lists candidate names for each field.
2. Add a test in `tests/test_opendata.py` with a few rows in the portal's real layout.
3. Run it once live and set `verified=True` when it loads cleanly.
4. Add it to [Data sources](../data-sources.md) and to [NOTICE](../../NOTICE) if it requires attribution.

## Configuration

`DATABASE_URL`, `CELERY_BROKER_URL`, `DATA_DIR` (reference files and download cache), `LISTING_FEED_URL`.
