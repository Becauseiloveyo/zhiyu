"""Gate A uses real PostgreSQL and the existing ingestion/intelligence services."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_incident_api import http_chain
from test_raw_ingest import sensor_principal

from zhiyu.api.routes.product import get_product_db
from zhiyu.core.config import settings
from zhiyu.db.models import ActionRow, AuditEntryRow, IncidentRow, ScopeRow, SensorHealthRow
from zhiyu.db.session import get_db
from zhiyu.main import app
from zhiyu.product import snapshots
from zhiyu.product.access import product_settings
from zhiyu.product.contracts import ReadGrant

pytestmark = pytest.mark.postgres
TOKEN = "product-test-only-" + "x" * 40
ENV = "lab-zhiyu-01"
PARAMS = {"environment_id": ENV, "hours": 168}


@pytest.fixture
def client(bootstrapped, monkeypatch):
    principal = sensor_principal().model_copy(
        update={"permissions": sensor_principal().permissions | {"product:read"}}
    )
    monkeypatch.setattr(settings, "service_tokens", {hashlib.sha256(TOKEN.encode()).hexdigest(): principal})
    monkeypatch.setattr(
        product_settings,
        "grants",
        {principal.principal_id: {ENV: ReadGrant(version="test-1", scope_ids={"scope-lab-web"})}},
    )

    def normal():
        with Session(bootstrapped) as db:
            yield db

    def readonly():
        with bootstrapped.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                with Session(bind=connection) as db:
                    yield db

    app.dependency_overrides[get_db] = normal
    app.dependency_overrides[get_product_db] = readonly
    try:
        with TestClient(app, headers={"Authorization": "Bearer " + TOKEN}) as result:
            yield result
    finally:
        app.dependency_overrides.clear()


def get(client, path, **params):
    return client.get("/v1/product" + path, params={**PARAMS, **params})


def test_real_chain_snapshot_and_no_business_writes(client, bootstrapped):
    incident = http_chain(client)
    with Session(bootstrapped) as db:
        before = db.scalar(select(func.count()).select_from(AuditEntryRow))
    page = get(client, "/incidents")
    assert page.status_code == 200, page.text
    assert [r["incident_id"] for r in page.json()["items"]] == [incident]
    assert page.json()["items"][0]["risk_score"] == 62
    result = get(client, f"/incidents/{incident}/snapshot")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["consistency"] == "IMMUTABLE_SNAPSHOT"
    assert body["content_sha256"] == snapshots.digest(body["facts"])
    kinds = {r["kind"] for r in body["facts"]}
    assert {
        "incident",
        "resource",
        "raw",
        "normalization",
        "event",
        "evidence",
        "group",
        "correlation",
    } <= kinds
    for forbidden in ('"raw_ref"', '"content_ref"', '"content"', '"parameters"', "db://", TOKEN):
        assert forbidden not in result.text
    cached = get(client, "/snapshots/" + body["snapshot_id"])
    assert cached.json() == body
    overview = get(client, "/overview").json()
    assert overview["metrics"]["incidents"] == 1
    assert overview["metrics"]["associated_events"] == 3
    assert overview["protection_score"] is None
    with Session(bootstrapped) as db:
        assert db.scalar(select(func.count()).select_from(AuditEntryRow)) == before
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0


def test_read_grants_and_environment_isolation(client, monkeypatch):
    incident = http_chain(client)
    for suffix in ("/incidents", "/overview", "/runtime-health", f"/incidents/{incident}/snapshot"):
        assert get(client, suffix, environment_id="foreign").status_code == 403
        assert get(client, suffix, scope_id="foreign-scope").status_code == 403
    assert get(client, "/incidents/missing/snapshot").status_code == 404
    monkeypatch.setattr(product_settings, "grants", {})
    assert get(client, "/incidents").status_code == 403


def test_mixed_scope_hidden_in_lists_counts_detail_and_cached_snapshot(client, bootstrapped):
    incident = http_chain(client)
    snapshot = get(client, f"/incidents/{incident}/snapshot").json()["snapshot_id"]
    with Session(bootstrapped) as db:
        row = db.get(IncidentRow, incident)
        row.affected_asset_ids = [*row.affected_asset_ids, "foreign-resource"]
        db.commit()
    assert get(client, "/incidents").json()["items"] == []
    assert get(client, "/overview").json()["metrics"]["incidents"] == 0
    assert get(client, f"/incidents/{incident}/snapshot").status_code == 404
    assert get(client, f"/snapshots/{snapshot}").status_code == 404


def test_snapshot_frozen_then_grant_revoked_and_expired(client, bootstrapped, monkeypatch):
    incident = http_chain(client)
    body = get(client, f"/incidents/{incident}/snapshot").json()
    with Session(bootstrapped) as db:
        db.get(IncidentRow, incident).title = "changed after capture"
        db.commit()
    assert get(client, "/snapshots/" + body["snapshot_id"]).json() == body
    monkeypatch.setattr(
        product_settings,
        "grants",
        {"sensor-tests": {ENV: ReadGrant(version="changed", whole_environment=True)}},
    )
    assert get(client, "/snapshots/" + body["snapshot_id"]).status_code == 404
    assert get(client, "/snapshots/unknown").status_code == 410


def test_keyset_ties_query_binding_and_filters(client, bootstrapped):
    identifier = http_chain(client)
    with Session(bootstrapped) as db:
        source = db.get(IncidentRow, identifier)
        values = {column.name: getattr(source, column.name) for column in IncidentRow.__table__.columns}
        for i in range(4):
            db.add(IncidentRow(**{**values, "incident_id": f"test-page-{i}"}))
        db.commit()
    first = get(client, "/incidents", limit=2, search="test-page")
    assert first.status_code == 200, first.text
    pages = [first.json()]
    while pages[-1]["next_cursor"]:
        pages.append(
            get(client, "/incidents", limit=2, search="test-page", cursor=pages[-1]["next_cursor"]).json()
        )
    assert [i["incident_id"] for p in pages for i in p["items"]] == [f"test-page-{i}" for i in (3, 2, 1, 0)]
    cursor = first.json()["next_cursor"]
    for override in ({"search": "changed"}, {"sort": "created_asc"}, {"priority": "P4"}):
        assert get(client, "/incidents", cursor=cursor, **override).status_code == 422
    assert get(client, "/incidents", search="%").json()["items"] == []
    assert get(client, "/incidents", status="CLOSED").json()["items"] == []
    for params in ({"cursor": "bad"}, {"limit": 201}, {"hours": 169}, {"priority": "bad"}):
        assert get(client, "/incidents", **params).status_code == 422


def test_stale_sensor_never_healthy_and_ai_default_off(client, bootstrapped):
    with Session(bootstrapped) as db:
        for row in db.scalars(select(SensorHealthRow)):
            row.status = "HEALTHY"
            row.last_heartbeat_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()
    result = get(client, "/runtime-health")
    assert result.status_code == 200, result.text
    assert result.json()["runtime_status"] == "UNKNOWN"
    assert result.json()["ai_mode"] == "OFF"
    assert all(s["effective_status"] == "UNKNOWN" for s in result.json()["sensors"])


def test_historical_scope_expiry_does_not_grant_new_execution(client, bootstrapped):
    incident = http_chain(client)
    with Session(bootstrapped) as db:
        scope = db.get(ScopeRow, ("scope-lab-web", ENV))
        scope.valid_until = datetime.now(UTC) - timedelta(hours=1)
        db.commit()
    assert get(client, f"/incidents/{incident}/snapshot").status_code == 200


def test_anonymous_and_reader_cannot_call_business_write(client, monkeypatch):
    principal = sensor_principal().model_copy(update={"permissions": frozenset({"product:read"})})
    monkeypatch.setattr(settings, "service_tokens", {hashlib.sha256(TOKEN.encode()).hexdigest(): principal})
    assert get(client, "/incidents").status_code == 200
    assert client.post("/v1/intelligence/process", json={"environment_id": ENV}).status_code == 403
    assert client.get("/v1/product/access", headers={"Authorization": ""}).status_code == 401


def test_explicit_sql_allowlist_and_secret_redaction():
    from zhiyu.product.registry import SPECS, columns, public_value

    sensitive = {
        "content",
        "input_body",
        "output",
        "configuration",
        "parameters",
        "locator",
        "content_ref",
        "raw_ref",
    }
    for kind in SPECS:
        assert not sensitive.intersection(c.key for c in columns(kind))
    assert (
        public_value("token=never-publish password=never-publish Bearer never-publish")
        == "[REDACTED] [REDACTED] [REDACTED]"
    )
