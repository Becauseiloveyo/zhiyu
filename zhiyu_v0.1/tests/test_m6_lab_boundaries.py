# ruff: noqa: F811
"""Fail-closed boundaries for the opt-in Lab primitive; prior tests are untouched."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session
from test_m6_lab_remediation import (  # noqa: F401
    ENV,
    SCOPE,
    action_for,
    dispatch,
    lab_environment,
    make_plan,
    run_verification,
)

from zhiyu.core.errors import ConflictError
from zhiyu.db.models import EnvironmentRow, ScopeRow
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.gateway import ActionGateway
from zhiyu.response.lab_client import LabClient
from zhiyu.response.lab_target import LabState
from zhiyu.response.scheduler import TaskScheduler
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.policy import VerificationPolicy, validate_spec
from zhiyu.verification.runtime import VerificationService, containment_spec


@pytest.mark.postgres
@pytest.mark.parametrize("boundary", ["production", "observe_only", "scope", "target_binding"])
def test_lab_state_change_fail_closed_before_target(lab_environment, monkeypatch, boundary):
    from zhiyu.core.config import settings

    engine, principal, _, state, *_ = lab_environment
    make_plan(lab_environment)
    with Session(engine) as db:
        claim = TaskScheduler(db).claim(ENV, principal)
    if boundary == "target_binding":
        monkeypatch.setattr(settings, "lab_targets", {})
    else:
        with Session(engine) as db, db.begin():
            if boundary == "production":
                db.get(EnvironmentRow, ENV).deployment_stage = "PRODUCTION"
            elif boundary == "observe_only":
                db.get(EnvironmentRow, ENV).autonomy_mode = "OBSERVE_ONLY"
            else:
                db.get(ScopeRow, (SCOPE, ENV)).valid_until = datetime.now(UTC) - timedelta(seconds=1)
    with Session(engine) as db:
        decision = AuthorizationService(db).authorize_task(
            ENV, claim["task_id"], generation=claim["generation"], principal=principal
        )
    assert decision.outcome == "DENY"
    result = ActionGateway(engine).dispatch(
        ENV, claim["task_id"], claim["generation"], decision.authorization_id, principal
    )
    assert result["execution_outcome"] == ("STALE" if boundary == "scope" else "DENIED")
    assert state.mutations == 0 and result["executor"] == "NOT_DISPATCHED"


@pytest.mark.postgres
def test_lab_target_restart_invalidates_old_epoch_and_never_restores_containment(lab_environment):
    lab = lab_environment
    make_plan(lab)
    result, *_ = dispatch(lab)
    action = action_for(lab[0], result)
    restarted = LabState(ENV, action.target.resource_id)
    assert not restarted.snapshot()["restricted"]
    with pytest.raises(ValueError, match="state_compare_failed"):
        restarted.apply(LabClient(action).command())
    assert restarted.mutations == 0


@pytest.mark.postgres
def test_containment_rejects_action_worker_and_detection_substitution(lab_environment):
    lab = lab_environment
    engine, principal, verifier, *_ = lab
    make_plan(lab)
    result, *_ = dispatch(lab)
    with Session(engine) as db:
        sensors = db.get(EnvironmentRow, ENV).required_sensor_ids
    spec = containment_spec(action_for(engine, result), sensors)
    bad = spec.model_copy(deep=True)
    bad.checks[0].capability_id = "state_snapshot_check"
    with pytest.raises(ValueError):
        validate_spec(bad)
    bad = spec.model_copy(deep=True)
    bad.checks[0].assertions[0].expected = 200
    with pytest.raises(ValueError):
        validate_spec(bad)
    service = VerificationService(engine)
    service.create(ENV, result["attempt_id"], spec, verifier, VerificationPolicy(minimum_window_seconds=1))
    claim = service.claim(ENV, principal, spec_id=spec.verification_spec_id)
    assert claim
    with pytest.raises(ConflictError, match="different worker"):
        service.run_claim(ENV, claim, principal)


@pytest.mark.postgres
def test_containment_stale_independent_evidence_never_passes(lab_environment):

    lab = lab_environment
    engine, _, verifier, *_ = lab
    make_plan(lab, ttl=60)
    result, *_ = dispatch(lab)
    with Session(engine) as db:
        sensors = db.get(EnvironmentRow, ENV).required_sensor_ids
    spec = containment_spec(action_for(engine, result), sensors)
    service = VerificationService(engine)
    service.create(
        ENV,
        result["attempt_id"],
        spec,
        verifier,
        VerificationPolicy(minimum_window_seconds=1, evidence_ttl_seconds=5),
    )
    from test_m6_lab_remediation import fresh_sensor_window

    fresh_sensor_window(engine)
    import time

    for _ in range(100):
        claim = service.claim(ENV, verifier, spec_id=spec.verification_spec_id)
        if claim:
            service.run_claim(ENV, claim, verifier)
        else:
            time.sleep(0.02)
    # Explicit decision-time boundary: no fresh observations are collected after their expiry.
    verdict = VerificationEngine(engine).decide(
        ENV, spec.verification_spec_id, verifier, now=datetime.now(UTC) + timedelta(seconds=6)
    )
    assert verdict.status == "INCONCLUSIVE"


@pytest.mark.postgres
def test_compensation_with_fresh_digest_still_cannot_release_other_owner(lab_environment):
    lab = lab_environment
    make_plan(lab)
    first, *_ = dispatch(lab)
    make_plan(lab, prior=first["action_id"])
    dispatch(lab)
    make_plan(lab)
    other, *_ = dispatch(lab)
    mutations = lab[3].mutations
    make_plan(lab, prior=first["action_id"], revision="foreign-owner-current-digest")
    result, *_ = dispatch(lab)
    assert result["execution_outcome"] == "EXECUTION_UNKNOWN"
    assert lab[3].mutations == mutations
    assert lab[3].snapshot()["owner"] == "zhiyu-lab:" + other["action_id"]


@pytest.mark.postgres
def test_absent_receipt_is_not_failure_while_original_command_can_still_arrive(lab_environment):
    from zhiyu.response.lab_reconcile import compare

    lab = lab_environment
    make_plan(lab)
    result, *_ = dispatch(lab)
    action = action_for(lab[0], result).model_copy(
        update={"action_id": "still-in-flight", "ownership_tag": "zhiyu-lab:still-in-flight"}
    )
    observed = LabClient(action).request("GET")
    assert observed["receipt"] is None
    assert compare(action, observed) == ("UNKNOWN", "inflight_command_window_not_closed")


@pytest.mark.postgres
def test_migration_downgrade_refuses_to_erase_lab_receipt(lab_environment):
    import runpy
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    lab = lab_environment
    make_plan(lab)
    result, *_ = dispatch(lab)
    migration = runpy.run_path(str(Path(__file__).parents[1] / "migrations/versions/0016_lab_remediation.py"))
    with lab[0].begin() as connection:
        with pytest.raises(IntegrityError):
            with connection.begin_nested(), Operations.context(MigrationContext.configure(connection)):
                migration["downgrade"]()
        assert (
            connection.scalar(
                text("SELECT side_effect FROM action_execution_results WHERE attempt_id=:attempt"),
                {"attempt": result["attempt_id"]},
            )
            == "LAB_PATH"
        )
        definition = connection.scalar(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid='action_execution_results'::regclass "
                "AND conname='ck_action_execution_results_action_result_read_only'"
            )
        )
        assert "LAB_PATH" in definition


@pytest.mark.postgres
@pytest.mark.parametrize("fault", ["invalid_status", "trickled_body"])
def test_lab_transport_faults_are_bounded_and_leave_target_unchanged(lab_environment, monkeypatch, fault):
    import time

    lab = lab_environment
    make_plan(lab)
    result, *_ = dispatch(lab)
    action = action_for(lab[0], result)
    mutations = lab[3].mutations

    def broken_read(handler):
        try:
            if fault == "invalid_status":
                handler.wfile.write(b"invalid status\r\n\r\n")
            else:
                handler.wfile.write(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n")
                for _ in range(30):
                    handler.wfile.write(b" ")
                    handler.wfile.flush()
                    time.sleep(0.2)
        except OSError:
            pass

    monkeypatch.setattr(lab[4].RequestHandlerClass, "do_GET", broken_read)
    started = time.monotonic()
    with pytest.raises((ValueError, TimeoutError, OSError)):
        LabClient(action).request("GET")
    assert time.monotonic() - started < 4.5
    assert lab[3].mutations == mutations
