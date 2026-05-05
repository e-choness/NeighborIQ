# WebGIS House Discovery - Legacy System Modernization Plan

## Executive Summary

**What:** Modernize a Spring Boot monolith + Layui SPA + Java scraper into a modular, service-oriented architecture with AI rental insights.

**Why:** Current stack is outdated (Spring Boot 2.3.7, Java 8, Layui 2019-era). Modernization enables: faster development (Python/Vue 3), AI/ML integration, independent service scaling, multi-tenant capabilities, and cloud-native deployment.

**How:** Restructure as 6+ services (FastAPI Python backend, modular monolith with shared PostgreSQL), modernize scraper to Python Scrapy, build AI insights engine using XGBoost/LightGBM for numeric prediction + Azure OpenAI for text narratives, and ship Vue 3 frontend with multi-tenant UX. Deploy via Docker Compose on VPS, with Kubernetes as a future scaling option.

**Timeline:** 12 weeks

---

## Current State Analysis

### Tech Stack (Legacy)

| Component | Technology                                                                                                |
| --------- | --------------------------------------------------------------------------------------------------------- |
| Backend   | Spring Boot 2.3.7, Java 1.8, JPA/Hibernate, JWT                                                           |
| Frontend  | Layui Admin Framework, ArcGIS JS v4.18 (bundled locally), Baidu Maps (bmap.min.js), ECharts, jQuery, MQTT |
| Scraper   | Spring Boot 2.1.4, WebMagic 0.7.3, Redis, MyBatis                                                         |
| Database  | MySQL 5.7+ with InnoDB                                                                                    |
| Build     | Maven, Gulp, npm                                                                                          |

### Architecture (Legacy)

```
Layui SPA ← JWT Auth ← Spring Boot REST API ← MySQL
              ↑
              └─ House-Web-Spider (separate Java app)
                 ├─ Lianjia.com scraping
                 ├─ WebMagic processors
                 └─ Redis deduplication
```

### Core Business Domain

1. **Real Estate Search:** Map-based house discovery with POI filters (schools, hospitals, transit)
2. **Data Collection:** Automated scraping of Lianjia.com (Chinese real estate platform)
3. **Geo-Intelligence:** Community geo-coordinates, bus proximity ranking
4. **Environmental Monitoring:** Watershed analysis, water quality tracking (removed — out of scope)

Documentation / settings changes
    - scraper/settings.py: default cities list → Canadian cities
    - scraper/pipelines/coordinate.py: remove or replace with a no-op pass-through (or delete it and remove from ITEM_PIPELINES)
    - Docs: remove all references to GCJ-02, Lianjia.com, yuan (¥), Chinese fields

    What stays the same
    - Dedup pipeline (Redis URL hashing — identical)
    - Validation pipeline (price > 0, area 10–500 m², rooms 1–10 — same rules work for Canada)
    - Postgres pipeline (schema unchanged)
    - Celery dispatch pipeline (unchanged)
    - All middleware (user-agent rotation, rate limiting, failure alerting)

---

## Modern Architecture Design

### Target Tech Stack

| Component       | Technology                                                             |
| --------------- | ---------------------------------------------------------------------- |
| Backend         | Python 3.11, FastAPI (async-first)                                     |
| Frontend        | Vue 3, TypeScript, Pinia (state management), Vite                      |
| Scraper         | Python 3.11, Scrapy / Playwright                                       |
| Database        | PostgreSQL 15+, Redis 7+, Elasticsearch 8+                             |
| Deployment      | Docker Compose on VPS (Kubernetes as future scaling option)            |
| CI/CD           | GitHub Actions                                                         |
| AI/ML           | XGBoost/LightGBM (numeric prediction) + Azure OpenAI (text narratives) |
| Maps            | OpenLayers 9+ + OpenStreetMap                                          |
| Authentication  | PyJWT, passlib                                                         |
| Task Scheduling | Celery + Celery Beat                                                   |

### Microservices Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Vue 3 Frontend (Multi-Tenant SPA)                    │
│         (Public Search + User Portfolio + Admin Dashboard)              │
└────────────────┬────────────────────────────────────────────────────────┘
                 │ REST APIs (HTTP/JSON)
    ┌────────────┴──────────────────────────────────────────────────────┐
    │              SERVICES LAYER (FastAPI on Python 3.11)              │
    ├──────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │  ┌─────────────────────────────────────────────────────────┐    │
    │  │           API Gateway Service (port 8000)               │    │
    │  │   JWT RS256 verification · Rate limiting · Routing      │    │
    │  └──────┬──────────┬──────────┬──────────┬────────────────┘    │
    │         │          │          │          │                       │
    │  ┌──────▼──┐  ┌────▼────┐  ┌─▼────────┐ │                      │
    │  │  Auth   │  │ House   │  │  Search  │ │                       │
    │  │ Service │  │   API   │  │ Service  │ │                       │
    │  │ (8001)  │  │ (8002)  │  │ (8004)   │ │                       │
    │  └─────────┘  └─────────┘  └──────────┘ │                      │
    │                                          │                      │
    │  ┌──────────────┐  ┌──────────────┐  ┌──▼────────────┐         │
    │  │   Scraper    │  │ AI Insights  │  │   Portfolio   │         │
    │  │   Service    │  │   Service    │  │    Service    │         │
    │  │   (8005)     │  │   (8003)     │  │    (8006)     │         │
    │  └──────────────┘  └──────────────┘  └───────────────┘         │
    │                                                                  │
    └───────────────────────────┬──────────────────────────────────────┘
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
        ┌────▼────┐        ┌────▼────┐      ┌─────▼─────┐
        │PostgreSQL│        │  Redis  │      │Elasticsearch
        │ (Core DB)│        │ (Cache) │      │(Full-text +
        │ PostGIS  │        │(7d TTL) │      │ geo search)
        └──────────┘        └─────────┘      └───────────┘
