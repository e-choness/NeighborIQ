import sys
sys.path.insert(0, '/app')

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "house-api-service"}


def test_list_houses_contract(client: TestClient) -> None:
    """List houses returns paginated HouseListResponse with correct fields."""
    response = client.get("/api/v1/houses")

    assert response.status_code == 200
    data = response.json()
    # HouseListResponse shape: {total, page, page_size, items}
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_get_house_not_found_returns_404(client: TestClient) -> None:
    """Fetching a non-existent house by integer ID must return 404."""
    response = client.get("/api/v1/houses/999999")

    assert response.status_code == 404


def test_list_houses_pagination_defaults(client: TestClient) -> None:
    """Default pagination params: page=1, page_size=50."""
    response = client.get("/api/v1/houses")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 50
