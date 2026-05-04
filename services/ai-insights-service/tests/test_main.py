from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_predict_local():
    payload = {
        "provider": "local",
        "input": {"city": "Austin", "median_income": 80000}
    }
    r = client.post("/api/v1/ai/predict", json=payload)
    assert r.status_code == 200
    j = r.json()
    assert "predictions" in j
    assert "price" in j["predictions"]


def test_narrative_local():
    payload = {
        "provider": "local",
        "input": {"city": "Austin"}
    }
    r = client.post("/api/v1/ai/narrative", json=payload)
    assert r.status_code == 200
    j = r.json()
    assert "text" in j
    assert isinstance(j["text"], str)
