"""Gate B: real PostgreSQL intent/authorization persistence, no executor dispatch."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_response_planner import (  # noqa: F401
    ENV,
    INSTANT,
    SCOPE,
    create_plan,
    response_environment,
    response_principal,
)

from zhiyu.core.errors import AccessDenied, ConflictError, LeaseLostError, ReferenceError
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import (
    ActionAttemptRow,
    ActionRow,
    AuthorizationContextRow,
    AuthorizationDecisionRow,
    CapabilityHealthRow,
    EnvironmentRow,
    ResourceRow,
    SensorHealthRow,
    TaskRow,
    WorkerLeaseRow,
)
from zhiyu.db.response_authority import (
    ActionControlRow,
    AuthorizationSnapshotRow,
    CapabilityConfigRow,
    ResponseControlRow,
)
from zhiyu.db.response_planning import TaskRuntimeRow
from zhiyu.domain.contracts import ActionRequest, AuthorizationContext, CapabilityHealth, Risk, SensorHealth
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.catalog import INPUTS
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.planner import PlannerPolicy
from zhiyu.response.policy import RiskPolicyGate
from zhiyu.response.registry import CapabilityRegistry


@pytest.fixture
def authority_environment(response_environment):  # noqa: F811
    engine, _ = response_environment
    principal = response_principal()
    with Session(engine) as db:
        CapabilityRegistry(db).install(ENV, principal)
    with Session(engine) as db, db.begin():
        env = db.get(EnvironmentRow, ENV)
        env.max_auto_risk, env.autonomy_mode, env.active_validation = (
            "R2",
            "CONTROLLED_AUTONOMY",
            "ISOLATED_ONLY",
        )
        policy = ResponsePolicy(worker_sources={principal.principal_id: "validation-a"})
        db.add(
            ResponseControlRow(
                environment_id=ENV,
                policy_version=env.policy_version,
                enabled=True,
                configuration=policy.model_dump(mode="json"),
                valid_from=INSTANT - timedelta(minutes=1),
                valid_until=INSTANT + timedelta(hours=1),
                next_probe_at=INSTANT,
            )
        )
        for sensor_id in env.required_sensor_ids:
            sensor = SensorHealth(
                sensor_id=sensor_id,
                environment_id=ENV,
                status="HEALTHY",
                last_heartbeat_at=INSTANT,
                last_event_at=INSTANT,
                lag_seconds=0,
                lost_event_count=0,
                coverage_scope_ids=[SCOPE],
                coverage_validated=True,
                config_version="SYNTHETIC-AUTHORIZATION-FIXTURE",
            )
            db.add(SensorHealthRow(**values_for(sensor, SensorHealthRow)))
    for capability in INPUTS:
        with Session(engine) as db:
            CapabilityRegistry(db).record_health(
                CapabilityHealth(
                    capability_id=capability,
                    capability_version="1.0.0",
                    environment_id=ENV,
                    worker_pool="response",
                    status="HEALTHY",
                    checked_at=INSTANT,
                    latency_ms=1,
                    queue_depth=0,
                    running_count=0,
                    detail="SYNTHETIC fixture",
                ),
                principal,
            )
    plan = create_plan(
        response_environment,
        policy=PlannerPolicy(policy_version="response-plan/probe", include_http_probe=True),
    )
    return engine, plan


def claim_fixture(fixture, capability="collect_resource_context"):
    engine, plan = fixture
    task = next(t for t in plan.tasks if t.capability_id == capability)
    with Session(engine) as db, db.begin():
        row = db.get(TaskRow, task.task_id)
        lease = WorkerLeaseRow(
            lease_id="lease-" + task.task_id,
            task_id=task.task_id,
            worker_id=response_principal().principal_id,
            generation=1,
            acquired_at=INSTANT,
            expires_at=INSTANT + timedelta(seconds=20),
            renewed_at=None,
        )
        db.add(lease)
        db.flush()
        row.status, row.worker_id, row.active_lease_id, row.attempt_count = (
            "RUNNING",
            lease.worker_id,
            lease.lease_id,
            1,
        )
        db.get(TaskRuntimeRow, task.task_id).generation = 1
    return task.task_id


def authorize(engine, task_id, *, now=INSTANT, principal=None):
    with Session(engine) as db:
        return AuthorizationService(db).authorize_task(
            ENV, task_id, generation=1, principal=principal or response_principal(), now=now
        )


@pytest.mark.postgres
@pytest.mark.parametrize(
    "capability,risk",
    [("collect_resource_context", "R0"), ("query_event_history", "R1"), ("safe_http_probe", "R2")],
)
def test_valid_low_risk_authorization_snapshot_and_explanation(authority_environment, capability, risk):
    engine, _ = authority_environment
    task_id = claim_fixture(authority_environment, capability)
    decision = authorize(engine, task_id)
    assert decision.outcome == "ALLOW" and decision.assessed_risk == risk
    again = authorize(engine, task_id)
    assert again.action_id == decision.action_id
    with Session(engine) as db:
        snapshot = db.get(AuthorizationSnapshotRow, decision.authorization_context_id)
        assert snapshot.inputs["lease_id"] == "lease-" + task_id
        assert snapshot.inputs["generation"] == 1 and snapshot.inputs["task"]["task_id"] == task_id
        assert snapshot.inputs["environment"]["environment_id"] == ENV
        assert snapshot.inputs["capability_health_snapshot"]["status"] == "HEALTHY"
        assert snapshot.rule_id == "response-policy/1.0.0" and snapshot.denied_dimensions == []
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 1
        assert db.scalar(select(func.count()).select_from(AuthorizationContextRow)) == 2
        assert db.scalar(select(func.count()).select_from(ActionAttemptRow)) == 0


@pytest.mark.postgres
def test_production_r2_requires_approval_without_execution(authority_environment):
    engine, _ = authority_environment
    task_id = claim_fixture(authority_environment, "safe_http_probe")
    with Session(engine) as db, db.begin():
        db.get(EnvironmentRow, ENV).deployment_stage = "PRODUCTION"
    decision = authorize(engine, task_id)
    assert decision.outcome == "REQUIRE_APPROVAL" and decision.human_approval_required
    with Session(engine) as db:
        assert db.get(ActionControlRow, decision.action_id).status == "WAITING_APPROVAL"


@pytest.mark.postgres
@pytest.mark.parametrize(
    "case,reason",
    [
        ("scope", "scope_mismatch"),
        ("target", "target_not_authorized"),
        ("health", "capability_unavailable"),
        ("sensor", "sensor_health_below_threshold"),
        ("impact", "business_impact_too_high"),
        ("autonomy", "insufficient_autonomy"),
        ("active_disabled", "active_validation_disabled"),
        ("stale_policy", "policy_version_mismatch"),
        ("source", "worker_source_binding_mismatch"),
        ("parameters", "invalid_structured_parameters"),
    ],
)
def test_persisted_denial_dimensions(authority_environment, case, reason):
    engine, _ = authority_environment
    task_id = claim_fixture(authority_environment, "safe_http_probe")
    # Create authorized immutable intent first, then change an authority dimension.
    first = authorize(engine, task_id)
    assert first.outcome == "ALLOW"
    with Session(engine) as db, db.begin():
        if case == "scope":
            db.get(EnvironmentRow, ENV).scope_ids = []
        elif case == "target":
            db.get(ResourceRow, ("target-a", ENV)).binding_version += 1
        elif case == "health":
            db.get(CapabilityHealthRow, ("safe_http_probe", "1.0.0", ENV, "response")).status = "OFFLINE"
        elif case == "sensor":
            db.scalars(select(SensorHealthRow)).first().status = "DEGRADED"
        elif case == "impact":
            db.get(CapabilityConfigRow, ("safe_http_probe", "1.0.0")).business_impact = "HIGH"
        elif case == "autonomy":
            db.get(EnvironmentRow, ENV).autonomy_mode = "OBSERVE_ONLY"
        elif case == "active_disabled":
            db.get(EnvironmentRow, ENV).active_validation = "DISABLED"
        elif case == "stale_policy":
            db.get(EnvironmentRow, ENV).policy_version = "changed"
        elif case == "source":
            control = db.get(ResponseControlRow, ENV)
            control.configuration = {**control.configuration, "worker_sources": {}}
        elif case == "parameters":
            db.get(TaskRow, task_id).parameters = {"command": "forbidden"}
    decision = authorize(engine, task_id)
    assert decision.outcome == "DENY"
    assert ("task_snapshot_mutation" if case == "parameters" else reason) in decision.reasons
    with Session(engine) as db:
        assert (
            db.get(AuthorizationSnapshotRow, decision.authorization_context_id).denied_dimensions
            == decision.reasons
        )


@pytest.mark.postgres
def test_action_mutation_denied_bound_to_original_digest(authority_environment):
    engine, _ = authority_environment
    task_id = claim_fixture(authority_environment)
    first = authorize(engine, task_id)
    with Session(engine) as db, db.begin():
        action = contract_from(db.get(ActionRow, first.action_id), ActionRequest)
        action.parameters = {"limit": 99}
        denied = AuthorizationService(db).evaluate(
            action, db.get(TaskRow, task_id), 1, response_principal(), INSTANT
        )
        assert denied.outcome == "DENY" and "action_digest_mismatch" in denied.reasons
        assert denied.action_digest == first.action_digest


@pytest.mark.postgres
@pytest.mark.parametrize(
    "case", ["unknown", "inactive", "cap_version", "expired_control", "lease", "cross_environment"]
)
def test_unresolvable_or_stale_authority_rejected_before_intent(authority_environment, case):
    engine, _ = authority_environment
    task_id = claim_fixture(authority_environment)
    principal = response_principal()
    with Session(engine) as db, db.begin():
        if case == "inactive":
            db.get(CapabilityConfigRow, ("collect_resource_context", "1.0.0")).active = False
        elif case == "expired_control":
            db.get(ResponseControlRow, ENV).valid_until = INSTANT - timedelta(seconds=1)
        elif case == "lease":
            db.get(WorkerLeaseRow, "lease-" + task_id).expires_at = INSTANT + timedelta(seconds=1)
    if case in {"unknown", "cap_version"}:
        with Session(engine) as db, pytest.raises(ReferenceError):
            CapabilityRegistry(db).resolve(
                "arbitrary_shell" if case == "unknown" else "collect_resource_context", "missing"
            )
    else:
        if case == "cross_environment":
            principal = principal.model_copy(update={"environment_ids": frozenset({"outside"})})
        with pytest.raises((AccessDenied, ConflictError, LeaseLostError)):
            authorize(
                engine,
                task_id,
                principal=principal,
                now=INSTANT + timedelta(seconds=2) if case == "lease" else INSTANT,
            )
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0


@pytest.mark.postgres
@pytest.mark.parametrize("risk", ["R3", "R4", "R5"])
def test_high_risk_policy_always_denies(authority_environment, risk):
    engine, _ = authority_environment
    first = authorize(engine, claim_fixture(authority_environment))
    with Session(engine) as db:
        context = contract_from(
            db.get(AuthorizationContextRow, first.authorization_context_id), AuthorizationContext
        )
        context.requested_risk = Risk(risk)
        facts = db.get(AuthorizationSnapshotRow, first.authorization_context_id).inputs
        denied = RiskPolicyGate().decide(
            context,
            facts,
            ResponsePolicy(),
            decision_id="negative-risk",
            valid_until=INSTANT + timedelta(seconds=10),
        )
        assert denied.outcome == "DENY" and "high_risk_autonomous_action_denied" in denied.reasons
        assert db.scalar(select(func.count()).select_from(ActionAttemptRow)) == 0


@pytest.mark.postgres
def test_authorization_audit_failure_rolls_back_entire_intent(authority_environment, monkeypatch):
    engine, _ = authority_environment
    task_id = claim_fixture(authority_environment)
    import zhiyu.response.authorization as module

    def fail(*args, **kwargs):
        raise RuntimeError("injected authorization audit failure")

    monkeypatch.setattr(module, "emit", fail)
    with pytest.raises(RuntimeError, match="injected"):
        authorize(engine, task_id)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0
        assert db.scalar(select(func.count()).select_from(AuthorizationDecisionRow)) == 0


@pytest.mark.postgres
def test_capability_registration_health_replay_history_and_conflict(authority_environment):
    engine, _ = authority_environment
    principal = response_principal()
    with Session(engine) as db:
        CapabilityRegistry(db).install(ENV, principal)
    with Session(engine) as db:
        original = contract_from(
            db.get(CapabilityHealthRow, ("safe_http_probe", "1.0.0", ENV, "response")), CapabilityHealth
        )
    with Session(engine) as db:
        CapabilityRegistry(db).record_health(original, principal)
    offline = original.model_copy(update={"status": "OFFLINE", "checked_at": INSTANT + timedelta(seconds=1)})
    with Session(engine) as db:
        CapabilityRegistry(db).record_health(offline, principal)
    with Session(engine) as db:
        history = CapabilityRegistry(db).health_history(ENV, "safe_http_probe", "1.0.0", "response")
        assert history == {"last_success": INSTANT, "last_failure": offline.checked_at}
    for stale in [original, offline.model_copy(update={"status": "HEALTHY"})]:
        with Session(engine) as db, pytest.raises(ConflictError):
            CapabilityRegistry(db).record_health(stale, principal)


@pytest.mark.postgres
def test_runtime_authorization_snapshot_is_immutable(authority_environment):
    engine, _ = authority_environment
    decision = authorize(engine, claim_fixture(authority_environment))
    with Session(engine) as db, pytest.raises(IntegrityError), db.begin():
        db.get(AuthorizationSnapshotRow, decision.authorization_context_id).inputs = {"forged": True}
