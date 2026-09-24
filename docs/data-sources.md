# Data sources

Everything NeighborIQ shows comes from one of four places. None of it is scraped from MLS® systems or
REALTOR.ca.

| What | Source | Status |
|---|---|---|
| Listings | Synthetic demo data, or a licensed feed you connect | Demo by default, labelled "Demo data" in the UI |
| Rents | Rent benchmarks CSV in CMHC Rental Market Survey format | **Placeholder values** until you replace the file |
| Neighbourhood, property, transit, supply, rates | Public open data (below) | Loaded on demand |
| Amenities (schools, hospitals, stops) | OpenStreetMap via Overpass | Loaded on demand, refreshed weekly |

## Listings

- **Demo data.** `python -m ingestion seed` (run automatically by `bootstrap` on first start) generates
  deterministic synthetic listings across Toronto, Vancouver, Calgary, Ottawa and Montréal (32
  neighbourhoods). Prices, sizes and fees follow realistic ranges per neighbourhood, but no row is a real
  property. Rows carry `source=seed` and `is_synthetic=1`.
- **Real listings need a licence.** In Canada, listing content belongs to the brokerages and boards. The
  usual route for an investor tool is CREA's DDF® (Data Distribution Facility) through a participating
  brokerage, or a board's IDX/VOW feed. Once you have one:
  - a file export: `python -m ingestion import listings.csv --source ddf` (CSV or JSON in the canonical
    format in [`ingestion/canonical.py`](../services/ingestion-worker/ingestion/canonical.py));
  - a URL feed: add its host to `FEED_ALLOWED_HOSTS`, then trigger it from the admin page
    (`POST /api/v1/admin/feeds`) or set `LISTING_FEED_URL` for a nightly crawl.
- Comparable-listing valuations use asking prices. Sold prices are board-licensed and not available here;
  the UI says "vs. comparable asking prices" for this reason.

## Rents

`data/reference/rent_benchmarks.csv` holds average monthly rent by city and bedroom count (0 = bachelor,
3 = 3+), in the shape of CMHC's Rental Market Survey tables. **The shipped values are approximations, not
official figures.** Replace them with the current CMHC table (Housing Market Information Portal → Rental
Market → average rent by bedroom type, per CMA), then run `python -m ingestion rents`. The UI always lets
the user override rent, and warns that survey averages include long tenancies and so sit below asking rents
for vacant units.

## Open data

Registry: [`ingestion/opendata/sources.py`](../services/ingestion-worker/ingestion/opendata/sources.py).
Every load writes a row to `od_load_log` with row count, licence and attribution; the Data page
(`/data`) lists them.

### Coverage

| Need | Toronto | Vancouver | Calgary | Edmonton | Ottawa | Montréal |
|---|---|---|---|---|---|---|
| Neighbourhood polygons | ✓ | ✓ | ✓ | ✓ | ✓ (`--url`) | ✓ |
| Assessed values (assessment roll) | — ¹ | ✓ | ✓ | ✓ | — ¹ | size/units only ² |
| Building permits (new supply) | — | ✓ | ✓ | — | — | — |
| Crime | ✓ (`--url`) | — | — | — | — | — |
| Transit frequency (GTFS) | ✓ | ✓ | ✓ (`--url`) | ✓ | ✓ | ✓ |
| Census 2021 (income, tenure, population) | national, by dissemination area |||||
| Rates and price index | Bank of Canada, StatCan New Housing Price Index (national) |||||

1. Ontario assessments are held by MPAC and are not open data.
2. Montréal's roll publishes building characteristics without values.

Sources marked `--url` have no stable machine-readable address; download the file from the portal and pass
it with `--url` or `--file`.

### Source keys

| Key | Loader | Licence |
|---|---|---|
| `toronto_areas`, `vancouver_areas`, `calgary_areas`, `edmonton_areas`, `ottawa_areas`, `montreal_areas` | areas (GeoJSON polygons) | City open-government licences; Montréal CC BY 4.0 |
| `vancouver_assessments`, `calgary_assessments`, `edmonton_assessments`, `montreal_assessments` | assessments | as above |
| `vancouver_permits`, `calgary_permits` | permits | as above |
| `toronto_crime` | incidents (Major Crime Indicators) | Toronto Police Service Open Data Licence |
| `ttc_gtfs`, `translink_gtfs`, `calgary_transit_gtfs`, `ets_gtfs`, `octranspo_gtfs`, `stm_gtfs` | gtfs (stops + weekday departures) | Agency terms |
| `census_da_points` | census points (DA representative points) | Statistics Canada Open Licence |
| `census_profile` | census profile (one file per province, `--url`) | Statistics Canada Open Licence |
| `bank_of_canada` | Valet API: 5-year conventional mortgage, overnight target, prime | Bank of Canada terms (attribution) |
| `statcan_nhpi` | StatCan table 18-10-0205-01 | Statistics Canada Open Licence |

Portal URLs are resolved at load time (CKAN `package_show`, Opendatasoft exports, Socrata catalogue search),
so a republished dataset with a new ID still resolves.

### Loading

```bash
# inside the ingestion-worker container (docker compose exec ingestion-worker …)
python -m ingestion opendata --list                          # every source and whether it is verified
python -m ingestion opendata --city Vancouver                # all sources for a city, areas first
python -m ingestion opendata --sources bank_of_canada,statcan_nhpi
python -m ingestion opendata --sources toronto_crime --file /data/mci.csv
python -m ingestion opendata --sources census_profile --url https://…/98-401-X2021006_English_CSV_data_BritishColumbia.zip
```

The admin page runs the same loads as background jobs. Load a city's `*_areas` source first: the other
loaders assign rows to polygons.

### Verified vs. unverified

Only `bank_of_canada` has been exercised against the live service. The other entries were written from each
portal's documented format and field names (`verified=False`). Each column mapping lists candidate names,
and a mismatch fails the load with a `SchemaError` that names the columns actually found, so a first live
load either works or tells you exactly which mapping line to fix.

## OpenStreetMap

`python -m ingestion osm --cities Toronto,…` queries Overpass for schools, hospitals and transit stops in each
city's bounding box and links each listing to its nearest ones. Data © OpenStreetMap contributors, ODbL.

## Basemap

The map background is an optional self-hosted Protomaps PMTiles file (OpenStreetMap data, ODbL). See
[Operations → Basemap](operations.md#basemap).

## Attribution

[NOTICE](../NOTICE) lists the attribution text each publisher requires; the Data page and the map footer
display it.
