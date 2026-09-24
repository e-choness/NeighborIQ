from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/v1/health").status_code == 200


def test_fabricated_provider_stubs_removed():
    """The old /ai/predict stub returned made-up prices; it must stay gone."""
    assert client.post("/api/v1/ai/predict", json={}).status_code == 404
