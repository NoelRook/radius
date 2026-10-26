import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("CHAOS_KEY", "test-key")
os.environ.setdefault("APP_REVISION", "test-sha")

from app.main import app  # noqa: E402

client = TestClient(app)
HEADERS = {"X-Chaos-Key": "test-key"}


@pytest.fixture(autouse=True)
def reset_state():
    client.post("/admin/reset", headers=HEADERS)
    client.post("/admin/chaos", json={"mode": "off", "rate": 0.0}, headers=HEADERS)
    yield
    client.post("/admin/chaos", json={"mode": "off", "rate": 0.0}, headers=HEADERS)


def test_health_reports_revision():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["revision"] == "test-sha"
    assert body["contract"] == "autonomy.yaml"
    assert response.headers["x-radius-revision"] == "test-sha"


def test_quote_works_without_chaos():
    response = client.get("/quote")
    assert response.status_code == 200
    assert "quote" in response.json()


def test_chaos_requires_key():
    response = client.post("/admin/chaos", json={"mode": "error", "rate": 1.0})
    assert response.status_code == 403


def test_chaos_injects_real_errors():
    client.post("/admin/chaos", json={"mode": "error", "rate": 1.0}, headers=HEADERS)
    response = client.get("/work")
    assert response.status_code == 503


def test_metrics_reports_error_rate():
    client.post("/admin/chaos", json={"mode": "error", "rate": 1.0}, headers=HEADERS)
    for _ in range(4):
        client.get("/work")
    metrics = client.get("/metrics").json()
    assert metrics["errors"] >= 4
    assert metrics["error_rate"] > 0.5
    assert metrics["revision"] == "test-sha"


def test_reset_clears_counters():
    client.get("/quote")
    assert client.get("/metrics").json()["requests"] >= 1
    client.post("/admin/reset", headers=HEADERS)
    assert client.get("/metrics").json()["requests"] == 1  # this metrics call
