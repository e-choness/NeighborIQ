# AI Insights Service

## Introduction & Design

The AI Insights Service owns **machine learning predictions** and **async insight generation** for property valuations and neighborhood analysis.

**Provider-agnostic architecture** — The service can use different LLM providers (local, OpenAI, Azure) for narrative generation via the `NARRATIVE_PROVIDER` environment variable.

The service operates in two modes:
1. **Synchronous** — Direct API calls for predictions
2. **Asynchronous** — Celery tasks for batch processing (triggered by scraper, scheduled narratives)

---

## ML Pipeline Flowchart

```mermaid
flowchart TD
    Input["House features<br/>area, rooms, floor,<br/>age, decoration,<br/>price_per_sqm_regional"]
    
    Input --> FeatureEng["Feature Engineering<br/>Extract & normalize<br/>features"]
    
    FeatureEng --> Scale["StandardScaler<br/>Normalize to<br/>mean=0, std=1"]
    
    Scale --> XGBRegressor["XGBoost Regressor<br/>n_estimators=100<br/>max_depth=4<br/>learning_rate=0.1"]
    
    XGBRegressor --> Predict["Prediction<br/>Point estimate<br/>+ CI bounds"]
    
    Predict --> Output["Output<br/>predicted_price: int<br/>price_low: int (−15%)<br/>price_high: int (+15%)<br/>confidence: float"]
    
    Output --> End([End])
```

**Model Details**:
- **Algorithm**: XGBoost regression (gradient boosting)
- **Features**: 6-8 numeric features per house
- **Output**: Point estimate + 80% confidence interval (±15% heuristic)
- **Minimum training data**: 1,000 houses (smaller datasets produce lower-confidence predictions)
- **Persistence**: joblib serialization at `/app/models/price_prediction.joblib`

---

## Celery Task Flow

```mermaid
sequenceDiagram
    participant Scraper as Scraper Service
    participant Broker as Redis Broker<br/>DB 2
    participant Worker as Celery Worker<br/>Queue: insights
    participant DB as PostgreSQL
    participant Beat as Celery Beat<br/>Scheduler
    
    Note over Scraper: Scraper inserts<br/>1000 new houses
    Scraper->>Broker: Publish compute_insights task<br/>bulk_house_ids={...}
    
    Broker->>Worker: Task arrives
    Worker->>DB: SELECT * FROM house_houses<br/>WHERE id IN (bulk_ids)
    DB-->>Worker: House rows
    
    Worker->>Worker: Feature engineering<br/>Load XGBoost model<br/>Generate predictions
    
    Worker->>DB: UPDATE house_houses<br/>predicted_price, confidence
    
    Worker->>Broker: Task complete
    
    Note over Beat: 04:00 UTC nightly
    Beat->>Broker: Publish generate_daily_narratives<br/>cities=['toronto', 'vancouver', ...]
    
    Broker->>Worker: Task arrives
    Worker->>DB: SELECT neighborhood stats<br/>for each city
    
    Worker->>Worker: Call LLM provider<br/>NARRATIVE_PROVIDER=openai<br/>Generate narrative<br/>Combine with stats
    
    Worker->>DB: INSERT INTO narratives<br/>city, narrative, created_at
    
    Worker->>Broker: Task complete
```

---

## XGBoost Model Features

| Feature | Type | Source | Example | Reason |
|---------|------|--------|---------|--------|
| `area` | float | House data | 250.5 | Building size primary price driver |
| `rooms` | int | House data | 4 | Number of bedrooms affects value |
| `floor` | int | House data | 3 | Floor number (accessibility) |
| `age` | int | House data | 5 | Building age (depreciation) |
| `decoration` | categorical | House data | "精装" | Finish quality |
| `price_per_sqm_regional` | float | Regional lookup | 2600 | Market price index for region |

All features are normalized by StandardScaler before feeding to XGBoost.

---

## Rental Yield Calculation

**Formula** (no ML required):

```
annual_rent = area (m²) × regional_rate_per_sqm_per_year (CAD/m²/year)

gross_yield = annual_rent / purchase_price

net_yield = (annual_rent - management_costs) / purchase_price
  where management_costs = annual_rent × 0.10  (10% property mgmt fee)
```

### Regional Rental Rates (CAD/m²/year)

| City | Rate (CAD/m²/year) |
|------|-------------------|
| toronto | 350.0 |
| vancouver | 400.0 |
| calgary | 220.0 |
| ottawa | 240.0 |
| montreal | 200.0 |
| edmonton | 190.0 |
| winnipeg | 170.0 |
| **Fallback** | 250.0 |

**Example**:
- Property: 250 m² in Toronto, $650,000
- Annual rent: 250 × 350 = 87,500 CAD
- Gross yield: 87,500 / 650,000 = 13.5%
- Net yield: (87,500 - 8,750) / 650,000 = 12.1%

---

## Celery Beat Schedule

| Task | Schedule | Queue | Timezone | Description |
|------|----------|-------|----------|-------------|
| `compute_insights` | Manual trigger | insights | — | Triggered by scraper POST |
| `generate_daily_narratives` | 04:00 UTC daily | narratives | America/Toronto | Nightly narrative generation for all cities |
| `retrain_model` | Sunday 03:00 UTC | insights | America/Toronto | Weekly model retraining on accumulated data |

