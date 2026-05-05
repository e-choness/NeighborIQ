"""
Tests for the scraper-service FastAPI control API.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


class TestScraperAPI:
    def test_health(self, client):
        resp = client.get("/api/v1/scraper/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_status_returns_expected_fields(self, client):
        resp = client.get("/api/v1/scraper/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "worker_status" in data
        assert "last_run" in data
        assert "next_scheduled" in data
        assert "recent_error_count" in data

    def test_errors_returns_list(self, client):
        resp = client.get("/api/v1/scraper/errors")
        assert resp.status_code == 200
        data = resp.json()
        assert "errors" in data
        assert isinstance(data["errors"], list)

    def test_trigger_job_queues_celery_task(self, client):
        mock_result = MagicMock()
        mock_result.id = "test-job-id-123"
        with patch("app.main._celery") as mock_celery:
            mock_celery.send_task.return_value = mock_result
            resp = client.post(
                "/api/v1/scraper/jobs",
                json={"cities": ["nanjing", "beijing"]},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "test-job-id-123"
        assert data["cities"] == ["nanjing", "beijing"]
        assert "queued_at" in data

    def test_trigger_job_service_unavailable_on_celery_error(self, client):
        with patch("app.main._celery") as mock_celery:
            mock_celery.send_task.side_effect = Exception("broker down")
            resp = client.post(
                "/api/v1/scraper/jobs",
                json={"cities": ["nanjing"]},
            )
        assert resp.status_code == 503
