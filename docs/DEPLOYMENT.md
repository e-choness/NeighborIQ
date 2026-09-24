# Deployment

NeighborIQ runs on one Linux server with Docker Compose. Caddy terminates TLS and obtains certificates
automatically. A 2 GB machine runs the full stack with demo data; loading assessment rolls for several
cities benefits from 4 GB or more.

## Where to host

NeighborIQ needs a few always-on processes: Postgres with PostGIS, the Valkey broker, the API, two Celery
workers and their schedulers. With demo data the whole Compose stack uses about **1 GB of RAM** at idle
(measured: insights worker ~400 MB, everything else under 150 MB each), so plan for **2 GB**. The frontend
reaches the API on the same origin (`/api/v1` through its nginx), so the simplest deployment is one machine
running the Compose stack below.

Free and low-cost options as of September 2026. Terms change often, so check each provider before you rely on
it:

| Option | Runs the whole stack? | Notes |
|---|---|---|
| **Oracle Cloud Always Free** (Ampere A1 VM) | **Yes** | The only free tier here with enough memory for the full stack. Free-tier accounts get 2 OCPU / 12 GB (halved from 4 / 24 in June 2026). ARM64: build the images on the VM (`--build`); every dependency ships ARM64 wheels. New instances can be hard to get in busy regions |
| **A small VPS** (any provider, 2 GB, e.g. a DigitalOcean Droplet) | **Yes** | A few dollars or euros a month. The most predictable option, running the same commands as below |
| **DigitalOcean App Platform** | **Yes**, managed | Paid: one container per component plus a managed Postgres. No servers to maintain; see [below](#digitalocean-app-platform) |
| **Render** free | No | Free web services sleep after 15 min idle; free Postgres expires after 30 days (then a 14-day grace period). Background workers aren't free. Fine for a short demo of the API |
| **Koyeb** free | No | One small web service (0.1 vCPU, 512 MB) and a 1 GB Postgres with PostGIS but only 5 compute hours a month |
| **Google Cloud Run** free tier | API only | 2 M requests and 360 k vCPU-seconds a month; scale-to-zero suits the stateless API, not the always-on workers |
| **Neon** / **Supabase** free Postgres | Database only | Both support PostGIS. Neon: 0.5 GB per project. Supabase: 500 MB, paused after 7 days idle. Demo data fits; a few cities of assessment rolls may not |
| **Fly.io**, **Railway** | No | Fly.io has no free tier for new accounts; Railway gives trial credit only |

Splitting the app across free services (for example, the frontend on a static host and the API on Cloud
Run) needs one custom domain for both, because the session cookies are `SameSite=Strict`. The frontend would
also need an API base-URL setting it doesn't have today. The docs site is different: it is static and is
already published free on GitHub Pages.

## 1. Prepare

- A server with Docker Engine and the Compose v2 plugin.
- A DNS `A`/`AAAA` record for your domain pointing at the server.
- Ports 80 and 443 open (Caddy needs 80 for the ACME challenge).

```bash
git clone https://github.com/e-choness/neighboriq.git && cd neighboriq
cp .env.example .env
```

## 2. Secrets

Edit `.env`:

| Variable | Value |
|---|---|
| `DOMAIN` | Public hostname, e.g. `app.example.ca` |
| `POSTGRES_PASSWORD` | A long random string (`openssl rand -base64 32`) |
| `ADMIN_EMAILS` | Your email; you become admin when you sign up with it |
| `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` | RS256 key pair (below). Required in production |
| `SECURE_COOKIES` | `1` (the default). Auth cookies are then sent only over HTTPS |
| `FEED_ALLOWED_HOSTS` | Hosts allowed for partner listing feeds, if you have one |

Generate the key pair and write it to `.env` as single lines:

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out jwt.key
openssl rsa -in jwt.key -pubout -out jwt.pub
printf 'JWT_PRIVATE_KEY="%s"\n' "$(awk 'BEGIN{ORS="\\n"}1' jwt.key)" >> .env
printf 'JWT_PUBLIC_KEY="%s"\n'  "$(awk 'BEGIN{ORS="\\n"}1' jwt.pub)" >> .env
shred -u jwt.key
```

Remove the empty `JWT_PRIVATE_KEY=`/`JWT_PUBLIC_KEY=` lines that came from `.env.example`. Keep `.env`
readable only by the deploy user (`chmod 600 .env`).

## 3. Start

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

The production overlay:

- adds **Caddy** on 80/443 (HTTP/3 included) with HSTS and security headers ([`Caddyfile`](../Caddyfile));
- removes every other published port, so Postgres, Redis and the API are reachable only on the Compose network;
- makes `POSTGRES_PASSWORD` and the JWT keys mandatory (Compose refuses to start without them);
- sets `restart: always` and log rotation, and turns on Redis persistence.

Open `https://$DOMAIN`, sign up with your admin email, and load open data from the Admin page.

## 4. Update

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

`migrate` runs on every start and applies new revisions before the API starts. Take a backup first (see
[Operations → Backups](operations.md#backups)).

Prebuilt images are published to GHCR from `main` (`ghcr.io/e-choness/neighboriq-{api,ingestion-worker,
insights-worker,frontend}`). To deploy those instead of building on the server, set `image:` for each service
in a Compose override.

## Scaling

| Pressure | Action |
|---|---|
| API latency under load | `--scale api=3`. The API is stateless. Set `RATE_LIMIT_STORAGE=redis://redis:6379/3` so limits are shared |
| Long data loads delay other jobs | `--scale ingestion-worker=2`, or run it on a second host against the same Postgres/Redis |
| Yield recomputes queue behind training | `--scale insights-worker=2` |
| Map traffic | Serve `/tiles/` and static assets from a CDN |
| Database | Managed Postgres with PostGIS; point `DATABASE_URL` at it and drop the `postgres` service |

Never scale the `*-beat` services beyond one each.

## Rollback

Images are tagged with the commit SHA. To roll back code, check out the previous commit (or pin the previous
image tags) and bring the stack up again. Roll back the schema only if the new revision's `downgrade` is safe
for your data: `docker compose run --rm migrate alembic -c migrations/alembic.ini downgrade -1`. Otherwise,
restore the backup you took before updating.

## Checklist

- [ ] DNS resolves to the server; ports 80/443 open
- [ ] `.env` has real `POSTGRES_PASSWORD`, JWT keys and `ADMIN_EMAILS`; `chmod 600 .env`
- [ ] `https://$DOMAIN/health` returns `"database": "up"`
- [ ] Rent benchmarks replaced with official CMHC figures ([Data sources](data-sources.md#rents))
- [ ] Nightly `pg_dump` stored off the host

## DigitalOcean App Platform

App Platform builds from GitHub and runs each component in its own container, with no server to maintain.
Its auto-detection only looks for a `Dockerfile`, `package.json` or `requirements.txt` at the repository root.
This repository has five deployables in subfolders, so connecting it directly ends with *"Verify the repo
contains supported file types…"*. Create the app from the spec in [`.do/app.yaml`](../.do/app.yaml) instead:

| Component | Type | From | Size |
|---|---|---|---|
| `web` | static site | `frontend/` (`npm run build` → `dist/`) | — |
| `api` | service, public at `/api` | `services/api/Dockerfile` | 1 vCPU / 0.5 GB |
| `valkey` | private service (`internal_ports` only) | `valkey/valkey:9-alpine` | 1 vCPU / 0.5 GB |
| `ingestion-worker`, `insights-worker` | workers, each with its own scheduler (`celery worker -B`) | the worker Dockerfiles | 1 vCPU / 1 GB each |
| `migrate` | job, before each deploy | `alembic upgrade head` | 0.5 GB |
| `bootstrap` | job, after each deploy | demo data if the database is empty | 0.5 GB |
| `db` | Managed PostgreSQL (existing cluster) | `neighboriq-db` | smallest plan |

The browser sees one origin: App Platform routes `/api` to the API and everything else to the SPA, so the
`SameSite=Strict` session cookies work unchanged. `DATABASE_URL` is injected as a plain libpq URL
(`postgresql://…?sslmode=require`); [`shared/database/urls.py`](../shared/database/urls.py) converts it for
asyncpg and psycopg2.

### Steps

1. **Database.** Create a Managed PostgreSQL cluster named `neighboriq-db` in the app's region (the spec uses
   `tor`, Toronto). App Platform's dev databases are not suitable, because the schema needs the PostGIS extension.
   Connect once as `doadmin` and run:

   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```

2. **Secrets.** Generate the JWT key pair as in [Secrets](#2-secrets). In `.do/app.yaml` (or later in the
   control panel), replace the `REPLACE_ME` values: `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` (single-line PEM with
   `\n` escapes) and `ADMIN_EMAILS`.

3. **Create the app.**

   ```bash
   doctl apps spec validate .do/app.yaml
   doctl apps create --spec .do/app.yaml
   ```

   Without `doctl`: create an app from the repository in the control panel, then open **Settings → App Spec →
   Edit**, paste the file and save. App Platform needs read access to the repository; grant it under
   **GitHub → Settings → Applications → DigitalOcean**.

4. **Deploy.** Each deploy runs `migrate` first, then starts the new versions, then runs `bootstrap`. Pushes
   to `main` redeploy automatically (`deploy_on_push`).

### Notes

- **Cost:** App Platform bills each container. The layout above runs five containers plus the managed
  database, so it costs several times a single 2 GB Droplet running the Compose stack. Check
  [DigitalOcean's pricing](https://www.digitalocean.com/pricing/app-platform) for current rates.
- **Storage:** containers have no persistent disk. The open-data download cache and the trained model are
  rebuilt after a redeploy; the weekly retrain, or **Admin → Retrain**, restores the model.
- **Scaling:** keep one instance of each worker, because each runs a scheduler. To scale job throughput,
  add worker components without `-B`.
- **Instance sizes:** `doctl apps tier instance-size list` shows the current slugs.

