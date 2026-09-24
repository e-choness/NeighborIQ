"""
Registry of public data sources NeighborIQ can load.

Each source says where the data lives (a URL or a portal resolver), which
loader parses it, its licence and required attribution, and how its columns
map onto our fields. `verified=False` marks entries whose URL or column names
come from the portal's documented format but have not been exercised against
a live download yet: the first load will either work or fail with a SchemaError
naming the columns actually present — fix the mapping here.

Coverage by need (see docs/data-sources.md):
  neighbourhood polygons ... all six cities
  property values ......... Vancouver, Calgary, Edmonton (Montréal: size/units only)
  demographics ............ national (StatCan Census 2021, dissemination areas)
  transit frequency ....... TTC, TransLink, Calgary Transit, ETS, OC Transpo, STM (GTFS)
  crime ................... Toronto (Major Crime Indicators); other cities pending
  new supply (permits) .... Vancouver, Calgary
  rates / price index ..... Bank of Canada, StatCan New Housing Price Index
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from ingestion.opendata.fetch import USER_AGENT

OGL_TORONTO = "Open Government Licence – Toronto"
OGL_VANCOUVER = "Open Government Licence – Vancouver"
OGL_CALGARY = "Open Government Licence – City of Calgary"
OGL_EDMONTON = "City of Edmonton Open Data Terms of Use"
OGL_OTTAWA = "Open Government Licence – City of Ottawa"
CC_MONTREAL = "CC BY 4.0 (Ville de Montréal)"
STATCAN = "Statistics Canada Open Licence"
BOC = "Bank of Canada terms of use (attribution required)"


@dataclass(frozen=True)
class Source:
    key: str
    city: str  # "" for national sources
    kind: str  # areas | assessments | permits | incidents | gtfs | census_points | census_profile | valet | statcan_table
    licence: str
    attribution: str
    url: str | None = None
    resolver: tuple | None = None  # ("ckan", base, package, formats) | ("ods", domain, dataset, fmt) | ("socrata", domain, title, fmt)
    options: dict = field(default_factory=dict)
    verified: bool = False


def _json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 — fixed portal hosts
        return json.loads(resp.read())


def resolve_url(source: Source) -> str:
    """Turn a portal resolver into a concrete download URL."""
    if source.url:
        return source.url
    if not source.resolver:
        raise ValueError(f"{source.key}: no URL — pass --url or --file (see docs/data-sources.md)")
    kind, *args = source.resolver
    if kind == "ckan":
        base, package, formats = args
        data = _json(f"{base}/api/3/action/package_show?id={urllib.parse.quote(package)}")
        for resource in data["result"]["resources"]:
            if (resource.get("format") or "").lower() in [f.lower() for f in formats]:
                return resource["url"]
        raise ValueError(f"{source.key}: package {package} has no {formats} resource")
    if kind == "ods":
        domain, dataset, fmt = args
        suffix = "?delimiter=%2C" if fmt == "csv" else ""
        return f"https://{domain}/api/explore/v2.1/catalog/datasets/{dataset}/exports/{fmt}{suffix}"
    if kind == "socrata":
        domain, title, fmt = args
        found = _json(
            "https://api.us.socrata.com/api/catalog/v1?"
            + urllib.parse.urlencode({"domains": domain, "q": title, "limit": 10})
        )
        for result in found.get("results", []):
            if result["resource"]["name"].strip().lower() == title.lower():
                return f"https://{domain}/resource/{result['resource']['id']}.{fmt}?$limit=5000000"
        raise ValueError(f"{source.key}: no dataset titled {title!r} on {domain}")
    raise ValueError(f"{source.key}: unknown resolver {kind}")


TORONTO_CKAN = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
MONTREAL_CKAN = "https://donnees.montreal.ca"

SOURCES: dict[str, Source] = {s.key: s for s in [
    # ── Neighbourhood polygons ──────────────────────────────────────────────
    Source("toronto_areas", "Toronto", "areas", OGL_TORONTO, "Contains information licensed under the Open Government Licence – Toronto",
           resolver=("ckan", TORONTO_CKAN, "neighbourhoods", ["GeoJSON"]),
           options={"name_fields": ["AREA_NAME", "AREA_DESC"], "code_fields": ["AREA_SHORT_CODE", "AREA_LONG_CODE"]}),
    Source("vancouver_areas", "Vancouver", "areas", OGL_VANCOUVER, "Contains information licensed under the Open Government Licence – Vancouver",
           resolver=("ods", "opendata.vancouver.ca", "local-area-boundary", "geojson"),
           options={"name_fields": ["name"], "code_fields": ["mapid"]}),
    Source("calgary_areas", "Calgary", "areas", OGL_CALGARY, "Contains information licensed under the Open Government Licence – City of Calgary",
           resolver=("socrata", "data.calgary.ca", "Community District Boundaries", "geojson"),
           options={"name_fields": ["name", "comm_name"], "code_fields": ["comm_code"]}),
    Source("edmonton_areas", "Edmonton", "areas", OGL_EDMONTON, "City of Edmonton Open Data",
           resolver=("socrata", "data.edmonton.ca", "City of Edmonton - Neighbourhoods", "geojson"),
           options={"name_fields": ["name", "descriptive_name"], "code_fields": ["neighbourhood_number"]}),
    Source("ottawa_areas", "Ottawa", "areas", OGL_OTTAWA, "Ottawa Neighbourhood Study; City of Ottawa Open Data",
           options={"name_fields": ["Name", "ONS_Name", "NAME"], "code_fields": ["ONS_ID"]}),
    Source("montreal_areas", "Montreal", "areas", CC_MONTREAL, "Ville de Montréal, données ouvertes (CC BY 4.0)",
           resolver=("ckan", MONTREAL_CKAN, "limites-administratives-agglomeration", ["GeoJSON"]),
           options={"name_fields": ["NOM", "nom"], "code_fields": ["CODEID", "CODEMAMH"]}),

    # ── Assessment rolls (property values) ──────────────────────────────────
    Source("vancouver_assessments", "Vancouver", "assessments", OGL_VANCOUVER, "City of Vancouver property tax report",
           resolver=("ods", "opendata.vancouver.ca", "property-tax-report", "csv"),
           options={"mapping": {
               "source_id": ["pid", "PID"],
               "civic_number": ["from_civic_number", "FROM_CIVIC_NUMBER"],
               "street_name": ["street_name", "STREET_NAME"],
               "postal_code": ["property_postal_code", "PROPERTY_POSTAL_CODE"],
               "property_class": ["legal_type", "LEGAL_TYPE"],
               "zoning": ["zoning_district", "ZONING_DISTRICT"],
               "land_value": ["current_land_value", "CURRENT_LAND_VALUE"],
               "improvement_value": ["current_improvement_value", "CURRENT_IMPROVEMENT_VALUE"],
               "year_built": ["year_built", "YEAR_BUILT"],
               "tax_levy": ["tax_levy", "TAX_LEVY"],
               "assessment_year": ["tax_assessment_year", "TAX_ASSESSMENT_YEAR", "report_year"],
               "geo_point": ["geo_point_2d"],
           }}),
    Source("calgary_assessments", "Calgary", "assessments", OGL_CALGARY, "City of Calgary property assessments",
           resolver=("socrata", "data.calgary.ca", "Current Year Property Assessments (Parcel)", "csv"),
           options={"mapping": {
               "source_id": ["roll_number"],
               "address": ["address"],
               "assessed_value": ["assessed_value"],
               "property_class": ["assessment_class_description", "assessment_class"],
               "zoning": ["land_use_designation"],
               "year_built": ["year_of_construction"],
               "lot_size": ["land_size_sf"],
               "neighbourhood": ["comm_name"],
               "assessment_year": ["roll_year"],
               "latitude": ["latitude"],
               "longitude": ["longitude"],
           }}),
    Source("edmonton_assessments", "Edmonton", "assessments", OGL_EDMONTON, "City of Edmonton property assessment data",
           resolver=("socrata", "data.edmonton.ca", "Property Assessment Data (Current Calendar Year)", "csv"),
           options={"mapping": {
               "source_id": ["account_number"],
               "civic_number": ["house_number"],
               "street_name": ["street_name"],
               "assessed_value": ["assessed_value"],
               "neighbourhood": ["neighbourhood"],
               "property_class": ["tax_class", "assessment_class_1"],
               "latitude": ["latitude"],
               "longitude": ["longitude"],
           }}),
    Source("montreal_assessments", "Montreal", "assessments", CC_MONTREAL, "Ville de Montréal, unités d'évaluation foncière (CC BY 4.0)",
           resolver=("ckan", MONTREAL_CKAN, "unites-evaluation-fonciere", ["CSV"]),
           options={"areas_in_sqm": True, "mapping": {
               "source_id": ["ID_UEV"],
               "civic_number": ["CIVIQUE_DEBUT"],
               "street_name": ["NOM_RUE"],
               "year_built": ["ANNEE_CONSTRUCTION"],
               "units": ["NOMBRE_LOGEMENT"],
               "floor_area": ["SUPERFICIE_BATIMENT"],
               "lot_size": ["SUPERFICIE_TERRAIN"],
               "property_class": ["LIBELLE_UTILISATION"],
           }}),

    # ── Building permits (future supply) ────────────────────────────────────
    Source("vancouver_permits", "Vancouver", "permits", OGL_VANCOUVER, "City of Vancouver issued building permits",
           resolver=("ods", "opendata.vancouver.ca", "issued-building-permits", "csv"),
           options={"mapping": {
               "source_id": ["permitnumber"],
               "issued_date": ["issuedate"],
               "kind": ["typeofwork"],
               "value": ["projectvalue"],
               "geo_point": ["geo_point_2d"],
           }}),
    Source("calgary_permits", "Calgary", "permits", OGL_CALGARY, "City of Calgary building permits",
           resolver=("socrata", "data.calgary.ca", "Building Permits", "csv"),
           options={"mapping": {
               "source_id": ["permitnum"],
               "issued_date": ["issueddate"],
               "kind": ["permitclassmapped", "workclassgroup"],
               "units": ["housingunits"],
               "value": ["estprojectcost"],
               "latitude": ["latitude"],
               "longitude": ["longitude"],
           }}),

    # ── Crime ───────────────────────────────────────────────────────────────
    Source("toronto_crime", "Toronto", "incidents", "Toronto Police Service Open Data Licence",
           "Toronto Police Service Public Safety Data Portal",
           options={"mapping": {
               "category": ["MCI_CATEGORY"],
               "year": ["OCC_YEAR"],
               "area_name": ["NEIGHBOURHOOD_158"],
               "latitude": ["LAT_WGS84"],
               "longitude": ["LONG_WGS84"],
           }}),

    # ── Transit (GTFS static) ───────────────────────────────────────────────
    Source("ttc_gtfs", "Toronto", "gtfs", OGL_TORONTO, "Toronto Transit Commission",
           resolver=("ckan", TORONTO_CKAN, "ttc-routes-and-schedules", ["ZIP"])),
    Source("translink_gtfs", "Vancouver", "gtfs", "TransLink Transit Data Terms of Use", "TransLink",
           url="https://gtfs-static.translink.ca/gtfs/google_transit.zip"),
    Source("calgary_transit_gtfs", "Calgary", "gtfs", OGL_CALGARY, "Calgary Transit"),
    Source("ets_gtfs", "Edmonton", "gtfs", OGL_EDMONTON, "Edmonton Transit Service",
           url="https://gtfs.edmonton.ca/TMGTFSRealTimeWebService/GTFS/gtfs.zip"),
    Source("octranspo_gtfs", "Ottawa", "gtfs", "OC Transpo Open Data Licence", "OC Transpo",
           url="https://www.octranspo.com/files/google_transit.zip"),
    Source("stm_gtfs", "Montreal", "gtfs", CC_MONTREAL, "Société de transport de Montréal",
           url="https://www.stm.info/sites/default/files/gtfs/gtfs_stm.zip"),

    # ── Census 2021 (national) ──────────────────────────────────────────────
    Source("census_da_points", "", "census_points", STATCAN,
           "Statistics Canada, 2021 Census Geographic Attribute File",
           url="https://www12.statcan.gc.ca/census-recensement/2021/geo/aip-pia/attribute-attribs/files-fichiers/2021_92-151_X.zip",
           options={"member": ".csv"}),
    # The DA-level Census Profile is published per province; pass --url for each
    # (Comprehensive download file, 98-401-X2021006, CSV).
    Source("census_profile", "", "census_profile", STATCAN,
           "Statistics Canada, 2021 Census of Population, Census Profile (98-401-X2021006)",
           options={"member": "_data.csv"}),

    # ── Rates and price indexes (national) ──────────────────────────────────
    # V80691335: 5-year conventional mortgage (posted); V39079: target for the
    # overnight rate; V80691311: prime rate. Labels are stored from the API.
    Source("bank_of_canada", "", "valet", BOC, "Bank of Canada",
           url="https://www.bankofcanada.ca/valet/observations/V80691335,V39079,V80691311/json?start_date=2019-01-01",
           verified=True),
    Source("statcan_nhpi", "", "statcan_table", STATCAN,
           "Statistics Canada, Table 18-10-0205-01 New housing price index, monthly",
           url="https://www150.statcan.gc.ca/n1/tbl/csv/18100205-eng.zip",
           options={"member": "18100205.csv", "series_prefix": "nhpi",
                    "filters": {"New housing price indexes": "Total (house and land)"}}),
]}


def for_city(city: str) -> list[Source]:
    """Sources for one city, in dependency order (areas first)."""
    order = ["areas", "assessments", "permits", "incidents", "gtfs"]
    matches = [s for s in SOURCES.values() if s.city.lower() == city.lower()]
    return sorted(matches, key=lambda s: order.index(s.kind) if s.kind in order else 99)
