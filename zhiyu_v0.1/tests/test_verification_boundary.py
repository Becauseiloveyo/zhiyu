# ruff: noqa: F811
import hashlib
import json

import pytest
from alembic import command
from conftest import migration_config
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_response_api import live_authority  # noqa: F401
from test_response_authorization import authority_environment  # noqa: F401
from test_response_gateway import claim, execute
from test_response_planner import ENV, response_environment  # noqa: F401
from test_verification_replan import closed_loop_environment, decide  # noqa: F401
from test_verification_runtime import AT, verification_environment, verifier  # noqa: F401

from zhiyu.api.routes import verification
from zhiyu.core.config import settings
from zhiyu.core.errors import AccessDenied
from zhiyu.db.models import PlanRow
from zhiyu.db.session import get_db
from zhiyu.main import app
from zhiyu.verification.replan import DeterministicReplanner

pytestmark = pytest.mark.postgres


def test_read_api_complete_lineage_metrics_and_scope(closed_loop_environment, monkeypatch):
    engine = closed_loop_environment[0]
    result = decide(closed_loop_environment)
    DeterministicReplanner(engine).handle(ENV, result.verification_id, verifier(), now=AT)
    token = "verification-api-test-" + "d" * 32
    digest = hashlib.sha256(token.encode()).hexdigest()
    monkeypatch.setattr(settings, "service_tokens", {digest: verifier()})
    monkeypatch.setattr(verification, "get_engine", lambda: engine)

    def database():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = database
    try:
        with TestClient(app, headers={"Authorization": "Bearer " + token}) as client:
            read = client.get("/v1/verifications/" + result.verification_id)
            assert read.status_code == 200, read.text
            value = read.json()
            assert value["runtime"]["action_result_id"] and value["state_update"] and value["effectiveness"]
            checks = client.get("/v1/verifications/" + result.verification_spec_id + "/checks?limit=2").json()
            assert len(checks["items"]) == 2 and checks["next_cursor"]
            tail = client.get(
                "/v1/verifications/" + result.verification_spec_id + "/checks",
                params={"after": checks["next_cursor"]},
            ).json()
            assert len(tail["items"]) == 1
            incident = client.get(
                f"/v1/incidents/{result.incident_id}/verifications", params={"environment_id": ENV}
            ).json()
            assert len(incident["items"]) == 1
            timeline = client.get(
                f"/v1/incidents/{result.incident_id}/timeline", params={"environment_id": ENV}
            ).json()
            assert len(timeline["items"][0]["actions"]) == len(timeline["items"][0]["action_results"]) == 4
            measured = client.get("/v1/verification-metrics", params={"environment_id": ENV})
            assert measured.status_code == 200, measured.text
            assert (
                measured.json()["verification_pass"] == 1
                and measured.json()["verification_evidence_count"] == 4
            )
            assert (
                client.post(
                    "/v1/verifications", json={"environment_id": ENV, "command": "arbitrary"}
                ).status_code
                == 422
            )
            monkeypatch.setattr(
                settings,
                "service_tokens",
                {digest: verifier().model_copy(update={"environment_ids": {"outside"}})},
            )
            assert client.get("/v1/verifications/" + result.verification_id).status_code == 404
            assert client.get("/v1/verification-metrics", params={"environment_id": ENV}).status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "table",
    ["verification_specs", "verification_results", "verification_observations", "verification_checks"],
)
def test_managed_verification_immutable(closed_loop_environment, table):
    engine = closed_loop_environment[0]
    decide(closed_loop_environment)
    # Fixed test-owned table identifiers, never user-supplied SQL.
    updates = {
        "verification_specs": "objective_type='CONTAINMENT'",
        "verification_results": "claim='silently overwritten'",
        "verification_observations": "assertion_status='FAIL'",
        "verification_checks": "definition='{}'::jsonb",
    }
    with engine.begin() as connection, pytest.raises(DBAPIError):
        with connection.begin_nested():
            connection.execute(text("UPDATE " + table + " SET " + updates[table]))


def test_0007_roundtrip_preserves_v02_v03_data(authority_environment):
    engine, _ = authority_environment
    execute(engine, claim(engine))
    names = [
        "raw_records",
        "normalized_events",
        "event_groups",
        "correlation_decisions",
        "incidents",
        "plans",
        "tasks",
        "worker_leases",
        "action_requests",
        "action_dispatches",
        "action_execution_results",
        "authorization_contexts",
        "authorization_decisions",
        "evidence",
        "audit_entries",
        "outbox",
    ]

    def snapshot(connection):
        return json.dumps(
            {
                name: connection.scalars(
                    text("SELECT row_to_json(r) FROM " + name + " r ORDER BY row_to_json(r)::text")
                ).all()
                for name in names
            },
            sort_keys=True,
        )

    with engine.begin() as connection:
        before = snapshot(connection)
        for revision in ("0007_execution", "head", "0007_execution", "head"):
            (command.upgrade if revision == "head" else command.downgrade)(
                migration_config(connection), revision
            )
            assert snapshot(connection) == before


def test_check_scope_permission_and_active_policy(verification_environment):
    engine, service, result, spec, _ = verification_environment
    absent = verifier().model_copy(update={"permissions": frozenset()})
    with pytest.raises(AccessDenied):
        service.create(ENV, result, spec, absent, now=AT)
    with pytest.raises(AccessDenied):
        service.claim(ENV, absent, now=AT)
    with Session(engine) as db:
        assert db.scalar(select(PlanRow)).total_model_calls == 0


def test_continuous_plan_request_replay_after_lifecycle_transition(live_authority, monkeypatch):
    engine, original = live_authority
    principal = verifier().model_copy(update={"permissions": verifier().permissions | {"incidents:write"}})
    monkeypatch.setattr(verification, "get_engine", lambda: engine)
    request = verification.ContinuousPlanRequest(
        environment_id=ENV,
        incident_id=original.incident_id,
        expected_version=2,
        scope_id=original.tasks[0].scope_id,
    )
    first = verification.create_plan(request, principal)
    assert verification.create_plan(request, principal) == first