**Configuration** (in `tasks/celery_app.py`):
```python
beat_schedule = {
    "daily-narratives": {
        "task": "tasks.generate_daily_narratives",
        "schedule": crontab(hour=4, minute=0),
        "kwargs": {"cities": ["toronto", "vancouver", "calgary", "ottawa", "montreal"]},
    },
    "weekly-model-retrain": {
        "task": "tasks.retrain_model",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Sunday 03:00
    },
}
```

---

## Provider Configuration

The `NARRATIVE_PROVIDER` environment variable selects which LLM generates narratives:

| Provider | ENV Value | Config | Notes |
|----------|-----------|--------|-------|
| **Local (Ollama)** | `local` | — | Offline; use for dev/testing |
| **OpenAI** | `openai` | Requires `OPENAI_API_KEY` | Production-quality narratives |
| **Azure** | `azure` | Requires `AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT` | Enterprise-grade |

**Example**:
```bash
export NARRATIVE_PROVIDER=openai
export OPENAI_API_KEY=sk-...
docker-compose up -d ai-insights-service
```

---

## API Endpoints

### Predict House Price

```http
POST /api/v1/predict
Content-Type: application/json

{
  "area": 250.5,
  "rooms": 4,
  "floor": 3,
  "age": 5,
  "decoration": "精装",
  "city": "toronto"
}
```

**Response**:
```json
{
  "predicted_price": 650000,
  "price_low": 552500,
  "price_high": 747500,
  "confidence": 0.85,
  "model_version": "v1.0.0-xgboost"
}
```

### Get House Insights

```http
GET /api/v1/insights/{house_id}
```

**Response**:
```json
{
  "house_id": 1,
  "predicted_price": 650000,
  "confidence": 0.85,
  "annual_rent": 87500,
  "gross_yield": 0.135,
  "net_yield": 0.121,
  "updated_at": "2025-12-06T10:00:00Z"
}
```

### Get Neighborhood Analysis

```http
GET /api/v1/analysis/{city}/{region}
```

**Response**:
```json
{
  "city": "toronto",
  "region": "downtown",
  "median_price": 625000,
  "average_yield": 0.128,
  "narrative": "Downtown Toronto continues to be a premium market...",
  "last_updated": "2025-12-06T04:00:00Z"
}
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SCRAPER_DATABASE_URL` | `postgresql://root:root@localhost:5432/house_discovery` | Read-only access to house data |
| `CELERY_BROKER_URL` | `redis://localhost:6379/2` | Task broker (Redis DB 2) |
| `NARRATIVE_PROVIDER` | `local` | LLM provider: local, openai, azure |
| `MODEL_PATH` | `/app/models/price_prediction.joblib` | Path to XGBoost model file |
| `OPENAI_API_KEY` | — | OpenAI API key (if NARRATIVE_PROVIDER=openai) |
| `AZURE_OPENAI_KEY` | — | Azure OpenAI key (if NARRATIVE_PROVIDER=azure) |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint (if NARRATIVE_PROVIDER=azure) |

---

## Model Persistence & Retraining

### Initial Model Training

At service startup, if the model doesn't exist, it's trained on existing house data:

```python
@app.lifespan
async def lifespan(app):
    await load_or_train_model()  # Train if not found
    yield
```

### Weekly Retraining

Celery Beat triggers `retrain_model` every Sunday at 03:00 UTC:

```python
@shared_task
def retrain_model():
    """Retrain XGBoost on accumulated data."""
    houses = get_training_data()
    X, y = extract_features_and_labels(houses)
    
    if len(X) < 1000:
        logger.warning("Insufficient data for retraining")
        return
    
    pipeline = ml_models.train_model(X, y)
    joblib.dump(pipeline, MODEL_PATH)
    logger.info(f"Model retrained with {len(X)} samples")
```

---

## Troubleshooting

### Model Not Found (500 Server Error)

**Root Cause**: `MODEL_PATH` file missing

**Solution**:
```bash
# Check file exists
docker-compose exec ai-insights-service ls -la /app/models/

# If missing, restart service (triggers training)
docker-compose restart ai-insights-service
```

### Celery Worker Offline

**Symptom**: Async tasks not executing; tasks stuck in Pending

**Root Cause**: Worker process crashed or not running

**Solution**:
```bash
# Check worker status
docker-compose ps ai-insights-worker

# View logs
docker-compose logs -f ai-insights-worker

# Restart worker
docker-compose restart ai-insights-worker
```

### Low Confidence Prediction (< 0.5)

**Symptom**: `confidence: 0.3` for new house

**Root Cause**: House features are outliers or model is undertrained

**Solution**:
- Wait for more training data (> 1,000 houses)
- Check feature values are within expected ranges
- Consider retraining more frequently

---

## See Also

- [**Scraper Service**](./scraper-service.md) — Provides house data for training
- [**System Architecture**](../architecture/overview.md) — Celery worker topology
