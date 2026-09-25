# Deployment

NeighborIQ runs on one Linux server with Docker Compose. Caddy serves the app over HTTPS and obtains its
certificate from Let's Encrypt automatically.

**You need:**

- A Linux server (x86-64 or ARM64) with **2 GB of RAM** or more. The stack uses about 1 GB with demo data;
  loading assessment rolls for several cities needs 4 GB or more.
- Ports **80 and 443** reachable from the internet. Caddy needs port 80 to obtain the certificate.
- A **domain name** with an `A` record pointing at the server's public IP address.

The first section below walks through Oracle Cloud's free tier from an empty account. On any other server,
start at [Install Docker](#install-docker).

## Oracle Cloud (Always Free)

Oracle's Always Free tier includes an Ampere A1 (ARM64) virtual machine that is large enough for the whole
stack. The images build natively on ARM64.

### Create the instance

In the Oracle Cloud console, open **Compute → Instances → Create instance**:

| Setting | Value |
|---|---|
| Image | **Canonical Ubuntu 24.04** |
| Shape | **Ampere → VM.Standard.A1.Flex**, 2 OCPUs, 12 GB memory (within the Always Free allowance) |
| Networking | Create a new virtual cloud network with a public subnet, and keep **Assign a public IPv4 address** on |
| SSH keys | Upload your public key, or download the generated private key |
| Boot volume | 50 GB (the default) is enough |

If you see *"Out of capacity for shape VM.Standard.A1.Flex"*, pick another availability domain or try again
later.

When the instance is running, note its **public IP address** and point your domain at it (an `A` record).

### Open ports 80 and 443

Oracle blocks all inbound traffic except SSH at the network level. Open **Networking → Virtual cloud
networks →** your VCN **→ Security Lists → Default Security List → Add Ingress Rules**, and add:

| Source CIDR | IP protocol | Destination port range |
|---|---|---|
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |
| `0.0.0.0/0` | UDP | `443` (optional: HTTP/3) |

You don't need to change the firewall on the instance itself. Docker adds its own rules for the ports it
publishes, and Caddy is the only container that publishes any.

### Keep the instance

Oracle may reclaim an Always Free instance that stays mostly idle for 7 days (CPU, network and memory use all
below 20%). A small NeighborIQ deployment is often that idle. To prevent it, upgrade the account to
**Pay As You Go** (**Billing → Upgrade and Manage Payment**). Always Free resources stay free after the upgrade;
you are billed only for resources beyond the free allowance.

Then continue with the steps for any server.

## Any server

Connect with SSH (on Oracle's Ubuntu image the user is `ubuntu`):

```bash
ssh ubuntu@<public-ip>
```

### Install Docker

Docker's install script sets up Docker Engine and the Compose plugin from Docker's own repository:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
exit   # sign out and SSH in again so the group change applies
```

Check it after signing back in: `docker compose version`.

### Configure

```bash
git clone https://github.com/e-choness/NeighborIQ.git && cd NeighborIQ
cp .env.example .env
```

Set your domain, a database password and your admin email. Replace `app.example.ca` and `you@example.com`:

```bash
sed -i "s|^DOMAIN=.*|DOMAIN=app.example.ca|" .env
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 32)|" .env
sed -i "s|^ADMIN_EMAILS=.*|ADMIN_EMAILS=you@example.com|" .env
```

Generate the key pair that signs sign-in tokens and write it to `.env`:

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out jwt.key
openssl rsa -in jwt.key -pubout -out jwt.pub
sed -i '/^JWT_PRIVATE_KEY=/d; /^JWT_PUBLIC_KEY=/d' .env
printf 'JWT_PRIVATE_KEY="%s"\n' "$(awk 'BEGIN{ORS="\\n"}1' jwt.key)" >> .env
printf 'JWT_PUBLIC_KEY="%s"\n'  "$(awk 'BEGIN{ORS="\\n"}1' jwt.pub)" >> .env
shred -u jwt.key && rm jwt.pub
chmod 600 .env
```

Other settings in `.env`:

| Variable | Value |
|---|---|
| `SECURE_COOKIES` | `1` (the default): sign-in cookies are sent only over HTTPS |
| `FEED_ALLOWED_HOSTS` | Hosts allowed for a partner listing feed, if you have one |

### Start

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The first build takes several minutes. On start, `migrate` creates the database schema and `bootstrap`
loads demo data; both then exit. Check that everything else is running:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

The production overlay ([`docker-compose.prod.yml`](../docker-compose.prod.yml)):

- adds **Caddy** on ports 80 and 443 (HTTP/3 included), with HSTS and security headers
  ([`Caddyfile`](../Caddyfile)), and redirects HTTP to HTTPS;
- publishes no other ports, so Postgres, Valkey and the API are reachable only inside the Compose network;
- refuses to start without `POSTGRES_PASSWORD` and the JWT keys;
- restarts containers automatically, rotates logs and turns on Valkey persistence.

### Verify

```bash
curl https://app.example.ca/api/v1/health
# {"status":"ok","service":"api",...,"database":"up",...}
scripts/smoke-test.sh https://app.example.ca
```

If the certificate isn't issued, check `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs
caddy`. The usual causes are a DNS record that doesn't point at the server yet, or port 80 closed.

Open `https://app.example.ca`, sign up with your `ADMIN_EMAILS` address, and load open data for your city from
the **Admin** page.

## Update

Take a [backup](operations.md#backups) first, then:

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

`migrate` applies any new schema revisions before the API starts.

## Roll back

Check out the previous version and start the stack again:

```bash
git checkout <previous-commit>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

If the update included a schema change, undo it first, while the new version is still checked out:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm migrate \
  alembic -c migrations/alembic.ini downgrade -1
```

If a downgrade would lose data you need, restore the backup instead.

## Scaling

| Pressure | Action |
|---|---|
| API latency under load | `--scale api=3`. The API is stateless. Set `RATE_LIMIT_STORAGE=redis://redis:6379/3` so rate limits are shared |
| Long data loads delay other jobs | `--scale ingestion-worker=2` |
| Yield recomputes queue behind training | `--scale insights-worker=2` |
| Database | Use a managed Postgres with PostGIS: set `DATABASE_URL` and remove the `postgres` service |

Never run more than one of each `*-beat` service.

## Checklist

- [ ] Your domain resolves to the server; ports 80 and 443 are open
- [ ] `.env` has a generated `POSTGRES_PASSWORD`, the JWT keys and `ADMIN_EMAILS`, and is `chmod 600`
- [ ] `https://<your domain>/api/v1/health` reports `"database":"up"`
- [ ] Rent benchmarks replaced with official CMHC figures ([Data sources](data-sources.md#rents))
- [ ] Nightly [backups](operations.md#backups) stored off the server
- [ ] Oracle Cloud: account upgraded to Pay As You Go, so the instance isn't reclaimed

## DigitalOcean App Platform

App Platform runs each component in its own managed container, with no server to maintain. It costs more
than a single server: five containers plus a managed database. Create the app from the spec in
[`.do/app.yaml`](../.do/app.yaml). Connecting the repository without the spec fails, because the Dockerfiles
are in subfolders.

| Component | Type | From |
|---|---|---|
| `web` | static site | `frontend/` (`npm run build` → `dist/`) |
| `api` | service, public at `/api` | `services/api/Dockerfile` |
| `valkey` | private service | `valkey/valkey:9-alpine` |
| `ingestion-worker`, `insights-worker` | workers, each with its own scheduler | the worker Dockerfiles |
| `migrate` | job, before each deploy | `alembic upgrade head` |
| `bootstrap` | job, after each deploy | demo data if the database is empty |
| `db` | Managed PostgreSQL | cluster `neighboriq-db` |

### Steps

1. **Database.** Create a Managed PostgreSQL cluster named `neighboriq-db` in the app's region (the spec uses
   `tor`, Toronto). App Platform's dev databases don't work, because the schema needs PostGIS. Connect once as
   `doadmin` and run:

   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```

2. **Secrets.** Generate the key pair as in [Configure](#configure), but print the single-line values
   instead of appending them to `.env`: `awk 'BEGIN{ORS="\\n"}1' jwt.key`. In `.do/app.yaml` (or later in the
   control panel), replace each `REPLACE_ME`: `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` and `ADMIN_EMAILS`.

3. **Create the app.**

   ```bash
   doctl apps create --spec .do/app.yaml
   ```

   Without `doctl`: create an app from the repository in the control panel, then open **Settings → App Spec →
   Edit**, paste the file and save. App Platform needs read access to the repository (**GitHub → Settings →
   Applications → DigitalOcean**).

Each deploy runs `migrate`, starts the new version, then runs `bootstrap`. Pushes to `main` redeploy
automatically.

### Notes

- **Storage:** the containers have no persistent disk. The open-data download cache and the trained model are
  rebuilt after a redeploy; the weekly retrain, or **Admin → Retrain**, restores the model.
- **Scaling:** keep one instance of each worker, because each runs a scheduler.
- **Sizes and prices:** `doctl apps tier instance-size list` lists the instance sizes;
  [DigitalOcean's pricing page](https://www.digitalocean.com/pricing/app-platform) has current rates.
