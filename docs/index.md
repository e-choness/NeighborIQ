---
layout: home
title: NeighborIQ
titleTemplate: Rental-property analysis for Canadian small investors

hero:
  name: NeighborIQ
  text: Is the price fair? Will it cash-flow?
  tagline: Rental-property analysis for small investors in Canadian cities. Open source and self-hosted, and every number shows where it came from.
  actions:
    - theme: brand
      text: Get started
      link: /guide/
    - theme: alt
      text: Try the calculator
      link: /guide/calculator
    - theme: alt
      text: GitHub
      link: https://github.com/e-choness/NeighborIQ

features:
  - title: Fair value from comparables
    details: Median $/sq ft of the nearest similar listings, widening 1.5 → 3 → 6 km until there is enough evidence. The comps are drawn on a map and the result says how confident it is.
    link: /methodology#fair-value-from-comparable-listings
    linkText: How it's computed
  - title: Cash flow under Canadian rules
    details: Semi-annual mortgage compounding, CMHC premiums, and land transfer tax by province. Cap rate, cash-on-cash, DSCR and break-even rent, with every assumption editable.
    link: /guide/calculator
    linkText: Open the calculator
  - title: The neighbourhood, from open data
    details: Census income and tenure, transit frequency, crime, new supply and assessed values, from 20+ public sources. Each figure carries its source and date.
    link: /data-sources
    linkText: See the sources
  - title: Runs on one server
    details: "docker compose up gives you demo data and every feature. In production, one server with automatic HTTPS, one API and two workers that scale on their own."
    link: /DEPLOYMENT
    linkText: Deploy it
---

<Screens />

<div class="home-notes">

## What is real

The app ships with **synthetic demo listings**, labelled as such everywhere, so it runs without a data licence.
Real listings need a licensed feed such as CREA's DDF® through a brokerage. NeighborIQ does not scrape MLS® or
REALTOR.ca. Neighbourhood data, rates and transit come from public open data you load with one command.
[Data sources →](/data-sources)

## Run it

```bash
git clone https://github.com/e-choness/NeighborIQ.git && cd NeighborIQ
cp .env.example .env        # set ADMIN_EMAILS to your email
docker compose up -d        # http://localhost — migrates and loads demo data on first start
```

</div>

<style>
.home-notes {
  max-width: 760px;
  margin: 64px auto 0;
  padding: 0 24px;
}
</style>
