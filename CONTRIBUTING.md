# Contributing

Thanks for helping. Start with [Getting started](docs/development/getting-started.md) and the
[architecture overview](docs/architecture/overview.md).

## Workflow

1. Branch from `main`.
2. Keep changes focused. A schema change comes with its Alembic revision; an endpoint change comes with the
   regenerated `services/api/openapi.json`.
3. Before pushing:

   ```bash
   ruff check . && ruff format --check .
   python scripts/export_openapi.py --check
   # tests for what you touched — see docs/development/testing.md
   (cd frontend && npm run build)     # if you changed the frontend
   (cd docs && npm run build)         # if you changed docs or the cash-flow maths
   ```

4. Open a pull request describing what changed and why. CI must be green.

## Conventions

- **Python 3.11**, formatted and linted by Ruff (`pyproject.toml`, 110 columns).
- **`shared/`** holds only code used by more than one deployable (models, database sessions, analytics).
  Code used by one service lives in that service.
- **Money** in whole CAD integers. **Rates** as decimals in storage and percentages in API inputs named
  `*_pct`.
- **Numbers shown to users** must be traceable: document the method in [docs/methodology.md](docs/methodology.md)
  and show the source in the UI.
- **Data**: never add a source that scrapes listing sites. New open-data sources need a licence and
  attribution in the registry and in [NOTICE](NOTICE).
- **Security**: protected routes use the dependencies in `services/api/app/security.py`. Never trust identity
  from headers other than the token. Outbound fetches triggered by users go through an allow-list.
- **Frontend**: colours come from `src/theme/palette.ts` and `src/styles/app.css` tokens, never hex values
  in components. Colour is never the only encoding.
- **Docs** are Markdown in `docs/` that must read on GitHub and on the [site](https://e-choness.github.io/NeighborIQ/).
  Link to code with relative paths. Update the docs in the same PR as the behaviour they describe.
- **Decisions** that change architecture get an ADR in [docs/adr](docs/adr/).

## Licence

By contributing you agree that your contribution is licensed under the [MIT License](LICENSE).
