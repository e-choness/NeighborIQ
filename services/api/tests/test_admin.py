"""Operator endpoints: job dispatch to the Celery workers and data coverage."""
from unittest.mock import MagicMock, patch

import pytest


def test_ingest_dispatches_to_ingestion_worker(client, admin_headers):
    with patch("app.routers.admin._celery") as celery:
        celery.send_task.return_value = MagicMock(id="job-1")
        r = client.post("/api/v1/admin/ingest", headers=admin_headers,
                        json={"command": "opendata", "sources": ["bank_of_canada"]})
    assert r.status_code == 200 and r.json()["job_id"] == "job-1"
    args, kwargs = celery.send_task.call_args
    assert args[0] == "scraper.tasks.run_ingestion" and kwargs["queue"] == "scraper"
    assert kwargs["kwargs"]["sources"] == ["bank_of_canada"]


def test_unknown_command_rejected(client, admin_headers):
    assert client.post("/api/v1/admin/ingest", headers=admin_headers, json={"command": "rm -rf"}).status_code == 422


@pytest.mark.parametrize("url", [
    "http://feeds.partner.example/l.json",
    "https://evil.example/l.json",
    "https://api:8000/api/v1/auth/me",
    "file:///etc/passwd",
])
def test_feed_url_allow_list(client, admin_headers, monkeypatch, url):
    monkeypatch.setattr("app.routers.admin.FEED_ALLOWED_HOSTS", {"feeds.partner.example"})
    with patch("app.routers.admin._celery") as celery:
        r = client.post("/api/v1/admin/feeds", headers=admin_headers, json={"feed_url": url})
    assert r.status_code == 422
    celery.send_task.assert_not_called()


def test_broker_down_is_503(client, admin_headers):
    with patch("app.routers.admin._celery") as celery:
        celery.send_task.side_effect = Exception("broker down")
        r = client.post("/api/v1/admin/insights/retrain", headers=admin_headers)
    assert r.status_code == 503


def test_status_reports_coverage(client, admin_headers):
    with patch("app.routers.admin._celery") as celery:
        celery.control.ping.return_value = [{"celery@insights": {"ok": "pong"}}]
        body = client.get("/api/v1/admin/status", headers=admin_headers).json()
    assert "listings" in body["coverage"] and body["workers"] == ["celery@insights"]
