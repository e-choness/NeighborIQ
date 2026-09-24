# Operations

Day-to-day tasks for someone running NeighborIQ. Commands assume Docker Compose from the repository root; add
`-f docker-compose.yml -f docker-compose.prod.yml` in production.

## Startup order

`postgres` and `redis` start first. Then `migrate` runs `alembic upgrade head` and exits. `bootstrap` loads
rent benchmarks and demo listings only when `house_houses` is empty (`--if-empty`), then exits. After that
come `api`, the workers, the beats and `frontend`. A failed `migrate` blocks everything that depends on the
database. Check it with `docker compose logs migrate`.

## Schema changes

```bash
# create a revision (from a dev shell with DATABASE_URL set)
alembic -c migrations/alembic.ini revision -m "add something"
# apply on a running stack
docker compose run --rm migrate
```

Write migrations by hand, in the style of `005_open_data.py`, and include a `downgrade`. Services do not create
tables in Compose (`AUTO_CREATE_SCHEMA=0`).

## Admins

Admin role is assigned at sign-up to emails listed in `ADMIN_EMAILS` (comma-separated). To promote an existing
account:

```bash
docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "UPDATE auth_users SET role='admin' WHERE email='you@example.com'"
```

The user signs in again to get a token with the new role.

## Loading data

From the **Admin** page (`/admin`) you can queue jobs on the workers: load a city's open data, refresh rates,
reload OSM amenities, recompute yields, retrain the model. The same jobs run from the command line:

```bash
docker compose exec ingestion-worker python -m ingestion opendata --city Toronto
docker compose exec ingestion-worker python -m ingestion opendata --sources bank_of_canada
docker compose exec ingestion-worker python -m ingestion osm --cities Toronto,Vancouver
docker compose exec ingestion-worker python -m ingestion rents            # after replacing the CSV
docker compose exec ingestion-worker python -m ingestion import /data/listings.csv --source ddf
```

To load a file you downloaded by hand, copy it into the container (`docker compose cp mci.csv
ingestion-worker:/tmp/`) and pass `--file /tmp/mci.csv`. See [Data sources](data-sources.md) for every key.

Once listings are loaded, yields are computed automatically. To recompute them all, use
`POST /api/v1/admin/insights/recompute` or the admin button.

### Schedules

| Beat | Job | When (UTC) |
|---|---|---|
| ingestion-beat | Bank of Canada rates | daily 06:15 |
| ingestion-beat | OSM amenities refresh | Sunday 03:30 |
| ingestion-beat | Partner feed (only if `LISTING_FEED_URL` is set) | daily 02:00 |
| insights-beat | Market summaries | daily 04:00 |
| insights-beat | Model retrain + backtest | Sunday 03:00 |

Run exactly one of each beat.

### Removing demo data

After a real feed is connected:

```sql
DELETE FROM house_houses WHERE is_synthetic = 1;
```

Price history, links, yields and saved entries cascade.

## Basemap

The map works without a basemap (area polygons and points on a plain background). For streets and labels,
self-host a Protomaps PMTiles extract:

```bash
# pmtiles CLI: https://github.com/protomaps/go-pmtiles/releases
pmtiles extract https://build.protomaps.com/<YYYYMMDD>.pmtiles canada.pmtiles \
  --bbox=-141.0,41.6,-52.6,70.0 --maxzoom=15
```

A Canada-wide extract is several GB; a single city bounding box is much smaller. Then:

1. Mount the file into the frontend container at `/usr/share/nginx/html/tiles/canada.pmtiles` (a volume in a
   Compose override). nginx serves `/tiles/` with range requests and a one-day cache.
2. Build the frontend with `--build-arg VITE_PMTILES_URL=/tiles/canada.pmtiles`. Glyphs and sprites load
   from `protomaps.github.io` unless `VITE_MAP_GLYPHS` / `VITE_MAP_SPRITE` point elsewhere.

In production, put `/tiles/` behind a CDN if traffic grows. The file is static.

## Health and logs

- `GET /health` returns API liveness and a database check. Compose healthchecks cover Postgres and Redis.
- `GET /api/v1/admin/status` (admin) reports row counts per data set, the last 50 open-data loads, broker
  reachability and which workers answer a ping.
- `docker compose logs -f api ingestion-worker insights-worker` shows the logs. The prod overlay rotates
  them at 10 MB × 3 files.

## Backups

All state is in Postgres. Redis only holds queued jobs, which can be re-queued.

```bash
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > neighboriq-$(date +%F).dump
# restore into an empty database
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean < neighboriq-2026-09-24.dump
```

Keep the dumps off the host. Open data can be reloaded from source, but user accounts and portfolios cannot.

## Rotating JWT keys

Generate a new pair (see [Deployment](DEPLOYMENT.md#2-secrets)), update `.env`, then restart `api`. Existing
sessions become invalid and users sign in again.