```

> **Architecture note:** All services share one PostgreSQL instance (modular monolith pattern). This is an intentional tradeoff — it provides the same code-level separation as microservices without the operational complexity of per-service databases. Tables are domain-prefixed (e.g., `auth_`, `house_`, `portfolio_`) to maintain logical boundaries.

### Service Responsibilities

| Service                        | Port                                 | Purpose                                                                                  | Tech Stack                           |
| ------------------------------ | ------------------------------------ | ---------------------------------------------------------------------------------------- | ------------------------------------ |
| **api-gateway**          | 8000                                 | JWT RS256 verification, rate limiting, reverse proxy to all services                     | FastAPI + httpx                      |
| **auth-service**         | 8001                                 | JWT generation, token validation, user identity, JWKS endpoint                           | FastAPI + PyJWT                      |
| **house-api-service**    | 8002                                 | House CRUD, discovery, filtering, pagination                                             | FastAPI + SQLAlchemy                 |
| **search-service**       | 8004                                 | Elasticsearch indexing, full-text + geo queries                                          | FastAPI + elasticsearch-py           |
| **ai-insights-service**  | 8003                                 | Price prediction (XGBoost/LightGBM), rental yield, market text narratives (Azure OpenAI) | FastAPI + xgboost + Azure OpenAI SDK |
| **scraper-service**      | 8005                                 | Web scraping orchestration, data collection                                              | Scrapy + PostgreSQL                  |
| **portfolio-service**    | 8006                                 | User saved houses, watchlists, price alerts                                              | FastAPI + SQLAlchemy                 |
| **notification-service** | 8007 (API) + Celery worker (no port) | Alerts, emails — FastAPI API handles config; Celery worker handles sending              | FastAPI + Celery                     |

---

## Implementation Plan

### Phase 1: Backend Architecture Design (Weeks 1-2)

**Parallel Tasks:** 1A, 1B, 1C, 1D

#### 1A. Service Boundaries & API Contracts

- Define OpenAPI 3.0 schemas for each service
- Specify request/response DTOs for all endpoints
- Plan service-to-service communication (REST + JSON, gRPC optional later)
- Create shared message format specifications (HouseDTO, UserDTO, etc.)

#### 1B. FastAPI Project Structure

- **Approach:** Mono-repo with services as subdirectories
  ```
  /services/
  ├─ api-gateway/          # NEW: FastAPI reverse proxy — JWT verify, rate limit, route
  ├─ auth-service/
  ├─ house-api-service/
  ├─ search-service/
  ├─ ai-insights-service/
  ├─ scraper-service/
  └─ portfolio-service/
  /shared/
  ├─ models/
  ├─ database/
  └─ utils/
  ```

  > **/shared is intentionally shared across all services — this is a modular monolith, not pure microservices. Trade-off accepted for simplicity and speed of development. Any change to /shared requires redeploying all services.**
  >
- Each service follows FastAPI best practices
- Use `poetry` for dependency management
- Use `pytest` for unit & integration tests

#### 1C. Database Connection Layer & ORM

- **ORM:** SQLAlchemy 2.0 (async-first with `sqlalchemy[asyncio]`)
- Create shared connection pool (one PostgreSQL instance)
- Implement Pydantic models as DTOs (separate from SQLAlchemy ORM)
- Use Alembic for schema migrations (versioned, repeatable)
- **Note:** All services share one PostgreSQL instance (modular monolith pattern). Each service's tables are prefixed by domain (e.g., `auth_`, `house_`, `portfolio_`) to keep logical separation.

#### 1D. Security & Identity

- **JWT library:** PyJWT (replaces python-jose, which has known CVEs and is minimally maintained)
- **JWT signing:** RS256 asymmetric keys — auth-service generates a key pair on first startup, stores the private key securely (environment variable / Kubernetes Secret), and exposes the public key via `GET /api/v1/auth/.well-known/jwks.json`
- **Token verification:** The API Gateway fetches and caches the public key from the JWKS endpoint, verifying all incoming JWTs offline (no round-trip to auth-service per request)
- **JWT delivery:** HttpOnly cookie — `Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Strict` — NOT in response body, NOT in localStorage (XSS risk)
- **Token lifetimes:** Access token: 15 minutes; Refresh token: 7 days (stored in a separate HttpOnly cookie)
- **CORS:** Allow only the Vue 3 frontend domain
- **Rate limiting:** Implemented in the API Gateway service (not per-service with slowapi)
- **Secret management:** Azure Key Vault / Kubernetes Secrets for the private key

---

### Phase 2: Data Layer Setup (Weeks 1-2, parallel with Phase 1)

**Parallel Tasks:** 2A, 2B, 2C

#### 2A. PostgreSQL Schema Migration

**Source:** MySQL 5.7 → **Target:** PostgreSQL 15+ with PostGIS

**Steps:**

1. Export MySQL schema
2. Convert data types (MySQL → PostgreSQL idioms)
3. Add GIS extension: `CREATE EXTENSION postgis;`
4. Add JSON column support
5. Create indexes: (city, region, street), (latitude, longitude), (price, date)
6. Use Alembic versioning for schema changes

**Tables:**

- `users`, `roles`, `user_roles` (authentication)
- `houses`, `communities`, `streets`, `cities` (core domain — note: `communities` is a new normalized table; in the legacy system `community` was a string field on House)
- `schools`, `hospitals`, `bus_stops` (POI)
- `house_school`, `house_hospital`, `house_bus` (junction tables)
- `house_price_predictions`, `rental_yields`, `market_insights` (AI results)

#### 2B. Redis Cache Layer

- **Purpose:** Cache frequently accessed data
- **Cache Keys:**
  - `house:{id}` (24h TTL)
  - `community:{city}:{region}:{street}` (7d TTL)
  - `search:query:{hash}` (30m TTL)
- **Invalidation:** Update on scraper insert, AI compute
- **Tool:** `redis-py` library

#### 2C. Elasticsearch Indexing

- **Purpose:** Full-text search + geo-spatial queries
- **Index Schema:**
  ```json
  {
    "properties": {
      "id": { "type": "keyword" },
      "title": { "type": "text", "analyzer": "standard" },
      "city": { "type": "keyword" },
      "region": { "type": "keyword" },
      "price": { "type": "float" },
      "location": { "type": "geo_point" },
      "ai_score": { "type": "float" }
    }
  }
  ```
- **Indexing Strategy:** Bulk insert nightly, incremental updates on new houses
- **Query Patterns:** Multi-match (title + city), range (price), geo-distance (schools within 1km)

---

### Phase 3: FastAPI Backend Services (Weeks 3-6)

#### 3A. Auth Service

- **Endpoints:**
  - `POST /api/v1/auth/login` — Authenticate user, set HttpOnly access + refresh token cookies
  - `POST /api/v1/auth/signup` — Register new user
  - `POST /api/v1/auth/refresh` — Refresh expired access token using refresh token cookie
  - `POST /api/v1/auth/validate` — Validate JWT (used by API Gateway for token introspection)
  - `POST /api/v1/auth/logout` — Clear access and refresh token cookies
  - `GET /api/v1/auth/me` — Return current user info (reads from HttpOnly cookie automatically)
  - `GET /api/v1/auth/.well-known/jwks.json` — Return RS256 public key for all services to verify tokens
- **Token Expiration:** Access: 15 minutes; Refresh: 7 days (both HttpOnly cookies)
- **Dependencies:** `PyJWT`, `passlib`

#### 3B. House API Service

- **Endpoints:**
  - `GET /api/v1/houses` — List houses (paginated, filtered by city/region/price/etc.)
  - `GET /api/v1/houses/{id}` — Get house details
  - `POST /api/v1/houses` — Create house (admin only)
  - `PUT /api/v1/houses/{id}` — Update house (admin only)
  - `DELETE /api/v1/houses/{id}` — Delete house (admin only)
  - `GET /api/v1/communities` — List communities
  - `GET /api/v1/communities/{id}/stats` — Aggregated statistics
- **Filtering:** City, region, street, price range, rooms, area
- **Pagination:** 50 results per page, cursor-based
- **Dependencies:** FastAPI, SQLAlchemy, Pydantic

#### 3C. Search Service

- **Endpoints:**
  - `GET /api/v1/search?q={query}&filters={...}` — Full-text + geo search
  - `GET /api/v1/search/nearby?lat={lat}&lon={lon}&radius={km}` — Proximity search
- **Elasticsearch Integration:** Query optimization, aggregations
- **Caching:** Layer search results in Redis

#### 3D. Database & ORM Integration

- Create SQLAlchemy models for all entities
- Implement repository pattern (DataAccessLayer)
- Connection pooling (async SQLAlchemy)
- Transaction management for multi-step operations

#### 3E. Testing

- Unit tests: JWT validation, password hashing, business logic (pytest)
- Integration tests: Database transactions, API endpoint behavior
- Target: >80% code coverage

---

### Phase 4: Scraper Modernization (Weeks 4-6, parallel with Phase 3)

#### 4A. Python Scrapy Rewrite

**Replace:** WebMagic (Java) → **With:** Scrapy / Playwright (Python)

**Architecture:**

```
Scrapy Spider Hierarchy:
├─ CitySpider (entry point)
├─ RegionSpider (parse regions from city)
├─ StreetSpider (parse streets from region)
└─ HouseSpider (parse houses from street)

