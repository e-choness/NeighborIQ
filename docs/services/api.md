# api

[`services/api`](../../services/api). The only HTTP service is a FastAPI app on port 8000, stateless, with
one router per domain. Interactive reference: `/docs`. Contract snapshot:
[`services/api/openapi.json`](../../services/api/openapi.json).

## Routers

| Router | Endpoints | Auth |
|---|---|---|
| `auth` | `POST /api/v1/auth/{signup,login,refresh,logout}`, `GET /auth/me`, `GET /auth/.well-known/jwks.json` | public, rate-limited (`AUTH_RATE_LIMIT`, default 10/min) |
| `listings` | `GET /houses` (filters, bbox, sorts incl. `gross_yield`, `price_per_sqft`, `price_cut`), `GET /houses/search`, `GET /houses/{id}`, `/price-history`, `/neighbourhood`, `GET /communities…`; `POST/PUT/DELETE /houses` | reads public; writes admin |
| `insights` | `GET /houses/{id}/insights` (valuation, rent, cash flow, area, rate, model if enabled), `GET /houses/{id}/valuation`, `POST /valuation` (any property), `GET /rents`, `GET /cashflow/defaults`, `POST /cashflow`, `GET /markets`, `GET /markets/{city}/points`, `GET /neighborhoods/{city}/{region}/analysis` | public |
| `places` | `GET /areas`, `/areas/geojson`, `/areas/{id}`, `/indicators`, `/properties/lookup`, `/data-sources` | public |
| `portfolio` | `GET /portfolio/saved`, `POST /portfolio/save`, `PATCH/DELETE /portfolio/saved/{house_id}` | user |
| `admin` | `POST /admin/ingest`, `/admin/feeds`, `/admin/insights/recompute`, `/admin/insights/retrain`; `GET /admin/status` | admin |

All paths are under `/api/v1`. `GET /health` and `/api/v1/health` check the database.

## Authentication

- RS256 JWTs (`app/tokens.py`; passwords hashed with bcrypt in `app/passwords.py`). The access token lasts 15 minutes, the refresh token 7 days and is rotated on every use, and
  only a hash of it is stored. Both are set as `HttpOnly`, `SameSite=Strict` cookies (`Secure` unless
  `SECURE_COOKIES=0`). An `Authorization: Bearer` header is also accepted.
- Every protected route verifies the token in-process through dependencies in `app/security.py`
  (`optional_user`, `current_user`, `admin_user`). No identity headers are trusted.
- Keys come from `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`. Without them (development only) a pair is generated
  and stored in `auth_jwt_keys`.

## Background jobs

Admin endpoints enqueue Celery tasks by name (`send_task`) on Redis. The API never imports worker code.
Feed URLs must be `https` and on a host listed in `FEED_ALLOWED_HOSTS`, to prevent SSRF.

## Configuration

| Variable | Default | |
|---|---|---|
| `DATABASE_URL` | — | `postgresql+asyncpg://…` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/2` | |
| `CORS_ORIGINS` | `http://localhost:5173` | comma-separated |
| `ADMIN_EMAILS` | empty | emails granted admin at sign-up |
| `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` | empty | PEM; required in production |
| `SECURE_COOKIES` | `1` | |
| `RATE_LIMIT_DEFAULT`, `RATE_LIMIT_STORAGE` | `120/minute`, `memory://` | use Redis storage with several replicas |
| `AUTH_RATE_LIMIT` | `10/minute` | |
| `FEED_ALLOWED_HOSTS` | empty | |
| `ML_PREDICTIONS_ENABLED` | `0` | include model estimates in `/insights` |
| `AUTO_CREATE_SCHEMA` | `1` outside Compose | `create_all` on start; Compose sets `0` (Alembic owns the schema) |
