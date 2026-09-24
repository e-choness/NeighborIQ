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

    def test_trigger_feed_job_queues_celery_task(self, client, monkeypatch):
        monkeypatch.setattr("app.main.FEED_ALLOWED_HOSTS", {"feeds.partner.example"})
        mock_result = MagicMock()
        mock_result.id = "test-job-id-123"
        with patch("app.main._celery") as mock_celery:
            mock_celery.send_task.return_value = mock_result
            resp = client.post(
                "/api/v1/scraper/jobs",
                json={"feed_url": "https://feeds.partner.example/listings.json"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "test-job-id-123"
        assert data["feed_url"] == "https://feeds.partner.example/listings.json"
        assert mock_celery.send_task.call_args.args[0] == "scraper.tasks.run_feed"

    @pytest.mark.parametrize(
        "feed_url",
        [
            "http://feeds.partner.example/listings.json",  # not https
            "https://evil.example/listings.json",  # host not allow-listed
            "https://api-gateway:8000/api/v1/auth/me",  # internal service (SSRF)
            "file:///etc/passwd",
        ],
    )
    def test_feed_url_must_be_allow_listed_https(self, client, monkeypatch, feed_url):
        monkeypatch.setattr("app.main.FEED_ALLOWED_HOSTS", {"feeds.partner.example"})
        with patch("app.main._celery") as mock_celery:
            resp = client.post("/api/v1/scraper/jobs", json={"feed_url": feed_url})
        assert resp.status_code == 422
        mock_celery.send_task.assert_not_called()

    def test_trigger_ingestion_command(self, client):
        mock_result = MagicMock()
        mock_result.id = "ingest-1"
        with patch("app.main._celery") as mock_celery:
            mock_celery.send_task.return_value = mock_result
            resp = client.post("/api/v1/scraper/ingest", json={"command": "osm", "cities": ["Toronto"]})
        assert resp.status_code == 200
        assert resp.json()["command"] == "osm"
        assert mock_celery.send_task.call_args.kwargs["kwargs"] == {"command": "osm", "cities": ["Toronto"]}

    def test_unknown_ingestion_command_rejected(self, client):
        resp = client.post("/api/v1/scraper/ingest", json={"command": "rm -rf"})
        assert resp.status_code == 422

    def test_trigger_job_service_unavailable_on_celery_error(self, client):
        with patch("app.main._celery") as mock_celery:
            mock_celery.send_task.side_effect = Exception("broker down")
            resp = client.post("/api/v1/scraper/ingest", json={"command": "seed"})
        assert resp.status_code == 503


def test_worker_registers_its_tasks():
    """autodiscover_tasks(["tasks"]) silently registered nothing — guard the include list."""
    from tasks.celery_app import app as celery_app

    celery_app.loader.import_default_modules()
    assert {"scraper.tasks.run_feed", "scraper.tasks.run_ingestion"} <= set(celery_app.tasks)
