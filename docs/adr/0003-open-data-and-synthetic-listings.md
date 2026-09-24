# 0003 — Public open data and synthetic listings; no scraping

**Status:** Accepted (2026-09)

## Context

The project scraped Lianjia (a Chinese listings site) and targeted Chinese cities. The product is now a
rental-analysis tool for small investors in Canada. Canadian listing content is licensed by brokerages and
real-estate boards. Scraping MLS® systems or REALTOR.ca breaches their terms and exposes operators to
legal risk. Much of what an investor needs to judge a neighbourhood is published as open data: census,
assessment rolls, permits, transit schedules, crime and interest rates.

## Decision

- Remove the scraper. Listings come either from deterministic **synthetic** demo data (`is_synthetic=1`,
  labelled in the UI) or from a **licensed feed** (CREA DDF® through a brokerage, a board IDX/VOW feed, or a
  partner file) via the canonical import and feed spider.
- Load neighbourhood context from **public open data** through a source registry that records licence and
  attribution, logs every load, and fails loudly on schema changes.
- Rent defaults come from a **CMHC-format benchmark file**, which users can always override.
- Code and data are licensed separately: code under FSL-1.1-ALv2 ([ADR 0005](0005-license-fsl.md)), data under
  its publishers' licences ([NOTICE](../../NOTICE)).

## Consequences

- The demo works anywhere with no data licence. Its valuations show the method, not a real market.
- Coverage varies by city (Ontario assessments are not open, for example); the UI shows missing data as
  missing.
- Portal formats change. Loaders are written against documented formats, most still unverified live
  (`verified=False`); the first live load either succeeds or names the mismatched columns.
