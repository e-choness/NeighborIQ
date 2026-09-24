# Methodology

How each number in the app is computed, and what it cannot tell you. Code references are the source of
truth; this page explains them.

## Fair value from comparable listings

[`shared/analytics/valuation.py`](../shared/analytics/valuation.py) (`comps-v1`)

1. **Candidates**: active listings in the same city and property type, within ±1 bedroom and ±35% of the
   subject's square footage, with coordinates and a known size.
2. **Nearest first**: candidates are ranked by distance. The search radius widens through 1.5 km → 3 km → 6 km
   until at least 4 comps are found; at most 8 are used.
3. **Estimate**: median comp $/sq ft × subject sq ft. The range is the interquartile range (25th–75th
   percentile $/sq ft) × subject sq ft.
4. **Verdict**: asking price within ±5% of the estimate is "in line"; outside that it is "below" or "above".
5. **Confidence**: *high* with ≥ 6 comps and an IQR under 15% of the median; *medium* with ≥ 4 comps and an
   IQR under 25%; otherwise *low*. With fewer than 2 comps or no square footage, no estimate is shown.

The comps are returned with the answer and drawn on the map, so the user can judge them.

**Limits.** Comps are *asking* prices, not sold prices (sold data is board-licensed). $/sq ft ignores
condition, view, floor, parking and lot size beyond what the type and size filters capture. On demo data
the result demonstrates the method; it says nothing about a real market.

## Rent

The default rent is the city average for the bedroom count from `house_rent_benchmarks` (CMHC Rental Market
Survey format). Survey averages include long-standing tenancies, so they understate asking rent for a vacant
unit — the UI says this and asks for the user's own figure. The shipped CSV holds placeholder values; see
[Data sources → Rents](data-sources.md#rents).

## Cash flow

[`shared/analytics/cashflow.py`](../shared/analytics/cashflow.py). Every input is editable in the UI; the
defaults come from the listing and `GET /api/v1/cashflow/defaults`.

**Mortgage.** Canadian fixed-rate mortgages compound semi-annually, so the monthly rate is
`(1 + r/2)^(1/6) − 1`, not `r/12`. Payment is the standard annuity over the amortization (5–35 years).

**Default insurance.** Under 20% down, the CMHC premium is added to the principal: 2.80% of the loan up to
85% loan-to-value, 3.10% up to 90%, 4.00% up to 95%. The calculator warns that insured mortgages are
generally for owner-occupied homes, and are unavailable at $1.5M and above.

**Closing costs.** Land transfer tax by province (Ontario brackets, doubled for Toronto's municipal tax;
BC property transfer tax; Québec welcome tax, approximate; Alberta registration fees only), plus $2,000 for
legal and inspection. The user can override the total.

**Operating expenses.** Property tax (annual ÷ 12), condo fee, landlord insurance (default $35/month for a
condo unit, $125 for freehold), maintenance reserve as a share of rent (default 5% condo, 8% freehold, +2
points for buildings over 40 years old), optional management fee. Vacancy (default 4%) reduces rent and other
income.

**Outputs.**

| Metric | Definition |
|---|---|
| Monthly cash flow | Effective income − operating expenses − mortgage payment |
| NOI | (Effective income − operating expenses) × 12 |
| Cap rate | NOI ÷ price |
| Gross yield | Rent × 12 ÷ price |
| Cash-on-cash | Annual cash flow ÷ (down payment + closing costs) |
| DSCR | NOI ÷ annual debt service |
| Break-even rent | Rent at which monthly cash flow is zero, with the same vacancy and percentage costs |
| Year-1 principal paydown | Principal repaid over the first 12 payments (equity built, not cash) |

**Limits.** No income tax, capital cost allowance, rent growth, appreciation, rate renewal at the end of the
term, or special assessments. It is a first-year snapshot for screening, not a forecast.

## Stored yields

The insights worker computes `house_rental_yields` for every listing using the same function with default
assumptions and no financing: gross yield, and net yield = cap rate. These power the yield sort and the map
colouring; the listing page recomputes with the user's inputs.

## Interest rate

The default rate is the latest Bank of Canada posted 5-year conventional mortgage rate (series `V80691335`)
when it has been loaded, otherwise 4.5%. Posted rates are above typical discounted rates; the UI labels the
source and date.

## Neighbourhood facts

Area metrics come from `od_area_stats` for the polygon that contains the listing:

- **Census 2021**: median household income, median rent paid, share of renter households and population,
  from dissemination areas whose representative point falls inside the polygon. Counts are summed; medians are
  population-weighted means of the DA medians — an approximation, labelled "approx." in the UI.
- **Transit**: scheduled weekday departures (GTFS) from stops inside the polygon, per km², so a frequent line
  counts more than a stop served twice a day. Nearby stops, schools and hospitals (OpenStreetMap) are listed
  with walking-scale distances.
- **Crime**: reported major crime per year and per 1,000 residents, where a city publishes it.
- **New supply**: building permits issued in the last 24 months and the housing units they add.
- **Listings**: active listings and median asking $/sq ft and gross yield per area.

Assessment rolls are not averaged into area metrics; they back the property lookup on the Analyze page
(`GET /api/v1/properties/lookup`), which pre-fills size, year built, assessed value and tax for an address.

Each figure shows its source and period. Missing data is shown as missing, never estimated.

## Price model (off by default)

[`services/insights-worker/insights/ml_models.py`](../services/insights-worker/insights/ml_models.py)

An XGBoost regressor on listing and location features. Training holds out 20% of listings, measures relative
error on them, then refits on all rows. The 10th and 90th percentiles of held-out error set the displayed
range, so an "80% range" is an empirical statement checked on unseen listings. It needs at least 100 rows.
Estimates appear only when `ML_PREDICTIONS_ENABLED=1`; enable it once the stored backtest metrics (MAPE,
coverage) are acceptable for your market. Comparable listings stay the primary valuation.

## Market summaries

`house_market_insights` holds a short per-city summary generated nightly from computed statistics only
(counts, medians, yields, price cuts). The default provider is a deterministic template; an optional LLM
provider (`NARRATIVE_PROVIDER=azure`) may only rephrase those figures and receives no other data.

## Not advice

Estimates rely on asking prices and public data. They are not appraisals, and they are not financial,
tax or legal advice.
