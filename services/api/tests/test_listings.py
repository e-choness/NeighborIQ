"""
Listing API behaviour: Canadian filters, route order, price history and admin enforcement.

Creates its own listings through the admin API using a bootstrapped admin token.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

TAG = uuid.uuid4().hex[:8]  # isolates this run's rows from earlier runs


def _listing(**overrides) -> dict:
    base = {
        "title": f"2-bed condo {TAG}",
        "community": f"Testhood-{TAG}",
        "city": "Testville",
        "region": "Central",
        "property_type": "condo",
        "price": 700000,
        "sqft": 800,
        "rooms": 2,
        "bathrooms": 2,
        "condo_fee": 550,
        "property_tax": 4200,
        "latitude": 43.65,
        "longitude": -79.38,
        "url": f"test://{TAG}/{uuid.uuid4().hex[:6]}",
    }
    base.update(overrides)
    return base


@pytest.fixture(scope="module")
def listings(client: TestClient, admin_headers) -> dict:
    created = {}
    for key, payload in {
        "condo": _listing(),
        "detached": _listing(property_type="detached", price=1500000, sqft=2000, rooms=4,
                             title=f"4-bed detached {TAG}", latitude=43.70, longitude=-79.40),
    }.items():
        r = client.post("/api/v1/houses", json=payload, headers=admin_headers)
        assert r.status_code == 200, r.text
        created[key] = r.json()
    return created


def test_write_requires_admin_role(client: TestClient, user_headers) -> None:
    assert client.post("/api/v1/houses", json=_listing(), headers=user_headers).status_code == 403
    assert client.put("/api/v1/houses/1", json={"price": 1}, headers=user_headers).status_code == 403
    assert client.delete("/api/v1/houses/1", headers=user_headers).status_code == 403


def test_search_route_not_shadowed_by_house_id(client: TestClient, listings) -> None:
    r = client.get("/api/v1/houses/search", params={"q": TAG})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2


def test_derived_fields(client: TestClient, listings) -> None:
    house = client.get(f"/api/v1/houses/{listings['condo']['id']}").json()
    assert house["price_per_sqft"] == 875.0
    assert house["original_price"] == 700000
    assert house["price_cut_pct"] is None
    assert house["is_synthetic"] is False


def test_filters(client: TestClient, listings) -> None:
    def ids(**params):
        r = client.get("/api/v1/houses", params={"q": TAG, **params})
        assert r.status_code == 200, r.text
        return {h["id"] for h in r.json()["items"]}

    condo, detached = listings["condo"]["id"], listings["detached"]["id"]
    assert ids() == {condo, detached}
    assert ids(property_type="condo") == {condo}
    assert ids(property_type="semi,detached") == {detached}
    assert ids(city="TESTVILLE") == {condo, detached}  # case-insensitive
    assert ids(rooms_min=3) == {detached}
    assert ids(sqft_max=1000) == {condo}
    assert ids(min_lat=43.6, max_lat=43.66, min_lon=-79.5, max_lon=-79.3) == {condo}


def test_price_change_is_recorded_and_filterable(client: TestClient, listings, admin_headers) -> None:
    house_id = listings["detached"]["id"]
    r = client.put(f"/api/v1/houses/{house_id}", json={"price": 1425000}, headers=admin_headers)
    assert r.status_code == 200

    history = client.get(f"/api/v1/houses/{house_id}/price-history").json()["items"]
    assert [p["price"] for p in history] == [1500000, 1425000]

    house = client.get(f"/api/v1/houses/{house_id}").json()
    assert house["original_price"] == 1500000
    assert house["price_cut_pct"] == 5.0

    cut = client.get("/api/v1/houses", params={"q": TAG, "price_cut": "true"}).json()["items"]
    assert [h["id"] for h in cut] == [house_id]


def test_sort_by_price_per_sqft(client: TestClient, listings) -> None:
    items = client.get(
        "/api/v1/houses", params={"q": TAG, "sort": "price_per_sqft", "order": "asc"}
    ).json()["items"]
    ppsf = [h["price_per_sqft"] for h in items]
    assert ppsf == sorted(ppsf)


def test_neighbourhood_empty_until_pois_loaded(client: TestClient, listings) -> None:
    r = client.get(f"/api/v1/houses/{listings['condo']['id']}/neighbourhood")
    assert r.status_code == 200
    body = r.json()
    assert body["loaded"] is False and body["schools"] == []
    assert "OpenStreetMap" in body["attribution"]


def test_unknown_house_404s(client: TestClient) -> None:
    assert client.get("/api/v1/houses/999999999/price-history").status_code == 404
    assert client.get("/api/v1/houses/999999999/neighbourhood").status_code == 404


def test_list_contract_and_pagination_defaults(client: TestClient) -> None:
    data = client.get("/api/v1/houses").json()
    assert {"total", "page", "page_size", "items"} <= set(data)
    assert data["page"] == 1 and data["page_size"] == 50


def test_get_house_not_found_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/houses/999999999").status_code == 404


def test_rows_carry_yields_and_sort_by_yield(client: TestClient, listings) -> None:
    """Yields appear once the insights worker has written house_rental_yields."""
    from sqlalchemy import create_engine, text

    from shared.database.sync import sync_database_url

    engine = create_engine(sync_database_url())
    with engine.begin() as conn:
        for key, gross in (("condo", 0.041), ("detached", 0.029)):
            conn.execute(text("""
                INSERT INTO house_rental_yields (house_id, annual_rent, gross_yield, net_yield, computed_at)
                VALUES (:h, 1, :g, :g / 2, now())
                ON CONFLICT (house_id) DO UPDATE SET gross_yield = EXCLUDED.gross_yield
            """), {"h": listings[key]["id"], "g": gross})
    items = client.get("/api/v1/houses", params={"q": TAG, "sort": "gross_yield", "order": "desc"}).json()["items"]
    assert [i["gross_yield_pct"] for i in items] == [4.1, 2.9]
    assert items[0]["cap_rate_pct"] == 2.05
