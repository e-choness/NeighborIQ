# Introduction

NeighborIQ helps a small investor screen a rental property in a Canadian city. For any listing, or any
address you found elsewhere, it answers three questions:

1. **Is the price fair?** The asking price against the nearest comparable listings, with those
   comparables shown so you can disagree with them.
2. **Will it cash-flow?** A monthly cash flow under Canadian rules: semi-annual compounding, CMHC
   insurance, land transfer tax. Every assumption is yours to change.
3. **What is the neighbourhood like?** Income, renter share, transit frequency, crime, new supply and
   assessed values, from public open data.

It is a screening tool. It does not appraise property and it gives no financial advice. It shows how each
number was computed so you can check it.

## Who it is for

People buying one to a few rental units who want to compare candidates quickly and consistently. The core
flow is:

- **Explore** a city: filter by yield, price cut, type and size.
- **Open a listing**: compare fair value against comps, adjust the cash flow, read the neighbourhood.
- **Save it** to your portfolio with your notes and assumptions.
- **Analyze** a property from anywhere else with the same tools.

## What is real, and what is demo

| Data | Out of the box | For real use |
|---|---|---|
| Listings | Synthetic, labelled "Demo data" | A licensed feed (CREA DDF®, board IDX/VOW, partner export) |
| Rents | Placeholder CMHC-format table | The current CMHC Rental Market Survey table |
| Neighbourhood data | Empty | `python -m ingestion opendata --city <City>` or the Admin page |
| Mortgage rate | 4.5% default | Bank of Canada 5-year posted rate, loaded daily |

## Quick start

Requires Docker with Compose v2.

```bash
git clone https://github.com/e-choness/NeighborIQ.git && cd NeighborIQ
cp .env.example .env            # set ADMIN_EMAILS to your email
docker compose up -d            # migrates the schema and loads demo data on first start
```

Open <http://localhost> and sign up with the email in `ADMIN_EMAILS`. The Admin page loads open data for a
city. The API reference is at <http://localhost:8000/docs>, and also [on this site](/reference/api).

## Where next

- [Methodology](/methodology): how every number is computed, and its limits
- [Data sources](/data-sources): what can be loaded, per city, and under which licence
- [Deployment](/DEPLOYMENT): one server with automatic HTTPS
- [Architecture](/architecture/overview): one API and two workers, and why
