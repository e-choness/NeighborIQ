# Scraper Service

## Introduction

The Scraper Service is the **data ingestion boundary** for NeighborIQ. It orchestrates:

- **Scrapy Spider** — Web scraping of Canadian real estate listings
- **Pipeline Stages** — Data validation, deduplication, geocoding, database persistence
- **Celery Job Control** — Async task distribution to worker processes
- **Admin Dashboard API** — Job status, error logs, manual job triggering

The service separates the API (FastAPI on port 8005) from the actual scraping work (Celery worker + beat scheduler).

---

## Scrapy Pipeline Stages Flowchart

```mermaid
flowchart TD
    Spider["Scrapy Spider<br/>house_spider.py<br/>Scrapes listings<br/>yields HouseItem"]
    
    Spider --> Validation["Validation Pipeline<br/>Check required fields<br/>Validate data types<br/>Drop invalid items"]
    
    Validation --> Dedup["Deduplication Pipeline<br/>Check URL uniqueness<br/>Skip duplicates<br/>Mark re-listings"]
    
    Dedup --> Geocode["Coordinate Lookup<br/>OpenStreetMap API<br/>Resolve lat/lon<br/>from address"]
    
    Geocode --> Postgres["PostgreSQL Pipeline<br/>INSERT/UPDATE<br/>house_houses<br/>Track price changes"]
    
    Postgres --> ES["Elasticsearch Pipeline<br/>Index document<br/>Full-text + geo fields"]
    
    ES --> CeleryDispatch["Celery Dispatch Pipeline<br/>Publish compute_insights task<br/>Trigger AI prediction<br/>for new houses"]
    
    CeleryDispatch --> Complete["Pipeline Complete<br/>Item logged to stats"]
    
    Complete --> [*]
```

---

## Scheduled Scrape Sequence

```mermaid
sequenceDiagram
    participant Beat as Celery Beat<br/>Scheduler
    participant Broker as Redis Broker<br/>DB 2
    participant ScraperWorker as Scraper Worker<br/>Celery Process
    participant Scrapy as Scrapy Engine
    participant Sites as Canadian<br/>Real Estate Sites
    participant DB as PostgreSQL
    participant ES as Elasticsearch
    participant AI as AI Service<br/>Celery Queue
    
    Note over Beat: 02:00 UTC nightly
    Beat->>Broker: Publish run_scrapy_spider task<br/>cities=['toronto', 'vancouver', ...]
    
    Broker->>ScraperWorker: Task dequeued
    ScraperWorker->>Scrapy: Start spider with cities
    Scrapy->>Sites: Fetch listing pages<br/>Apply rate limiting (2s/req)
    Sites-->>Scrapy: HTML responses
    
    Scrapy->>Scrapy: Parse HTML<br/>Extract HouseItem dicts
    
    loop For each HouseItem
        Scrapy->>Validation: Validate required fields
        Validation->>Dedup: Check URL uniqueness
        Dedup->>Geocode: Resolve coordinates
        Geocode->>Postgres: INSERT/UPDATE house_houses
        Postgres->>ES: Index document
        ES->>AI: Publish compute_insights task
    end
    
    Scrapy-->>ScraperWorker: Scraping complete
    ScraperWorker->>Broker: Task result {status, count}
    Broker-->>Beat: Task complete
    
    Note over DB: Database now contains<br/>latest listings
    Note over ES: ES index reflects<br/>latest data
    Note over AI: AI tasks queued<br/>for worker to process
```

---

## Spider Hierarchy

The `LianjiaHouseSpider` implements a 4-level crawl hierarchy:

| Level | Task | Example |
|-------|------|---------|
| **City** | List city URLs | https://toronto.lianjia.com/ershoufang/ |
| **Region** | Extract district links | https://toronto.lianjia.com/ershoufang/chaoyang/ |
| **Street** | Paginate street listings | https://toronto.lianjia.com/.../p2 |
| **House** | Parse property details | Extract: title, price, area, rooms, location |

**Callback Chain**:
```python
start_requests()
  → parse_city(response, city)
    → parse_region(response, city, region)
      → parse_street(response, city, region, street)
        → parse_house(response)
          → yield HouseItem
```

---

## Pipeline Stage Reference

| Stage | Class | Responsibility | Failure Behavior |
|-------|-------|-----------------|------------------|
| **Validation** | `ValidationPipeline` | Check required fields (title, price, city, region) | DROP: log to spider stats |
| **Deduplication** | `DedupPipeline` | Check URL uniqueness | SKIP: if URL exists, update price history |
| **Geocoding** | `CoordinatePipeline` | Resolve lat/lon from address | DROP if API fails; retry next run |
| **Postgres** | `PostgresPipeline` | INSERT/UPDATE house_houses; record price_history | DROP: log DB error |
| **Elasticsearch** | `ElasticsearchPipeline` | Index document for full-text search | WARN: continue (eventual consistency OK) |
| **Celery Dispatch** | `CeleryDispatchPipeline` | Publish compute_insights task | WARN: continue (tasks retry automatically) |

---

## HouseItem Fields

**Data contract** — Scrapy spider yields HouseItem with these fields:

