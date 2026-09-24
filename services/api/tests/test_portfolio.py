"""Portfolio: saved listings with notes and cash-flow assumptions, scoped per user."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def house_id(client: TestClient, admin_headers) -> int:
    r = client.post("/api/v1/houses", headers=admin_headers, json={
        "title": "portfolio test condo", "city": "Testville", "region": "Central",
        "community": "Portfolio", "price": 500000, "sqft": 700, "rooms": 1,
        "url": f"test://portfolio/{id(client)}",
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_requires_auth() -> None:
    with TestClient(app) as c:
        assert c.get("/api/v1/portfolio/saved").status_code == 401
        assert c.post("/api/v1/portfolio/save", json={"house_id": 1}).status_code == 401
        assert c.delete("/api/v1/portfolio/saved/1").status_code == 401


def test_save_update_list_remove(client: TestClient, user_headers, house_id) -> None:
    assumptions = {"down_payment_pct": 25, "interest_rate_pct": 4.2, "monthly_rent": 2300}
    r = client.post("/api/v1/portfolio/save", headers=user_headers,
                    json={"house_id": house_id, "notes": "look at", "assumptions": assumptions})
    assert r.json()["message"] == "House saved successfully"
    again = client.post("/api/v1/portfolio/save", headers=user_headers, json={"house_id": house_id})
    assert again.json()["message"] == "House already saved"

    saved = client.get("/api/v1/portfolio/saved", headers=user_headers).json()
    entry = next(e for e in saved if e["house_id"] == house_id)
    assert entry["assumptions"] == assumptions
    assert entry["house"]["price_per_sqft"] == pytest.approx(714.29, abs=0.01)

    patched = client.patch(f"/api/v1/portfolio/saved/{house_id}", headers=user_headers,
                           json={"notes": "offer at 480k"}).json()
    assert patched["notes"] == "offer at 480k" and patched["assumptions"] == assumptions

    assert client.delete(f"/api/v1/portfolio/saved/{house_id}", headers=user_headers).status_code == 200
    assert client.delete(f"/api/v1/portfolio/saved/{house_id}", headers=user_headers).status_code == 404


def test_users_cannot_see_each_other(client: TestClient, user_headers, admin_headers, house_id) -> None:
    client.post("/api/v1/portfolio/save", headers=admin_headers, json={"house_id": house_id})
    mine = client.get("/api/v1/portfolio/saved", headers=user_headers).json()
    assert all(e["house_id"] != house_id for e in mine)
    assert client.delete(f"/api/v1/portfolio/saved/{house_id}", headers=user_headers).status_code == 404


def test_unknown_house_404(client: TestClient, user_headers) -> None:
    r = client.post("/api/v1/portfolio/save", headers=user_headers, json={"house_id": 999999999})
    assert r.status_code == 404
