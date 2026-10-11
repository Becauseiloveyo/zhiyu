# ruff: noqa: F811
"""Dispatch-time revocation, approval parking, explicit control CAS and v0.2 migration preservation."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from conftest import migration_config
from sqlalchemy import text
from sqlalchemy.orm import Session
from test_event_intelligence import process
from test_incident_engine import chain, promote
from test_response_authorization import (  # noqa: F401
    authority_environment,
    claim_fixture,
    response_environment,
)
from test_response_gateway import CountingRegistry, authorize, claim
from test_response_planner import ENV, INSTANT, SCOPE, response_principal

from zhiyu.core.errors import ConflictError
from zhiyu.db.models import EnvironmentRow, ScopeRow, TaskRow
from zhiyu.db.response_authority import ResponseControlRow
from zhiyu.response import gateway
from zhiyu.response.admin import ControlRequest, configure
from zhiyu.response.gateway import ActionGateway

pytestmark = pytest.mark.postgres


def test_no_adapter_call_if_scope_changes_after_durable_intent(authority_environment, monkeypatch):
    engine, _ = authority_environment
    lease = claim(engine)
    decision = authorize(engine, lease["task_id"])
    registry = CountingRegistry(engine)
    original = gateway.assert_current

    def changed(db, *args):
        db.get(ScopeRow, (SCOPE, ENV)).version = "changed-at-boundary"
        original(db, *args)

    monkeypatch.setattr(gateway, "assert_current", changed)
    result = ActionGateway(engine, registry).dispatch(
        ENV, lease["task_id"], 1, decision.authorization_id, response_principal(), now=INSTANT
    )
    assert result["error_code"] == "dispatch_authority_changed"
    assert registry.calls == 0 and result["executor_ms"] == 0


def test_revocation_after_executor_does_not_erase_receipt(authority_environment, monkeypatch):
    engine, _ = authority_environment
    lease = claim(engine)
    decision = authorize(engine, lease["task_id"])
    service = ActionGateway(engine)
    original = service.complete

    def revoke(*args, **kwargs):
        with Session(engine) as db, db.begin():
            db.get(ResponseControlRow, ENV).enabled = False
        return original(*args, **kwargs)

    monkeypatch.setattr(service, "complete", revoke)
    result = service.dispatch(
        ENV, lease["task_id"], 1, decision.authorization_id, response_principal(), now=INSTANT
    )
    assert result["execution_outcome"] == "EXECUTION_SUCCESS"
    with Session(engine) as db:
        assert db.get(TaskRow, lease["task_id"]).status == "SUCCEEDED"


def test_production_probe_parks_for_approval_without_executor(authority_environment):
    engine, _ = authority_environment
    with Session(engine) as db, db.begin():
        db.get(EnvironmentRow, ENV).deployment_stage = "PRODUCTION"
    task_id = claim_fixture(authority_environment, "safe_http_probe")
    decision = authorize(engine, task_id)
    assert decision.outcome == "REQUIRE_APPROVAL"
    registry = CountingRegistry(engine)
    result = ActionGateway(engine, registry).dispatch(
        ENV, task_id, 1, decision.authorization_id, response_principal(), now=INSTANT
    )
    assert result["task_status"] == "WAITING_APPROVAL" and registry.calls == 0
    with Session(engine) as db:
        row = db.get(TaskRow, task_id)
        assert row.status == "WAITING_APPROVAL" and row.active_lease_id is None


def test_control_operator_cas_preserves_scope_and_environment(authority_environment):
    engine, _ = authority_environment
    now = datetime.now(UTC)
    with Session(engine) as db:
        old = db.get(ResponseControlRow, ENV)
        request = ControlRequest(
            environment_id=ENV,
            expected_version=old.row_version,
            policy_version=old.policy_version,
            enabled=False,
            configuration=old.configuration,
            valid_from=now - timedelta(minutes=1),
            valid_until=now + timedelta(hours=1),
        )
        env_version = db.get(EnvironmentRow, ENV).version
    with Session(engine) as db:
        assert configure(db, request, response_principal()) == request.expected_version + 1
    with Session(engine) as db, pytest.raises(ConflictError):
        configure(db, request, response_principal())
    with Session(engine) as db:
        assert db.get(EnvironmentRow, ENV).version == env_version


def test_v02_data_survives_m3_upgrade_downgrade_upgrade(bootstrapped):
    engine = bootstrapped
    # Populate only v0.2 structures, then remove empty M3 metadata to start at actual 0004.
    chain(engine)
    process(engine)
    promote(engine)
    tables = [
        "raw_records",
        "normalized_events",
        "event_groups",
        "event_group_members",
        "correlation_decisions",
        "incidents",
        "incident_events",
        "evidence",
        "audit_entries",
        "outbox",
    ]

    def snapshot(connection):
        return json.dumps(
            {
                t: connection.scalars(
                    text("SELECT row_to_json(r) FROM " + t + " r ORDER BY row_to_json(r)::text")
                ).all()
                for t in tables
            },
            sort_keys=True,
        )

    with engine.begin() as connection:
        command.downgrade(migration_config(connection), "0004_incidents")
        original = snapshot(connection)
        for destination in ("head", "0004_incidents", "head"):
            if destination == "head":
                command.upgrade(migration_config(connection), destination)
            else:
                command.downgrade(migration_config(connection), destination)
            assert snapshot(connection) == original