| Field | Type | Required | Example |
|-------|------|----------|---------|
| `title` | str | ✓ | "4-bedroom house near High Park" |
| `community` | str | ✓ | "King West" |
| `city` | str | ✓ | "toronto" |
| `region` | str | ✓ | "downtown" |
| `street` | str | ✗ | "King St W" |
| `price` | int | ✓ | 650000 (CAD) |
| `area` | float | ✗ | 250.5 (m²) |
| `rooms` | int | ✗ | 4 |
| `floor` | int | ✗ | 3 |
| `decoration` | str | ✗ | "精装" |
| `age` | int | ✗ | 5 (years) |
| `latitude` | float | ✗ | 43.6452 (WGS-84) |
| `longitude` | float | ✗ | -79.3807 (WGS-84) |
| `url` | str | ✓ | "https://lianjia.com/..." |
| `images` | list | ✗ | ["img1.jpg", "img2.jpg"] |

---

## Rate Limiting & Politeness

**Spider Configuration**:

| Setting | Value | Purpose |
|---------|-------|---------|
| `DOWNLOAD_DELAY` | 2 seconds | Delay between requests to same domain |
| `RANDOMIZE_DOWNLOAD_DELAY` | true | ±50% jitter on delay (avoid pattern detection) |
| `USER_AGENT` | Rotated | Random user-agent per request |
| `AUTOTHROTTLE_ENABLED` | true | Auto-adjust delay based on server response |

**Middlewares**:
- `UseragentMiddleware` — Rotate user-agents from pool
- `RatelimitMiddleware` — Enforce download delay

This prevents IP blocking and respects website TOS.

---

## Celery Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| `BROKER_URL` | `redis://redis:6379/2` | Redis DB 2 for task queue |
| `QUEUE` | `scraper` | Dedicated queue for scraper tasks |
| `WORKER_PREFETCH` | 1 | Worker takes 1 task at a time (prevent memory bloat) |
| `TASK_SERIALIZER` | `json` | JSON-safe serialization |
| `BEAT_SCHEDULE` | See below | Scheduled task triggers |

### Beat Schedule

| Task | Trigger | Recurrence | Notes |
|------|---------|-----------|-------|
| `run_scrapy_spider` | 02:00 UTC | Daily | Overnight scrape; avoid peak traffic |
| Optional: incremental scrape | 14:00 UTC | Daily | Optional mid-day scrape for price updates |

**Configuration** (in `tasks/celery_app.py`):
```python
beat_schedule = {
    "nightly-scrape": {
        "task": "tasks.run_scrapy_spider",
        "schedule": crontab(hour=2, minute=0),
        "kwargs": {"cities": ["toronto", "vancouver", "calgary", "ottawa", "montreal"]},
    },
}
```

---

## Control API Endpoints

### Trigger a Scrape Job

```http
POST /api/v1/scraper/jobs
Content-Type: application/json

{
  "cities": ["toronto", "vancouver"]
}
```

**Response**:
```json
{
  "job_id": "abc123def456",
  "cities": ["toronto", "vancouver"],
  "queued_at": "2025-12-06T15:30:00Z"
}
```

### Get Job Status

```http
GET /api/v1/scraper/jobs/{job_id}
```

**Response**:
```json
{
  "job_id": "abc123def456",
  "status": "success",
  "cities": ["toronto"],
  "items_scraped": 1234,
  "items_inserted": 1200,
  "started_at": "2025-12-06T02:00:00Z",
  "completed_at": "2025-12-06T02:45:00Z"
}
```

### Get Scraper Status

```http
GET /api/v1/scraper/status
```

**Response**:
```json
{
  "worker_status": "idle",
  "last_run": "2025-12-06T02:45:00Z",
  "next_scheduled": "2025-12-07T02:00:00Z",
  "recent_error_count": 0
}
```

### Get Recent Errors

```http
GET /api/v1/scraper/errors
```

**Response**:
```json
{
  "errors": [
    {
      "timestamp": "2025-12-05T14:30:00Z",
      "spider": "lianjia_houses",
      "error": "City not found: 'winnipeg'",
      "traceback": "..."
    }
  ]
}
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/2` | Task broker (Redis DB 2) |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache for scraper stats (optional) |
| `SCRAPER_DATABASE_URL` | `postgresql://root:root@localhost:5432/house_discovery` | Write access to insert houses |
| `SCRAPY_SETTINGS_MODULE` | `scraper.settings` | Scrapy configuration module |

---

## Troubleshooting

### Spider Selectors Not Finding Data

**Symptom**: 0 items scraped despite target site having listings

**Root Cause**: Website HTML structure changed; CSS selectors outdated

**Solution**:
```bash
# Inspect the website HTML
curl https://toronto.lianjia.com/ershoufang/ | grep -i "price"

# Update CSS selectors in house_spider.py
# Then restart worker
docker-compose restart scraper-worker
```

### Deduplication False Positives

**Symptom**: Legitimate new listings skipped due to URL match

**Root Cause**: Dedup logic is too aggressive or URLs are reused

**Solution**: 
- Consider composite uniqueness (URL + price)?
- Or track listing age and allow re-listing after 30 days?

### Celery Worker Lost

**Symptom**: Scraper jobs stuck in Pending forever

**Root Cause**: Worker process crashed or not running

**Solution**:
```bash
docker-compose restart scraper-worker scraper-beat

# Check logs
docker-compose logs scraper-worker
```

---

## See Also

- [**AI Insights Service**](./ai-insights-service.md) — Consumes scraped data for ML
- [**System Architecture**](../architecture/overview.md) — Celery topology
