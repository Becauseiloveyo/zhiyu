from fastapi.testclient import TestClient

from zhiyu.main import app


def test_health():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["architecture_baseline"] == "2026.09.12-ai.5"
    assert body["ai_enabled"] is False
