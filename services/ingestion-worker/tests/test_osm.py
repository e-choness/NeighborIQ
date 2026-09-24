"""Tests for the OpenStreetMap POI loader (parsing and nearest-neighbour; no network)."""

import pytest

from ingestion.osm import Poi, build_query, haversine_m, nearest, parse_elements

PAYLOAD = {
    "elements": [
        {
            "type": "node",
            "id": 1,
            "lat": 43.6453,
            "lon": -79.3806,
            "tags": {"railway": "station", "name": "Union"},
        },
        {
            "type": "node",
            "id": 2,
            "lat": 43.6700,
            "lon": -79.3900,
            "tags": {"station": "subway", "railway": "station", "name": "Bloor-Yonge"},
        },
        {
            "type": "way",
            "id": 3,
            "center": {"lat": 43.6590, "lon": -79.3880},
            "tags": {"amenity": "hospital", "name": "Toronto General Hospital"},
        },
        {
            "type": "way",
            "id": 4,
            "center": {"lat": 43.66, "lon": -79.40},
            "tags": {"amenity": "school", "name": "Central Tech", "isced:level": "3"},
        },
        {
            "type": "node",
            "id": 5,
            "lat": 43.65,
            "lon": -79.38,
            "tags": {"highway": "bus_stop"},
        },  # unnamed → skipped
        {
            "type": "node",
            "id": 6,
            "lat": 43.65,
            "lon": -79.38,
            "tags": {"amenity": "cafe", "name": "Not a POI we track"},
        },
    ]
}


def test_parse_categorizes_and_skips_unnamed():
    pois = {p.osm_id: p for p in parse_elements(PAYLOAD)}
    assert set(pois) == {"node/1", "node/2", "way/3", "way/4"}
    assert pois["node/1"].category == "transit" and pois["node/1"].detail == "rail"
    assert pois["node/2"].detail == "subway"
    assert pois["way/3"].category == "hospital"
    assert pois["way/4"].category == "school" and pois["way/4"].detail == "3"
    assert pois["way/3"].lat == pytest.approx(43.659)


def test_haversine_known_distance():
    # Union Station → Bloor-Yonge is roughly 2.8 km
    assert haversine_m(43.6453, -79.3806, 43.6709, -79.3857) == pytest.approx(2880, rel=0.05)


def test_nearest_respects_radius_and_order():
    pois = [
        Poi("a", "transit", "far", 43.70, -79.38),
        Poi("b", "transit", "near", 43.6455, -79.3806),
        Poi("c", "transit", "mid", 43.6480, -79.3806),
    ]
    hits = nearest((43.6453, -79.3806), pois, radius_m=1000, keep=3)
    assert [p.name for p, _ in hits] == ["near", "mid"]
    assert hits[0][1] < hits[1][1]


def test_query_contains_bbox():
    q = build_query(43.5, -79.6, 43.8, -79.1)
    assert "(43.5,-79.6,43.8,-79.1)" in q and "out center tags" in q