Middleware:
├─ Proxy rotation
├─ User-agent rotation
├─ Rate limiting (respectful crawl delays)

Pipelines:
├─ Deduplication (Redis-backed URL hashing)
├─ Validation (price > 0, valid coords, etc.)
├─ Coordinate conversion (GCJ-02 → WGS-84)
├─ PostgreSQL insert (batch mode)
└─ Celery task dispatch (trigger AI insights)
```

#### 4B. Lianjia.com Parsing

- Extract fields: title, url, price (total + avg), area, rooms, floor, decoration, age, images
- Handle pagination
- Store as JSON for flexibility
- Error handling: Retry failed requests, log failures, alert on 10+ consecutive failures

#### 4C. Data Quality & Deduplication

- Redis dedup: Store house URL hashes, skip if seen within 7 days
- Validation rules:
  - Price > 0
  - Non-null community coordinates
  - Valid room count (1-10)
  - Valid area (10-500 m²)

#### 4D. Integration with AI Service

- On batch insert: **Celery task dispatch** — scraper enqueues a `compute_insights` Celery task on batch insert complete; `ai-insights-service` Celery worker picks it up asynchronously. No direct HTTP call between services.
- Pass metadata: city, region, community, price history

---

### Phase 5: AI Rental Insights Engine (Weeks 7-8)

#### 5A. Data Preparation & Feature Engineering

- Historical price snapshots (multiple timestamps per house)
- Feature extraction:
  - Temporal: Date, day-of-week, season, age trend
  - Spatial: City, region, distance to schools/hospitals/transit
  - Property: Rooms, area, floor, age, decoration
  - Market: Neighborhood avg price, price trend, supply count
- Store engineered features in PostgreSQL

#### 5B. ML Models for Numeric Prediction

**Approach:** Train gradient boosting models on historical scraped data. LLMs are not used for numeric prediction — LLMs cannot do real estate regression and will hallucinate numeric outputs.

**Price Prediction Model:**

- Algorithm: XGBoost or LightGBM (best-in-class for tabular regression)
- Features: area (m²), rooms, floor, age, decoration type, city, region, distance to nearest school / hospital / transit
- Training data: accumulated price history from scraper (needs at least 1,000+ houses before training is meaningful)
- Output: predicted price (point estimate) + 80% confidence interval
- Libraries: `scikit-learn` pipeline + `xgboost` or `lightgbm`
- Model persistence: serialized with joblib, stored in PostgreSQL (BYTEA column) or as a file artifact

**Rental Yield Estimation:**

- Formula-based: `annual_rent_estimate = area × regional_rental_rate_per_sqm × 12`
- Regional rental rates: stored in DB, updated from market benchmarks (scraper or manual input)
- Net yield: `(annual_rent - management_costs) / purchase_price × 100%`
- No LLM needed for the numeric computation

#### 5C. LLM for Text Narrative Only (Azure OpenAI)

Azure OpenAI is used **only for generating human-readable text summaries**, not for numeric prediction:

- **Market insights summary:** GPT-3.5 generates a 2-3 paragraph market analysis per city per day
  - Input: pre-computed stats (top neighborhoods by yield, price trends, supply count from DB)
  - Output: plain-language market summary in English
- **Price report narrative:** GPT-3.5 explains a house's predicted price in natural language
  - Input: ML model's predicted price, key feature importances, comparable houses
  - Output: "Why this house is priced at X" explanation
- This reduces Azure OpenAI API calls from one-per-house to one-per-city-per-day (cost reduction of ~99%)

#### 5D. Batch Job Execution (via Celery Beat)

- **Scheduler:** Celery Beat (not APScheduler)
- **Process:**
  1. Fetch new/updated houses (last 24h)
  2. Run ML inference for price prediction (XGBoost/LightGBM, in-process, fast)
  3. Compute rental yield from formula
  4. Call Azure OpenAI for city-level text summary (once per city, not per house)
  5. Store results: `house_price_predictions`, `rental_yields`, `market_insights`
  6. Reindex Elasticsearch with AI scores
  7. Send alerts to users with high-yield opportunities
- **Retry Logic:** Exponential backoff for OpenAI API failures

#### 5E. API Endpoints

- `GET /api/v1/houses/{id}/insights` — Price prediction, rental yield, market position
- `GET /api/v1/neighborhoods/{city}/{region}/analysis` — Top opportunities, trends
- `GET /api/v1/search?sort=ai_score` — AI-ranked search results

---

### Phase 6: Vue 3 Frontend Modernization (Weeks 4-9, parallel)

#### 6A. Project Setup & Scaffolding

- **Build Tool:** Vite (fast HMR, modern ES modules)
- **Framework:** Vue 3 with Composition API
- **State Management:** Pinia (simpler than Vuex for Vue 3)
- **Language:** TypeScript (type safety)
- **Styling:** Tailwind CSS (utility-first, responsive)
- **HTTP Client:** Axios (with interceptors for auth — no manual token management, cookies sent automatically)
- **Router:** Vue Router 4 (SPA routing)
- **Maps:** OpenLayers 9 (`ol` npm package) + OpenStreetMap

**Project Structure:**

```
/frontend/
├─ src/
│  ├─ components/         # Reusable UI components
│  │  ├─ Map.vue          # OpenLayers map component
│  │  ├─ HouseCard.vue
│  │  ├─ InsightsDashboard.vue
│  │  ├─ FilterPanel.vue
│  │  └─ ...
│  ├─ pages/              # Route-based pages
│  │  ├─ SearchPage.vue
│  │  ├─ PortfolioPage.vue
│  │  ├─ AdminPage.vue
│  │  └─ LoginPage.vue
│  ├─ stores/             # Pinia stores
│  │  ├─ auth.ts
│  │  ├─ houses.ts
│  │  └─ portfolio.ts
│  ├─ services/           # API clients
│  │  ├─ api.ts
│  │  └─ ...
│  ├─ types/              # TypeScript interfaces
│  ├─ utils/              # Helper functions
│  ├─ App.vue
│  └─ main.ts
├─ public/
├─ index.html
├─ vite.config.ts
├─ tsconfig.json
├─ tailwind.config.js
└─ package.json
```

#### 6B. Authentication & Multi-Tenant UX

- **Login/Signup:** Email + password; JWT delivered as HttpOnly cookie (browser manages automatically — no localStorage)
- **Role-Based Access:** User, Admin (enforced on frontend + backend)
- **Roles:**
  - **Public User:** Search, view house details, create account
  - **Authenticated User:** Save houses, set price alerts, view portfolio
  - **Admin:** CRUD houses, manage users, view analytics

#### 6C. Multi-Tenant Pages

**1. Public Search Page** (unauthenticated accessible)

- Map viewer (OpenLayers + OpenStreetMap)
- Filter panel: City, region, price range, rooms, distance to POI
- House listings (card view or map markers)
- House detail modal (on click)
- Sign-up CTA

**2. User Portfolio Page** (authenticated)

- Saved houses (watchlist)
- Price alerts configuration
- Portfolio statistics (avg price, favorite neighborhoods)
- Compare tool (side-by-side house comparison)
- Export to CSV/PDF

**3. Admin Dashboard** (admin only)

- House management (CRUD table)
- User management (list, roles, deactivate)
- Scraper status (last run, next scheduled, error logs)
- AI insights analytics (model performance, cost tracking)

#### 6D. Map Integration (OpenLayers)

- **Library:** OpenLayers 9 (`ol` npm package) — MIT licensed, no API key required
- Base map: OpenStreetMap tiles via `ol/source/OSM`
- Layers: House markers (clustered via `ol/source/Cluster`), POI (schools, hospitals, transit)
- Interactivity: Click opens house detail modal (`ol/Overlay`)
- Geo-search: Draw radius using `ol/interaction/Draw`, filter by distance
- Performance: `ol/source/Cluster` handles 10k+ markers client-side

> **Coordinate System:** Lianjia.com data uses GCJ-02 (China national coordinate system, slightly offset from WGS-84). OpenStreetMap uses WGS-84. The scraper converts GCJ-02 → WGS-84 using the `gcj02` Python package on ingest. All DB coordinates are stored as WGS-84. The frontend receives WGS-84 from the API and passes directly to OpenLayers — no client-side conversion needed.
>
> Documentation / settings changes
>     - scraper/settings.py: default cities list → Canadian cities
>     - scraper/pipelines/coordinate.py: remove or replace with a no-op pass-through (or delete it and remove from ITEM_PIPELINES)
>     - Docs: remove all references to GCJ-02, Lianjia.com, yuan (¥), Chinese fields
>
>     What stays the same
>     - Dedup pipeline (Redis URL hashing — identical)
>     - Validation pipeline (price > 0, area 10–500 m², rooms 1–10 — same rules work for Canada)
>     - Postgres pipeline (schema unchanged)
>     - Celery dispatch pipeline (unchanged)
>     - All middleware (user-agent rotation, rate limiting, failure alerting)

#### 6E. AI Insights Presentation

- Dashboard cards:
  - Top 5 investment neighborhoods (by yield)
  - Price trends (line chart)
  - Rental yield ranking (bar chart)
  - Neighborhood scoring (heat map)
- Real-time updates: Poll insights API every 6h (or WebSocket if needed)

#### 6F. State Management (Pinia)

```typescript
// stores/auth.ts (HttpOnly cookie approach — no token in JS state)
export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    isAuthenticated: false,
  }),
  actions: {
    async checkAuth() {
      try {
        // Cookie is sent automatically by the browser; no token management needed in JS
        const response = await apiClient.get('/api/v1/auth/me')
        this.user = response.data
        this.isAuthenticated = true
      } catch {
        this.user = null
        this.isAuthenticated = false
      }
    },
    async login(email: string, password: string) {
      await apiClient.post('/api/v1/auth/login', { email, password })
      // Server sets HttpOnly cookie; client just fetches user info
      await this.checkAuth()
    },
    async logout() {
      await apiClient.post('/api/v1/auth/logout') // Server clears the cookie
      this.user = null
      this.isAuthenticated = false
    },
  },
})

