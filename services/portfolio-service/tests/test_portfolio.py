"""
Tests for portfolio service endpoints.
"""

from fastapi.testclient import TestClient


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "portfolio-service"


def test_get_saved_houses_unauthenticated(client: TestClient):
    """Missing X-User-ID header returns 401."""
    response = client.get("/api/v1/portfolio/saved")
    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()


def test_save_house_unauthenticated(client: TestClient):
    """Missing X-User-ID header returns 401."""
    response = client.post(
        "/api/v1/portfolio/save",
        json={"house_id": 1},
    )
    assert response.status_code == 401


def test_remove_house_unauthenticated(client: TestClient):
    """Missing X-User-ID header returns 401."""
    response = client.delete("/api/v1/portfolio/saved/1")
    assert response.status_code == 401


def test_invalid_user_id_header(client: TestClient):
    """Non-integer X-User-ID returns 401."""
    response = client.get(
        "/api/v1/portfolio/saved",
        headers={"X-User-ID": "not-a-number"},
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()
