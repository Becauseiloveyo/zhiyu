"""Real HTTP routes over PostgreSQL with fresh synthetic evidence; no clock override in API."""

# ruff: noqa: F811
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_response_authorization import authority_environment, response_environment  # noqa: F401
from test_response_planner import ENV, SCOPE, response_principal

from zhiyu.api.routes import response
from zhiyu.core.config import settings
from zhiyu.db.session import get_db
from zhiyu.main import app

pytestmark = pytest.mark.postgres
TOKEN = "synthetic-response-api-token-" + "c" * 32


@pytest.fixture
def live_authority(monkeypatch, request):
    import test_event_intelligence as events
    import test_incident_engine as incidents
    import test_response_authorization as authority
    import test_response_planner as plans

    # Keep this three-event fixture within one fixed correlation window, even when
    # the real clock is near a five-minute boundary. API time remains the real clock.
    base = (datetime.now(UTC) - timedelta(seconds=115)).replace(second=0, microsecond=0)
    for module in (events, incidents, plans):
        monkeypatch.setattr(module, "NOW", base)
    for module in (plans, authority):
        monkeypatch.setattr(module, "INSTANT", base + timedelta(seconds=110))
    monkeypatch.setattr(
        plans, "process", lambda engine: events.process(engine, now=base + timedelta(seconds=90))
    )
    return request.getfixturevalue("authority_environment")


@pytest.fixture
def client(live_authority, monkeypatch):
    engine, _ = live_authority
    monkeypatch.setattr(
        settings, "service_tokens", {hashlib.sha256(TOKEN.encode()).hexdigest(): response_principal()}
    )
    monkeypatch.setattr(response, "get_engine", lambda: engine)

    def db_override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    try:
        with TestClient(app, headers={"Authorization": "Bearer " + TOKEN}) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_api_lease_authorization_gateway_replay_and_worker_tick(client, live_authority):
    _, plan = live_authority
    body = {"environment_id": ENV}
    lease = client.post("/v1/response/claim", json=body).json()["lease"]
    task_id = lease["task_id"]
    decision_response = client.post(f"/v1/tasks/{task_id}/authorizations", json={**body, "generation": 1})
    assert decision_response.status_code == 200, decision_response.text
    decision = decision_response.json()
    assert decision["outcome"] == "ALLOW"
    execute = {
        **body,
        "generation": 1,
        "authorization_id": decision["authorization_id"],
        "action_digest": decision["action_digest"],
    }
    assert (
        client.post(f"/v1/tasks/{task_id}/execute", json={**execute, "command": "forbidden"}).status_code
        == 422
    )
    first = client.post(f"/v1/tasks/{task_id}/execute", json=execute)
    assert first.status_code == 200 and first.json()["execution_outcome"] == "EXECUTION_SUCCESS", first.text
    retry = client.post(f"/v1/tasks/{task_id}/execute", json=execute).json()
    assert retry["disposition"] == "DUPLICATE" and retry["attempt_id"] == first.json()["attempt_id"]
    action = client.get("/v1/actions/" + first.json()["action_id"]).json()
    assert len(action["results"]) == 1 and action["authorization_inputs"]["generation"] == 1
    for _ in range(2):
        result = client.post("/v1/response/worker/tick", json=body)
        assert (
            result.status_code == 200 and result.json()["result"]["execution_outcome"] == "EXECUTION_SUCCESS"
        ), result.text
    tasks = client.get("/v1/tasks", params={**body, "status": "SUCCEEDED"}).json()["items"]
    assert len(tasks) == 3
    assert client.get("/v1/plans/" + plan.plan_id).json()["plan"]["total_model_calls"] == 0


def test_api_plan_idempotency_stable_pages_and_scope_no_leak(client, live_authority, monkeypatch):
    _, plan = live_authority
    body = {"environment_id": ENV, "scope_id": SCOPE, "expected_version": 2}
    url = f"/v1/incidents/{plan.incident_id}/plans"
    first = client.post(url, json=body)
    assert first.status_code == 200, first.text
    assert first.json() == client.post(url, json=body).json()
    for path, key, count in [("tasks", "task_id", 7), ("capabilities", "definition", 5)]:
        items, cursor = [], None
        while True:
            params = {"environment_id": ENV, "limit": 2}
            if cursor:
                params["cursor"] = cursor
            page = client.get("/v1/" + path, params=params).json()
            items += page["items"]
            cursor = page["next_cursor"]
            if cursor is None:
                break
        identities = [x[key]["capability_id"] if key == "definition" else x[key] for x in items]
        assert len(set(identities)) == len(items) == count
        if path == "capabilities":
            assert all(
                x["health"]["status"] == "HEALTHY" and x["health_history"]["last_success"] for x in items
            )
        for extra in ({"cursor": "bad"}, {"limit": 0}, {"limit": 201}):
            assert client.get("/v1/" + path, params={"environment_id": ENV, **extra}).status_code == 422
    principal = response_principal().model_copy(update={"environment_ids": frozenset({"other"})})
    monkeypatch.setattr(settings, "service_tokens", {hashlib.sha256(TOKEN.encode()).hexdigest(): principal})
    for path in ("plans/" + plan.plan_id, "tasks/" + plan.tasks[0].task_id, "actions/missing"):
        assert client.get("/v1/" + path).status_code == 404
    assert client.get("/v1/tasks", params={"environment_id": ENV}).status_code == 403
    assert client.post("/v1/response/claim", json={"environment_id": ENV}).status_code == 403
    assert (
        client.post(
            "/v1/response/worker/tick",
            json={"environment_id": ENV},
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 401
    )