// stores/houses.ts
export const useHousesStore = defineStore('houses', {
  state: () => ({
    houses: [],
    filters: { city: '', region: '', priceMin: 0, priceMax: 5000000 },
  }),
  actions: {
    async fetchHouses() { /* call api.houses */ },
    async saveHouse(houseId) { /* call api.portfolio */ },
  },
});
```

---

### Phase 7: Deployment & DevOps (Weeks 10-11)

#### 7A. Dockerization

- **Base Image:** `python:3.11-slim` (all services)
- **Multi-stage Build:** Separate layers for deps and runtime
- **Dockerfile Template:**
  ```dockerfile
  FROM python:3.11-slim as builder
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --user -r requirements.txt

  FROM python:3.11-slim
  WORKDIR /app
  COPY --from=builder /root/.local /root/.local
  COPY . .
  ENV PATH=/root/.local/bin:$PATH
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- **Docker Compose (Local Dev & Production):**
  ```yaml
  version: '3.9'
  services:
    nginx:
      image: nginx:alpine
      ports:
        - "80:80"
        - "443:443"
      volumes:
        - ./nginx.conf:/etc/nginx/nginx.conf
        - ./certs:/etc/nginx/certs
      depends_on:
        - api-gateway

    postgres:
      image: postgres:15-alpine
      environment:
        POSTGRES_DB: house_discovery
        POSTGRES_USER: root
        POSTGRES_PASSWORD: root
      ports:
        - "5432:5432"
      volumes:
        - postgres_data:/var/lib/postgresql/data

    redis:
      image: redis:7-alpine
      ports:
        - "6379:6379"

    elasticsearch:
      image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
      environment:
        - discovery.type=single-node
        - xpack.security.enabled=false   # Required for local dev — ES 8 enables security by default
        - ES_JAVA_OPTS=-Xms512m -Xmx512m
      ports:
        - "9200:9200"

    api-gateway:
      build: ./services/api-gateway
      ports:
        - "8000:8000"
      environment:
        - AUTH_SERVICE_URL=http://auth-service:8000
        - HOUSE_SERVICE_URL=http://house-api-service:8000
        - SEARCH_SERVICE_URL=http://search-service:8000
      depends_on:
        - auth-service
        - house-api-service

    auth-service:
      build: ./services/auth-service
      ports:
        - "8001:8000"
      environment:
        - DATABASE_URL=postgresql://root:root@postgres:5432/house_discovery
        - REDIS_URL=redis://redis:6379/0

    house-api-service:
      build: ./services/house-api-service
      ports:
        - "8002:8000"
      depends_on:
        - postgres
        - redis

    # ... other services

  volumes:
    postgres_data:
  ```

#### 7B. Production Deployment (Docker Compose on VPS)

For the MVP launch, deploy to a single VPS (e.g., Hetzner, DigitalOcean, or Alibaba Cloud):

