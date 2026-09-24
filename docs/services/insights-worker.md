# insights-worker

[`services/insights-worker`](../../services/insights-worker). A Celery worker on queues `insights` and
`narratives`, plus `insights-beat`. It stores the derived numbers that list and map views need across many
listings at once. Per-listing analysis on request (comps, cash flow) runs in the API, using the same
`shared/analytics` code.

## Tasks

| Task | Queue | Does | Triggered by |
|---|---|---|---|
| `ai_insights.tasks.compute_insights` | insights | Rental yield (and model estimate, if a model exists) for given listing IDs | Ingestion after every write |
| `ai_insights.tasks.recompute_all` | insights | Same, for all active listings in batches of 500 | Admin page |
| `ai_insights.tasks.retrain_model` | insights | Train XGBoost, backtest on a 20% holdout, save model and metrics | Admin page, Sunday 03:00 |
| `ai_insights.tasks.generate_daily_narratives` | narratives | Per-city statistics → short summary | Daily 04:00 |

## Layout

| Path | Purpose |
|---|---|
| `insights/feature_engineering.py` | Listing and location features; city medians for normalisation |
| `insights/ml_models.py` | Train, backtest (MAPE, residual quantiles), save and load (`MODEL_PATH`) |
| `insights/narrative.py` | Summary text from computed statistics. `local` template by default, optional `azure` provider |
| `tasks/batch_tasks.py` | Celery tasks and SQL upserts |

## Configuration

| Variable | Default | |
|---|---|---|
| `DATABASE_URL`, `CELERY_BROKER_URL` | — | |
| `MODEL_PATH` | `/app/models/price_prediction.joblib` | mount a volume to keep the model across restarts |
| `NARRATIVE_PROVIDER` | `local` | `azure` needs `AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT` |

Model estimates are stored whenever a trained model exists; whether users see them is the API's
`ML_PREDICTIONS_ENABLED` flag.

See [Methodology](../methodology.md) for the maths.
