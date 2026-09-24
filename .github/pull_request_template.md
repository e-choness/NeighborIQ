## What and why

<!-- What changes, and what problem it solves for the person using NeighborIQ. -->

## How it was checked

- [ ] `ruff check . && ruff format --check .`
- [ ] Tests for the touched services (see docs/development/testing.md)
- [ ] `python scripts/export_openapi.py --check` (API changes)
- [ ] `cd frontend && npm run build` (frontend changes)
- [ ] `cd docs && npm run build` (docs changes)

## Notes for reviewers

<!-- Schema migrations, new environment variables, data sources and their licences, screenshots for UI changes. -->