- `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
- Nginx in front for SSL termination (Let's Encrypt via certbot)
- Nginx routes: `/ → frontend (static files)`, `/api/v1/* → api-gateway (port 8000)`
- Backups: daily PostgreSQL dumps to object storage (S3-compatible)
- Monitoring: docker stats + simple uptime check

**Nginx routing config (simplified):**

```nginx
server {
    listen 443 ssl;
    location /api/v1/ {
        proxy_pass http://api-gateway:8000;
    }
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
```

#### 7C. Kubernetes (Future Phase — when scaling required)

> Kubernetes deployment is planned for when the system requires horizontal scaling, multi-region, or zero-downtime rolling deployments. The Docker Compose configuration is intentionally compatible with Kompose for semi-automated K8s manifest generation when that time comes.

Key K8s concepts to implement when needed:

- Namespace: `house-discovery`
- Deployments: one per service, replicas: 2-3 for HA
- StatefulSets: PostgreSQL, Elasticsearch
- HPA: scale on CPU (50%) or RPS
- Ingress: route `/api/v1/*` to api-gateway, `/` to frontend

#### 7D. GitHub Actions CI/CD

**Pipeline Stages:**

1. **Trigger:** Push to `main` branch or PR
2. **Lint:** pylint, black (code style)
3. **Test:** pytest with coverage report
4. **Build:** Docker images for each service
5. **Push:** Tag images with commit SHA, push to registry
6. **Deploy:** SSH to VPS, pull and restart containers
7. **Verify:** Health checks, smoke tests

**Example Workflow (.github/workflows/ci-cd.yml):**

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - run: pip install -r requirements.txt
    - run: pytest tests/ --cov=app --cov-report=xml
    - uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
    - uses: actions/checkout@v3
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    - name: Login to Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ secrets.REGISTRY_URL }}
        username: ${{ secrets.REGISTRY_USER }}
        password: ${{ secrets.REGISTRY_PASSWORD }}
    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: ./services/house-api-service
        push: true
        tags: |
          ${{ secrets.REGISTRY_URL }}/house-api-service:latest
          ${{ secrets.REGISTRY_URL }}/house-api-service:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
    - uses: actions/checkout@v3
    - name: Deploy via SSH
      run: |
        ssh user@${{ secrets.SERVER_IP }} "cd /app && docker-compose pull && docker-compose up -d"
```

#### 7E. Observability & Logging

- **Logging (MVP):** Start lightweight — `docker logs` or Dozzle (simple Docker log viewer). Structured JSON logging from FastAPI.
- **Logging (Full):** ELK Stack (Elasticsearch + Logstash + Kibana) or Azure Monitor when needed
  - Centralized log aggregation across all services
  - Log levels: DEBUG (dev), INFO (prod)
- **Metrics:** Prometheus scraping FastAPI `/metrics` endpoint
  - Track: Request latency, error rate, cache hit ratio, DB connection pool
  - Grafana dashboards for visualization
- **Tracing:** OpenTelemetry integration
  - Distributed traces across service calls
  - Span context propagation (trace ID in logs)
- **Alerts:**
  - Error rate > 5% → PagerDuty
  - Latency p99 > 1s → Slack notification
  - Disk usage > 80% → Alert

---

### Phase 8: Integration & QA (Week 12)

#### 8A. End-to-End Tests

1. **Login Flow:** POST `/api/v1/auth/login` → HttpOnly cookie set → `GET /api/v1/auth/me` returns user
2. **Search Flow:** GET `/api/v1/houses?city=nanjing&priceMin=1000000` → verify results appear on map
3. **Save House:** Authenticated user saves house → appears in `/api/v1/portfolio/saved`
4. **Portfolio View:** User sees saved houses with price trends
5. **AI Insights:** New house inserted → batch job triggers → insights visible in dashboard

#### 8B. Load Testing

- **Tool:** Apache JMeter or k6
- **Scenario:** 1000 concurrent users searching houses
- **Targets:**
  - Response time: p50 < 200ms, p99 < 500ms
  - Error rate: < 1%
  - Throughput: > 5000 requests/sec

#### 8C. AI Insights Validation

- **Price Prediction Accuracy:** Compare predicted vs. actual selling prices
  - Metric: RMSE, R² score
  - Target: RMSE < 10% of avg price
- **Rental Yield Estimates:** Verify against market benchmarks
- **Market Insights:** Manual spot-check top recommendations

#### 8D. Security Testing

- **JWT Validation:** Expired/invalid tokens rejected
- **CORS:** Requests from unauthorized domains rejected
- **Rate Limiting:** API rejects >100 req/min from same IP
- **SQL Injection:** Parameterized queries in all database calls
- **XSS Prevention:** Vue 3 auto-escaping + Content Security Policy; HttpOnly cookies immune to XSS token theft

#### 8E. Production Rollout

- **Canary Deploy:** Route 10% traffic to new services, monitor
- **Blue-Green:** Run both old + new versions, switch at once
- **Rollback Plan:** Revert image tags, re-run `docker-compose up -d`

---

## Technology Stack Summary

### Backend

- **Runtime:** Python 3.11
- **Web Framework:** FastAPI (async, high performance)
- **Database ORM:** SQLAlchemy 2.0 (async support)
- **Database:** PostgreSQL 15+ with PostGIS
- **Cache:** Redis 7+
- **Search:** Elasticsearch 8+
- **Authentication:** PyJWT, passlib
- **ML/AI (numeric):** XGBoost or LightGBM + scikit-learn
- **ML/AI (text):** Azure OpenAI SDK (GPT-3.5 for narratives)
- **Web Scraping:** Scrapy, Playwright (as fallback)
- **Task Scheduling:** Celery + Celery Beat
- **Testing:** pytest, pytest-asyncio
- **Linting:** pylint, black, flake8
- **API Documentation:** Swagger (auto-generated by FastAPI)

### Frontend

- **Runtime:** Node.js 18+ / npm
- **Framework:** Vue 3 (Composition API)
- **Language:** TypeScript
- **Build Tool:** Vite
- **State Management:** Pinia
- **HTTP Client:** Axios (cookies sent automatically — no manual token management)
- **Router:** Vue Router 4
- **Styling:** Tailwind CSS
- **Maps:** OpenLayers 9 + OpenStreetMap
- **Testing:** Vitest, Vue Test Utils
- **E2E Testing:** Playwright / Cypress

### DevOps & Deployment

- **Containerization:** Docker
- **Primary Deployment:** Docker Compose on VPS + Nginx
- **Future Orchestration:** Kubernetes (v1.27+) when scaling needed
- **Registry:** Docker Hub / Azure Container Registry
- **CI/CD:** GitHub Actions
- **Monitoring:** Prometheus, Grafana
- **Logging:** Dozzle (MVP) → ELK Stack / Azure Monitor (production)
- **Tracing:** OpenTelemetry
- **Secret Management:** Kubernetes Secrets / Azure Key Vault

---

## Project Structure (Post-Modernization)

```
WebGIS-Application-for-House-Discovery/
├── services/
│   ├── api-gateway/         # NEW: FastAPI reverse proxy
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── middleware/
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── auth-service/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── models/
│   │   │   ├── routes/
│   │   │   ├── dependencies/
│   │   │   └── utils/
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── docker-compose.override.yml
│   ├── house-api-service/
│   ├── search-service/
│   ├── ai-insights-service/
│   ├── scraper-service/
│   └── portfolio-service/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── stores/
│   │   ├── services/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.vue
│   │   └── main.ts
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── tailwind.config.js
├── shared/                  # Modular monolith shared layer
│   ├── models/
│   │   └── pydantic_schemas.py
│   ├── database/
│   │   └── postgres.py
│   └── utils/
├── migrations/
│   └── alembic/
│       ├── versions/
│       │   └── 001_initial_schema.py
│       └── env.py
├── docker-compose.yml
├── docker-compose.prod.yml
├── nginx.conf
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── MODERNIZATION_PLAN.md (this file)
├── README.md
└── .gitignore
```

---

## Verification Checklist

### Unit Tests

- [ ] `pytest tests/ --cov` shows >80% coverage
- [ ] All service endpoints have unit tests
- [ ] Auth token generation/validation tested (RS256)
- [ ] House filtering logic tested
- [ ] XGBoost/LightGBM model inference tested with sample data

### Integration Tests

- [ ] Docker Compose: `docker-compose up` all services start successfully
- [ ] Elasticsearch: verify `xpack.security.enabled=false` allows unauthenticated connections in dev
- [ ] API Gateway: JWT RS256 verification rejects invalid/expired tokens
- [ ] Service-to-service calls: api-gateway → auth-service → house-api verified
- [ ] Database transactions: insert house → Elasticsearch index → cache invalidate
- [ ] Scraper pipeline: fetch → validate → GCJ-02 to WGS-84 convert → insert → Celery task dispatch
- [ ] PostgreSQL migrations: Alembic upgrade/downgrade works
- [ ] Coordinate conversion: verify GCJ-02 → WGS-84 produces valid OpenStreetMap-visible coordinates for sample houses in Nanjing, Beijing, Shanghai

### End-to-End Tests

- [ ] Login: POST `/api/v1/auth/login` → HttpOnly cookie set → `GET /api/v1/auth/me` returns user
- [ ] Search: GET `/api/v1/houses?city=nanjing&price_min=1000000` → results appear on OpenLayers map
- [ ] Save: Authenticated user saves house → appears in portfolio
- [ ] Insights: New house inserted → batch job triggers → insights visible 6h later
- [ ] Portfolio: User filters, exports, compares houses

### Load Testing

- [ ] 1000 concurrent users: p99 latency < 500ms
- [ ] Error rate < 1%
- [ ] Throughput > 5000 req/sec

### AI Insights

- [ ] Price prediction RMSE < 10% of avg price (XGBoost/LightGBM model)
- [ ] Rental yield estimates match market benchmarks
- [ ] Market insights text summaries (LLM) are relevant and actionable

### Production Deployment

- [ ] `docker-compose up` on VPS: all containers healthy
- [ ] Nginx SSL termination working (HTTPS)
- [ ] API gateway routes requests correctly to all downstream services
- [ ] PostgreSQL data persists across container restarts (volume mount)
- [ ] Docker log aggregation working (Dozzle or equivalent)

### Security

- [ ] JWT validation: Expired tokens rejected by API Gateway
- [ ] RS256 public key served correctly at `/api/v1/auth/.well-known/jwks.json`
- [ ] HttpOnly cookie: token not accessible via `document.cookie` in browser console
- [ ] CORS: Unauthorized domains rejected
- [ ] Rate limiting: API throttles >100 req/min from single IP
- [ ] SQL injection: All queries parameterized
- [ ] Secrets not logged or exposed

---

## Timeline & Milestones

| Phase                    | Weeks | Deliverable                                                 | Status     |
| ------------------------ | ----- | ----------------------------------------------------------- | ---------- |
| 1. Architecture Design   | 1-2   | OpenAPI schemas, DB design, service boundaries              | Planned    |
| 2. Data Layer            | 1-2   | PostgreSQL schema, Redis, Elasticsearch setup               | Parallel   |
| 3. FastAPI Services      | 3-6   | API Gateway, Auth, House API, Search services + tests       | Sequential |
| 4. Scraper Modernization | 4-6   | Python Scrapy, Lianjia parsing, coord conversion, dedup     | Parallel   |
| 5. AI Insights Engine    | 7-8   | XGBoost/LightGBM + Azure OpenAI narrative, Celery Beat jobs | Sequential |
| 6. Vue 3 Frontend        | 4-9   | Multi-tenant SPA, OpenLayers map, insights dashboard        | Parallel   |
| 7. DevOps & Deployment   | 10-11 | Docker Compose on VPS, Nginx, GitHub Actions                | Sequential |
| 8. QA & Rollout          | 12    | E2E tests, load tests, production launch                    | Final      |

---

## Design Decisions & Rationale

### 1. OpenLayers + OpenStreetMap over ArcGIS

- **Why:** ArcGIS requires Esri licensing for commercial use; the bundled v4.18 is enormous (~5MB+ gzipped). OpenLayers is MIT licensed, no API key, excellent Vue 3 integration.
- **Tradeoff:** Less polished 3D support vs ArcGIS. Not a concern for a 2D house map.

### 2. OpenLayers over Baidu Maps

- **Why:** Baidu Maps JS API is China-specific; OSM + OpenLayers works globally and has no API key requirements. Coordinate conversion (GCJ-02 → WGS-84) handles the China coordinate system difference.

### 3. Modular Monolith over Pure Microservices

- **Why:** Pure microservices (DB per service) adds immense operational complexity (6+ migration tracks, cross-service joins become API calls, distributed transactions). For this project's scale, a shared PostgreSQL with domain-prefixed tables gives the same code organization benefits without the operational overhead.
- **Acknowledged tradeoff:** Services are coupled at the data layer. Acceptable for MVP.

### 4. Docker Compose First, Kubernetes Later

- **Why:** Kubernetes adds 2-3 weeks of infrastructure work before any service is live. Docker Compose deploys to a single VPS in hours. K8s becomes relevant when you need horizontal scaling, multi-region, or zero-downtime rolling deployments.

### 5. RS256 Asymmetric JWT

- **Why:** Shared HS256 secret is a security anti-pattern — any compromised service can forge tokens for any other. RS256 means only auth-service can sign; other services (or the API Gateway) verify using the public key from the JWKS endpoint.

### 6. HttpOnly Cookie for JWT Storage

- **Why:** localStorage is readable by any JavaScript on the page (XSS vulnerability). HttpOnly cookies are invisible to JS; the browser manages them automatically and sends them with every request.

### 7. PyJWT over python-jose

- **Why:** python-jose has known CVEs and is minimally maintained. PyJWT is the most widely used Python JWT library, actively maintained, and supports RS256 natively.

### 8. XGBoost/LightGBM for Price Prediction (not LLMs)

- **Why:** LLMs have no access to Canadian real estate market data and cannot perform statistical regression. Numeric price "predictions" from GPT-4 would be hallucinations. Gradient boosting models trained on scraped historical data produce statistically valid predictions.

### 9. LLM (Azure OpenAI) for Text Narrative Only

- **Why:** GPT-3.5 excels at generating human-readable market summaries from pre-computed statistics. Running it once per city per day (not per house) makes costs manageable (~99% reduction vs. per-house LLM calls).

### 10. Celery + Celery Beat (single scheduler)

- **Why:** Using both APScheduler and Celery is unnecessary duplication. Celery Beat handles periodic scheduling; Celery handles async task execution. One system for both.

### 11. API Gateway Service

- **Why:** With 6+ services, each implementing auth verification, rate limiting, and request logging independently is duplicated logic and a maintenance burden. A thin FastAPI gateway centralizes these cross-cutting concerns behind a single entry point.

### 12. FastAPI over Django

- **Why:** Lighter, async-first, perfect for service-oriented architecture and high-throughput APIs. Django is better suited for monolithic apps.

### 13. PostgreSQL + Redis + Elasticsearch

- **Why:** Polyglot storage for specialized use cases:
  - PostgreSQL: Relational core (strong ACID, PostGIS for geo)
  - Redis: High-speed caching (microsecond latency)
  - Elasticsearch: Full-text + geo-spatial search (sub-100ms queries)

### 14. Batch Processing for AI (not Real-Time)

- **Why:** Cost-effective, simpler infrastructure, sufficient for daily insights
- **Future:** Can upgrade to stream processing (Kafka) if real-time insights are demanded

### 15. Multi-Tenant UX (not Single Admin Dashboard)

- **Why:** Future growth potential (public search marketplace, user portfolios, admin CMS). Layui is admin-only; Vue 3 SPA supports public + authenticated + admin from day 1.

---

## Further Considerations

### 1. Coordinate System (GCJ-02 vs WGS-84)

**Context:** Lianjia.com coordinates use GCJ-02 (China's national offset standard). OpenStreetMap uses WGS-84. Without conversion, house markers will appear visibly displaced (off by ~500m in Chinese cities).

**Solution:**

- Scraper converts GCJ-02 → WGS-84 on ingest using the `gcj02` Python package
- All coordinates stored in PostgreSQL and Elasticsearch are WGS-84
- Frontend receives WGS-84 from API and passes directly to OpenLayers (no client-side conversion needed)
- PostGIS operations (distance queries) use WGS-84 geometry (SRID 4326)

**Action:** Add GCJ-02 → WGS-84 conversion step to the scraper pipeline (Phase 4) before PostgreSQL insert.

Documentation / settings changes
    - scraper/settings.py: default cities list → Canadian cities
    - scraper/pipelines/coordinate.py: remove or replace with a no-op pass-through (or delete it and remove from ITEM_PIPELINES)
    - Docs: remove all references to GCJ-02, Lianjia.com, yuan (¥), Chinese fields

    What stays the same
    - Dedup pipeline (Redis URL hashing — identical)
    - Validation pipeline (price > 0, area 10–500 m², rooms 1–10 — same rules work for Canada)
    - Postgres pipeline (schema unchanged)
    - Celery dispatch pipeline (unchanged)
    - All middleware (user-agent rotation, rate limiting, failure alerting)

---

### 2. AI Model Retraining Cadence

**Question:** How often should ML models (XGBoost/LightGBM) be retrained for accuracy?

**Options:**

- Weekly (fast feedback, higher compute cost)
- Monthly (balanced)
- Quarterly (cost-effective but potentially stale)

**Recommendation:** Retrain monthly once sufficient historical data accumulates (1,000+ houses). Monitor prediction accuracy (RMSE); if degradation >10%, trigger immediate retraining. Use MLflow to version models.

**Action:** Implement model performance tracking in the AI insights dashboard.

---

### 3. Data Privacy & Compliance

**Question:** Are there Chinese data residency requirements (GDPR-equivalent)?

**Options:**

- Deploy to China regions (Azure China, AWS China)
- Keep data on-premise
- Use anonymization + external APIs

**Recommendation:** If yes, deploy to China regions. Ensure:

- Data encryption at rest (TLS, database encryption)
- Data encryption in transit (TLS 1.3)
- Avoid sending PII to external AI services (anonymize/hash before OpenAI API)
- Audit logs for compliance

**Action:** Conduct data privacy audit; align with local regulations (CYBERSPACE ADMINISTRATION OF CHINA, CAC).

---

### 4. Backward Compatibility with Legacy Frontend

**Question:** Should we run Layui and Vue 3 in parallel during transition?

**Options:**

- Full replacement (faster, cleaner)
- Parallel APIs with feature flags
- Gradual cutover (Layui → Vue 3)

**Recommendation:** Full replacement for a clean break. Use Docker Compose blue-green to switch all traffic at once; monitor for 2 weeks before decommissioning the legacy system.

---

### 5. Cost Optimization for Azure OpenAI

**Question:** OpenAI API costs at scale. How to control?

Since LLMs are now used only for text narratives (not per-house numeric predictions), costs are dramatically lower by design. Additional controls:

1. **Batching:** One API call per city per day (not per house)
2. **Caching:** Store narrative results in PostgreSQL with 7-day TTL
3. **Model Tiering:** GPT-3.5 for all narratives (GPT-4 only if quality is insufficient)
4. **Monitoring:** Track API spend per day, alert if >budget

**Action:** Add cost tracking dashboard; calculate monthly burn rate after first week of operation.

---

### 6. Scalability & Performance Optimization

**Question:** What's the target scale?

**Assumptions:**

- 1M+ houses across all Canadian cities
- 10k concurrent users during peak
- 5000 queries/sec (search, portfolio operations)

**Optimizations:**

- Elasticsearch sharding (one shard per city for faster queries)
- Redis replication (multi-region caching)
- PostgreSQL read replicas (distribute SELECT queries)
- CDN for static content (Vue 3 frontend, map tiles)
- gRPC between services (lower latency than HTTP/REST, future option)

**Action:** Performance testing in Week 11; identify bottlenecks; optimize accordingly.

---

### 7. Security Hardening for Production

**Considerations:**

- DDoS protection (Cloudflare, WAF)
- API authentication & authorization (RS256 JWT)
- Rate limiting (in API Gateway, per-user, per-IP, per-endpoint)
- Secrets rotation (Azure Key Vault, periodic rotation)
- Vulnerability scanning (Trivy, Snyk in CI/CD)

**Action:** Run security audit in Week 10; implement findings before production.

---

## Migration Strategy from Legacy System

### Step 1: Data Migration (Week 0-1)

1. Export MySQL schema to PostgreSQL (use `pg_chameleon` or custom Python script)
2. Convert community coordinates from GCJ-02 to WGS-84 during migration
3. Validate data integrity (row counts, checksums)
4. Parallel run (old API ← MySQL, new API ← PostgreSQL)

### Step 2: Service Launch (Week 3+)

1. Auth service live (JWT RS256 generation)
2. House API live (read-only initially)
3. Scraper starts populating PostgreSQL (in parallel with MySQL)

### Step 3: Cutover (Week 10)

1. Switch Nginx from old → new services via Docker Compose
2. Monitor error rates, logs
3. Rollback plan: revert docker-compose to old image tags

### Step 4: Shutdown Legacy (Week 12+)

1. Decommission Spring Boot / Layui after 2 weeks of parallel operation
2. Archive MySQL database as backup

---

## Success Metrics

| Metric                       | Target                                | How to Measure                                   |
| ---------------------------- | ------------------------------------- | ------------------------------------------------ |
| **Performance**        | p99 latency < 500ms                   | Prometheus metrics, load tests                   |
| **Reliability**        | 99.9% uptime                          | Docker health checks, alerting                   |
| **AI Accuracy**        | RMSE < 10% of avg price               | Backtest XGBoost/LightGBM predictions vs. actual |
| **User Adoption**      | > 80% active monthly                  | Frontend analytics                               |
| **Cost**               | < $5k/month (infrastructure + OpenAI) | VPS billing, Azure OpenAI API tracking           |
| **Developer Velocity** | 2x faster feature delivery            | Deployment frequency, lead time                  |
| **Code Quality**       | > 80% test coverage                   | pytest report                                    |
| **Security**           | 0 critical vulnerabilities            | Trivy scan, penetration test                     |

---

## Appendix A: AI Insights - Sample LLM Prompts (Text Narratives Only)

These prompts are used **only for generating human-readable text narratives**, not for numeric predictions. Numeric values (price, yield %) come from XGBoost/LightGBM models and are passed as input context.

### Market Insights Summary Prompt (per city, once daily)

```
You are a real estate market analyst. Based on the following pre-computed market statistics for {city}, 
write a 2-3 paragraph market summary in {language}.

Market Statistics (computed from actual data):
- Top neighborhoods by rental yield: {top_neighborhoods_json}
- Average price trend (last 6 months): {trend_pct}% {direction}
- Total active listings: {listing_count}
- Fastest appreciating area: {fastest_area} (+{appreciation_pct}%)

Write a clear, factual market summary. Do not invent statistics — use only the data provided above.
```

### Price Report Narrative Prompt (per house, on demand)

```
You are a real estate analyst explaining a price estimate to a buyer.

House: {city}, {region}, {community}
ML Model Predicted Price: ¥{predicted_price} (confidence interval: ¥{price_low} - ¥{price_high})
Key factors driving this estimate (from model feature importances):
- {factor_1}: {impact_1}
- {factor_2}: {impact_2}
- {factor_3}: {impact_3}
Comparable houses in this area: avg ¥{comparable_avg}/m²

Write 2-3 sentences explaining why this house is estimated at this price. 
Be factual, reference only the provided data, and note the confidence level.
```

---

## Appendix B: Example FastAPI Service (Auth Service)

```python
# services/auth-service/app/main.py
import os
import json
from fastapi import FastAPI, HTTPException, Depends, Response, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional
import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from passlib.context import CryptContext

app = FastAPI(title="Auth Service", version="1.0.0")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# RS256 key pair — load from env in production
PRIVATE_KEY_PEM = os.environ["JWT_PRIVATE_KEY"]  # PEM-encoded RSA private key
PUBLIC_KEY_PEM = os.environ["JWT_PUBLIC_KEY"]    # PEM-encoded RSA public key
ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# JWKS endpoint — all services fetch this to verify tokens
@app.get("/api/v1/auth/.well-known/jwks.json")
async def jwks():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    import base64
    public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(PUBLIC_KEY_PEM)
    # Return as JWKS format
    return {"keys": [json.loads(pyjwt.algorithms.RSAAlgorithm(pyjwt.algorithms.RSAAlgorithm.SHA256).to_jwk(public_key))]}

# Login — sets HttpOnly cookie, does NOT return token in body
@app.post("/api/v1/auth/login")
async def login(request: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, request.email)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
  
    access_token = create_token({"sub": str(user.id)}, expires_minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_token({"sub": str(user.id), "type": "refresh"}, expires_minutes=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)
  
    response.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="strict", max_age=900)
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="strict", max_age=604800)
    return {"message": "Login successful"}

# Me endpoint — reads cookie automatically
@app.get("/api/v1/auth/me")
async def me(access_token: Optional[str] = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = pyjwt.decode(access_token, PUBLIC_KEY_PEM, algorithms=[ALGORITHM])
        user = await get_user_by_id(db, payload["sub"])
        return {"id": user.id, "email": user.email, "roles": user.roles}
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Logout — clears cookies
@app.post("/api/v1/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}

# Signup
@app.post("/api/v1/auth/signup")
async def signup(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    # ... create user with hashed password
    pass

# Token validation (used by API Gateway)
@app.post("/api/v1/auth/validate")
async def validate_token(access_token: Optional[str] = Cookie(default=None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="No token")
    try:
        payload = pyjwt.decode(access_token, PUBLIC_KEY_PEM, algorithms=[ALGORITHM])
        return {"user_id": payload["sub"], "valid": True}
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_token(data: dict, expires_minutes: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return pyjwt.encode(to_encode, PRIVATE_KEY_PEM, algorithm=ALGORITHM)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

---

## Appendix C: Example Vue 3 Component (Search Page)

```vue
<!-- frontend/src/pages/SearchPage.vue -->
<template>
  <div class="search-page">
    <header>
      <nav>
        <router-link to="/">Home</router-link>
        <button v-if="!authStore.isAuthenticated" @click="goLogin">Sign In</button>
        <router-link v-else to="/portfolio">Portfolio</router-link>
      </nav>
    </header>

    <div class="main">
      <FilterPanel 
        :filters="housesStore.filters" 
        @update-filters="housesStore.updateFilters"
      />

      <Map 
        :houses="housesStore.houses" 
        :selected="selectedHouse"
        @select-house="selectedHouse = $event"
      />

      <HouseList 
        :houses="housesStore.houses"
        :loading="housesStore.loading"
        @select-house="selectedHouse = $event"
        @save-house="saveHouse"
      />

      <HouseDetailModal 
        v-if="selectedHouse"
        :house="selectedHouse"
        :insights="getInsights(selectedHouse.id)"
        @close="selectedHouse = null"
        @save="saveHouse(selectedHouse)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useHousesStore } from '@/stores/houses'
import { apiClient } from '@/services/api'
import FilterPanel from '@/components/FilterPanel.vue'
import Map from '@/components/Map.vue'
import HouseList from '@/components/HouseList.vue'
import HouseDetailModal from '@/components/HouseDetailModal.vue'

const authStore = useAuthStore()
const housesStore = useHousesStore()
const selectedHouse = ref(null)
const insights = ref({})

onMounted(async () => {
  await authStore.checkAuth()  // Verify session via HttpOnly cookie
  await housesStore.fetchHouses()
})

const getInsights = (houseId: number) => {
  return insights.value[houseId] || {}
}

const saveHouse = async (house) => {
  if (!authStore.isAuthenticated) {
    alert('Please sign in first')
    return
  }
  await apiClient.post('/api/v1/portfolio/save', { house_id: house.id })
  alert('House saved to portfolio!')
}

const goLogin = () => {
  // Navigate to login
}
</script>

<style scoped>
.search-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

header {
  background: #f5f5f5;
  padding: 1rem;
  border-bottom: 1px solid #ddd;
}

.main {
  display: grid;
  grid-template-columns: 250px 1fr 300px;
  flex: 1;
  gap: 1rem;
  padding: 1rem;
}

@media (max-width: 768px) {
  .main {
    grid-template-columns: 1fr;
  }
}
</style>
```

---

## Conclusion

This modernization plan transforms a legacy monolith into a service-oriented, AI-powered platform with a pragmatic architecture. The phased approach allows parallel development across frontend, backend, and infrastructure, targeting a 12-week delivery.

**Key Wins:**

- 10x faster API responses (async FastAPI vs. synchronous Spring Boot)
- Service-level code isolation (modular monolith — simpler than microservices, cleaner than a monolith)
- AI-powered insights: statistically valid price prediction (XGBoost/LightGBM) + human-readable narratives (Azure OpenAI)
- Modern developer experience (Vue 3, TypeScript, Pinia, OpenLayers)
- Pragmatic deployment (Docker Compose on VPS, K8s-ready for the future)
- Multi-tenant UX (public search + user portfolios + admin dashboard)
- Secure JWT implementation (RS256, HttpOnly cookies, API Gateway centralization)

**Risk Mitigation:**

- Parallel data migrations reduce cutover risk
- Blue-green deployment enables clean switchover
- Comprehensive testing (unit, integration, E2E, load)
- Rollback plan (revert docker-compose image tags)
