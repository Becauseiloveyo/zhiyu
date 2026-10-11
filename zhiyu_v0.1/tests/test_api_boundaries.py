import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from zhiyu.api.routes import health
from zhiyu.core.config import settings
from zhiyu.db.session import get_db
from zhiyu.main import app

TOKEN = "synthetic-test-token-" + "a" * 32


@pytest.fixture
def authorized_client(monkeypatch, principal):
    monkeypatch.setattr(settings, "service_tokens", {hashlib.sha256(TOKEN.encode()).hexdigest(): principal})
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {TOKEN}"
        yield client


def test_liveness_survives_missing_driver_and_unavailable_db(monkeypatch):
    def missing_driver():
        raise ModuleNotFoundError("synthetic missing driver")

    monkeypatch.setattr(health, "get_engine", missing_driver)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503


def test_readiness_database_unreachable(monkeypatch):
    engine = create_engine(
        "postgresql+psycopg://unused:unused@127.0.0.1:1/unused", connect_args={"connect_timeout": 1}
    )
    monkeypatch.setattr(health, "get_engine", lambda: engine)
    try:
        with TestClient(app) as client:
            result = client.get("/ready")
            assert result.status_code == 503
            assert "unused" not in result.text
            assert client.get("/health").status_code == 200
    finally:
        engine.dispose()


def test_business_api_disabled_without_identity_config(monkeypatch):
    monkeypatch.setattr(settings, "service_tokens", {})
    with TestClient(app) as client:
        assert client.get("/v1/incidents/any").status_code == 503


def test_unauthenticated_and_invalid_body(authorized_client, event):
    authorized_client.headers.pop("Authorization")
    assert (
        authorized_client.post(
            "/v1/events/batches", json={"events": [event.model_dump(mode="json")]}
        ).status_code
        == 401
    )
    authorized_client.headers["Authorization"] = f"Bearer {TOKEN}"
    invalid = event.model_dump(mode="json")
    invalid["severity_signal"] = "sensitive-raw-example"
    result = authorized_client.post("/v1/events/batches", json={"events": [invalid]})
    assert result.status_code == 422 and "sensitive-raw-example" not in result.text


def test_streamed_oversize_body_is_rejected(authorized_client):
    result = authorized_client.post(
        "/v1/events/batches", content=iter([b"a" * settings.max_body_bytes, b"x"])
    )
    assert result.status_code == 413


@pytest.mark.postgres
def test_http_ingest_duplicates_reference_rejection_and_ready(
    bootstrapped, authorized_client, event, monkeypatch
):
    def db_override():
        with Session(bootstrapped) as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    monkeypatch.setattr(health, "get_engine", lambda: bootstrapped)
    try:
        assert authorized_client.get("/ready").status_code == 200
        payload = {"events": [event.model_dump(mode="json")]}
        first = authorized_client.post("/v1/events/batches", json=payload)
        assert first.status_code == 202 and first.json()["accepted"] == 1
        assert authorized_client.post("/v1/events/batches", json=payload).json()["duplicates"] == 1
        payload["events"][0]["collector_id"] = "spoofed"
        assert authorized_client.post("/v1/events/batches", json=payload).status_code == 403
        assert authorized_client.get("/v1/incidents/missing").status_code == 404
    finally:
        app.dependency_overrides.clear()
