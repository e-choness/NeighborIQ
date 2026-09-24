# Deployment

NeighborIQ runs on one Linux server with Docker Compose. Caddy terminates TLS and obtains certificates
automatically. A 2 vCPU / 4 GB machine runs the full stack with demo data. Loading assessment rolls for
several cities, or training the model, benefits from 8 GB.

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
