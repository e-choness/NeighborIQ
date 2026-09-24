# Architecture decision records

| # | Decision | Status |
|---|---|---|
| [0001](0001-one-api-two-workers.md) | One API and two workers instead of seven services | Accepted |
| [0002](0002-search-in-postgres.md) | Keep search in PostgreSQL until measured need | Accepted (engine choice open) |
| [0003](0003-open-data-and-synthetic-listings.md) | Public open data and synthetic listings; no scraping | Accepted |
| [0004](0004-keep-celery.md) | Keep Celery + Redis for background jobs | Accepted |

Format: context, decision, consequences. Add a new record instead of rewriting an accepted one.
