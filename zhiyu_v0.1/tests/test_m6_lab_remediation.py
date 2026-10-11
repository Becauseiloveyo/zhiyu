"""Real HTTP target and PostgreSQL; synthetic incident/sensor fixtures are explicitly labelled.

These regressions exercise software prerequisites. They do not replace final Real Sensor acceptance.
"""

import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.config import settings
from zhiyu.core.errors import LeaseLostError
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import (
    ActionAttemptRow,
    ActionRow,
    CapabilityHealthRow,
    EnvironmentRow,
    IncidentRow,
    ResourceRow,
    ScopeRow,
    SensorHealthRow,
    TaskRow,
    WorkerLeaseRow,
)
from zhiyu.db.response_authority import ActionControlRow, ResponseControlRow
from zhiyu.db.response_execution import ActionResultRow
from zhiyu.domain.contracts import ActionRequest, CapabilityHealth, SensorHealth
from zhiyu.repositories.audit import AuditRepository
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.executors import ExecutorOutput
from zhiyu.response.gateway import ActionGateway
from zhiyu.response.lab_client import LabClient
from zhiyu.response.lab_protocol import CAPABILITY, LabBinding, LabInput
from zhiyu.response.lab_target import LabState, make_server
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy
from zhiyu.response.registry import CapabilityRegistry
from zhiyu.response.scheduler import TaskScheduler
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.lab_reviews import schedule_reviews
from zhiyu.verification.policy import VerificationPolicy
from zhiyu.verification.runtime import VerificationService, containment_spec

ENV, SCOPE = "lab-zhiyu-01", "scope-lab-web"


@pytest.fixture
def lab_environment(bootstrapped, monkeypatch):
    import test_incident_engine as incident_fixture
    from test_event_intelligence import process
    from test_response_planner import response_principal

    engine = bootstrapped
    # Preserve the golden chain's fixed-window alignment while keeping evidence fresh.
    # Sliding wall time across a five-minute boundary would split its three signals.
    base = datetime.fromtimestamp(
        int((datetime.now(UTC) - timedelta(seconds=110)).timestamp()) // 300 * 300, UTC
    )
    monkeypatch.setattr(incident_fixture, "NOW", base)
    incident_fixture.chain(engine)
    process(engine, now=base + timedelta(seconds=90))
    incident_fixture.promote(engine)
    incident = incident_fixture.incident_id(engine)
    incident_fixture.advance(engine, incident, "TRIAGED", 1)
    principal = response_principal()
    principal = principal.model_copy(
        update={
            "permissions": principal.permissions
            | {
                "capability:" + CAPABILITY,
                "response:reconcile",
                "verification:write",
                "verification:execute",
                "verification:replan",
            }
        }
    )
    verifier = principal.model_copy(update={"principal_id": "independent-lab-verifier"})
    state = LabState(ENV, "target-a")
    token = "synthetic-lab-test-control-token-no-production-secret"
    server = make_server("127.0.0.1", 0, state, token)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(
        settings,
        "lab_targets",
        {
            ENV + "/target-a": LabBinding(
                environment_id=ENV,
                resource_id="target-a",
                address="127.0.0.1",
                port=server.server_port,
                token=token,
            )
        },
    )
    try:
        with Session(engine) as db:
            CapabilityRegistry(db).install(ENV, principal)
        with Session(engine) as db:
            CapabilityRegistry(db).install(ENV, principal, lab=True)
        from zhiyu.response.catalog import INPUTS

        now = datetime.now(UTC)
        with Session(engine) as db, db.begin():
            env = db.get(EnvironmentRow, ENV)
            env.capability_allowlist = [*INPUTS, CAPABILITY]
            env.max_auto_risk, env.autonomy_mode, env.active_validation = (
                "R2",
                "CONTROLLED_AUTONOMY",
                "ISOLATED_ONLY",
            )
            scope = db.get(ScopeRow, (SCOPE, ENV))
            scope.allowed_capabilities = [*INPUTS, CAPABILITY]
            scope.capability_source_ids = {c: ["validation-a"] for c in scope.allowed_capabilities}
            scope.valid_from, scope.valid_until = now - timedelta(hours=1), now + timedelta(hours=1)
            scope.network_constraints = [
                {
                    "source_resource_ids": ["validation-a"],
                    "target_resource_ids": ["target-a"],
                    "destination_ports": [server.server_port],
                    "protocols": ["TCP"],
                }
            ]
            db.get(ResourceRow, ("target-a", ENV)).locator = {
                "address": "127.0.0.1",
                "port": server.server_port,
                "protocol": "TCP",
            }
            db.get(ResourceRow, ("validation-a", ENV)).locator = {
                "address": "127.0.0.1",
                "port": 1,
                "protocol": "TCP",
            }
            db.add(
                ResponseControlRow(
                    environment_id=ENV,
                    policy_version=env.policy_version,
                    enabled=True,
                    configuration=ResponsePolicy(
                        worker_sources={
                            principal.principal_id: "validation-a",
                            verifier.principal_id: "validation-a",
                        }
                    ).model_dump(mode="json"),
                    valid_from=now - timedelta(minutes=1),
                    valid_until=now + timedelta(hours=1),
                    next_probe_at=now,
                )
            )
            for sensor_id in env.required_sensor_ids:
                sensor = SensorHealth(
                    sensor_id=sensor_id,
                    environment_id=ENV,
                    status="HEALTHY",
                    last_heartbeat_at=now,
                    last_event_at=now,
                    lag_seconds=0,
                    lost_event_count=0,
                    coverage_scope_ids=[SCOPE],
                    coverage_validated=True,
                    config_version="SYNTHETIC-M6-REGRESSION-NOT-REAL-SENSOR",
                )
                db.add(SensorHealthRow(**values_for(sensor, SensorHealthRow)))
            for capability in [*INPUTS, CAPABILITY]:
                health = CapabilityHealth(
                    capability_id=capability,
                    capability_version="1.0.0",
                    environment_id=ENV,
                    worker_pool="response",
                    status="HEALTHY",
                    checked_at=now,
                    latency_ms=0,
                    queue_depth=0,
                    running_count=0,
                    detail="SYNTHETIC regression",
                )
                db.add(CapabilityHealthRow(**values_for(health, CapabilityHealthRow)))
        yield engine, principal, verifier, state, server, incident
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def make_plan(lab, *, ttl=30, prior=None, snapshot=None, revision="1"):
    engine, principal, _, state, _, incident = lab
    before = snapshot or state.snapshot()
    parameters = LabInput(
        epoch=before["epoch"],
        expected_generation=before["generation"],
        before_digest=before["digest"],
        ttl_seconds=ttl,
        operation="compensate" if prior else "contain",
        prior_action_id=prior,
    ).model_dump()
    with Session(engine) as db:
        return DeterministicResponsePlanner(
            db,
            PlannerPolicy(
                policy_version="m6-lab/" + canonical_hash([parameters, revision]),
                lab_target="target-a",
                lab_parameters=parameters,
            ),
        ).create(ENV, incident, expected_version=2, scope_id=SCOPE, principal=principal)


def dispatch(lab, gateway=None):
    engine, principal, *_ = lab
    with Session(engine) as db:
        ready = db.get(ResponseControlRow, ENV).next_probe_at
    delay = (ready - datetime.now(UTC)).total_seconds()
    if delay > 0:
        time.sleep(delay + 0.01)
    with Session(engine) as db:
        lease = TaskScheduler(db).claim(ENV, principal)
    assert lease is not None
    with Session(engine) as db:
        decision = AuthorizationService(db).authorize_task(
            ENV, lease["task_id"], generation=lease["generation"], principal=principal
        )
    assert decision.outcome == "ALLOW", decision.reasons
    result = (gateway or ActionGateway(engine)).dispatch(
        ENV, lease["task_id"], lease["generation"], decision.authorization_id, principal
    )
    return result, lease, decision


def action_for(engine, result):
    with Session(engine) as db:
        return contract_from(db.get(ActionRow, result["action_id"]), ActionRequest)


def fresh_sensor_window(engine):
    time.sleep(1.05)
    with Session(engine) as db, db.begin():
        for sensor in db.scalars(select(SensorHealthRow)):
            sensor.last_event_at = sensor.last_heartbeat_at = datetime.now(UTC)


def run_verification(lab, result, spec=None, *, policy=None, refresh=True):
    engine, _, verifier, *_ = lab
    service = VerificationService(engine)
    action = action_for(engine, result)
    with Session(engine) as db:
        sensors = db.get(EnvironmentRow, ENV).required_sensor_ids
    spec = spec or containment_spec(action, sensors)
    service.create(
        ENV, result["attempt_id"], spec, verifier, policy or VerificationPolicy(minimum_window_seconds=1)
    )
    if refresh:
        fresh_sensor_window(engine)
    completed = []
    for _ in range(100):
        claim = service.claim(ENV, verifier, spec_id=spec.verification_spec_id)
        if claim:
            completed.append(service.run_claim(ENV, claim, verifier))
        elif len(completed) == 3:
            break
        else:
            time.sleep(0.025)
    return VerificationEngine(engine).decide(ENV, spec.verification_spec_id, verifier)


@pytest.mark.postgres
def test_a05_receipt_loss_after_real_mutation_reconciles_without_replay(lab_environment, monkeypatch):
    lab = lab_environment
    engine, principal, verifier, state, *_ = lab
    make_plan(lab)
    gateway = ActionGateway(engine)
    original = gateway.complete

    def crash(*args, **kwargs):
        raise RuntimeError("receipt lost before commit")

    monkeypatch.setattr(gateway, "complete", crash)
    with pytest.raises(RuntimeError, match="receipt lost"):
        dispatch(lab, gateway)
    assert state.snapshot()["restricted"] and state.mutations == 1
    with Session(engine) as db, db.begin():
        attempt = db.scalars(select(ActionAttemptRow)).one()
        attempt_id = attempt.attempt_id
        assert db.scalar(select(func.count()).select_from(ActionResultRow)) == 0
        lease = db.scalars(select(WorkerLeaseRow)).one()
        lease.expires_at = datetime.now(UTC)
    with Session(engine) as db:
        assert TaskScheduler(db).claim(ENV, principal) is None
    with Session(engine) as db:
        assert db.get(ActionAttemptRow, attempt_id).status == "EXECUTION_UNKNOWN"
        assert db.scalars(select(ActionControlRow)).one().status == "EXECUTION_UNKNOWN"
    result = gateway.reconcile(ENV, attempt_id, verifier)
    assert result["execution_outcome"] == "EXECUTION_SUCCESS"
    assert result["output"]["reconciliation"] == "CONFIRMED_APPLIED"
    assert result["output"]["mutation_replayed"] is False
    assert state.mutations == 1
    assert gateway.reconcile(ENV, attempt_id, verifier)["disposition"] == "DUPLICATE"
    assert LabClient(action_for(engine, result)).request("POST")["duplicate"] is True
    assert state.mutations == 1
    with pytest.raises(LeaseLostError):
        original(
            ENV,
            attempt_id,
            1,
            principal,
            ExecutorOutput("EXECUTION_SUCCESS", {}),
            executor_name=CAPABILITY,
            executor_version="stale",
            executor_ms=0,
        )
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ActionAttemptRow)) == 1
        assert db.get(ActionAttemptRow, attempt_id).status == "EXECUTION_UNKNOWN"
        assert db.get(ActionAttemptRow, attempt_id).reconciliation_state == "CONFIRMED_APPLIED"
        assert AuditRepository(db).verify_chain(ENV)


@pytest.mark.postgres
def test_a06_compensation_refuses_foreign_owner_generation_and_stale_digest(lab_environment):
    lab = lab_environment
    engine, principal, _, state, *_ = lab
    make_plan(lab)
    first, lease, decision = dispatch(lab)
    original = action_for(engine, first)
    owned = state.snapshot()
    assert (
        ActionGateway(engine).dispatch(ENV, lease["task_id"], 1, decision.authorization_id, principal)[
            "disposition"
        ]
        == "DUPLICATE"
    )
    make_plan(lab, prior=original.action_id)
    release, *_ = dispatch(lab)
    assert release["execution_outcome"] == "EXECUTION_SUCCESS" and not state.snapshot()["restricted"]
    make_plan(lab)
    second, *_ = dispatch(lab)
    assert state.snapshot()["owner"] != owned["owner"]
    mutations = state.mutations
    make_plan(lab, prior=original.action_id, snapshot=owned, revision="stale-worker")
    stale, *_ = dispatch(lab)
    assert stale["execution_outcome"] == "EXECUTION_UNKNOWN"
    assert state.mutations == mutations and state.snapshot()["owner"] == "zhiyu-lab:" + second["action_id"]
    assert LabClient(original).request("POST")["duplicate"] is True
    assert state.mutations == mutations


@pytest.mark.postgres
@pytest.mark.parametrize(
    "case,expected",
    [
        ("contained", "PASS"),
        ("attack_reachable", "FAIL"),
        ("business_unavailable", "FAIL"),
        ("sensor_offline", "INCONCLUSIVE"),
    ],
)
def test_a07_real_three_dimensional_containment(lab_environment, monkeypatch, case, expected):
    lab = lab_environment
    engine, _, _, state, server, _ = lab
    make_plan(lab)
    result, *_ = dispatch(lab)
    if case == "attack_reachable":
        make_plan(lab, prior=result["action_id"])
        dispatch(lab)
    if case == "business_unavailable":
        original = server.RequestHandlerClass.do_HEAD

        def unavailable(self):
            if self.path == "/health":
                self.reply(503, {"error": "controlled-business-outage"})
            else:
                original(self)

        monkeypatch.setattr(server.RequestHandlerClass, "do_HEAD", unavailable)
    if case == "sensor_offline":
        with Session(engine) as db, db.begin():
            for sensor in db.scalars(select(SensorHealthRow)):
                sensor.status = "OFFLINE"
    verdict = run_verification(lab, result)
    assert verdict.objective_type == "CONTAINMENT" and verdict.status == expected
    with Session(engine) as db:
        assert db.get(IncidentRow, lab[-1]).status != "CLOSED"
        assert AuditRepository(db).verify_chain(ENV)


@pytest.mark.postgres
def test_a09_native_ttl_automatically_queues_fresh_independent_review(lab_environment):
    from zhiyu.db.verification_runtime import VerificationObservationRow, VerificationRuntimeRow

    lab = lab_environment
    engine, _, verifier, state, *_ = lab
    make_plan(lab, ttl=5)
    result, *_ = dispatch(lab)
    ids = schedule_reviews(engine, ENV, verifier)
    assert len(ids) == 2 and schedule_reviews(engine, ENV, verifier) == []
    with Session(engine) as db:
        reviews = list(db.scalars(select(VerificationRuntimeRow)))
        active = next(r for r in reviews if r.policy["start_after_seconds"] == 0)
        expiry = next(r for r in reviews if r.policy["start_after_seconds"] > 0)
        from zhiyu.db.models import VerificationSpecRow
        from zhiyu.domain.contracts import VerificationSpec

        active_spec = contract_from(db.get(VerificationSpecRow, active.spec_id), VerificationSpec)
        expiry_spec = contract_from(db.get(VerificationSpecRow, expiry.spec_id), VerificationSpec)
    first = run_verification(
        lab, result, active_spec, policy=VerificationPolicy.model_validate(active.policy)
    )
    assert first.status == "PASS" and state.snapshot()["restricted"]
    assert VerificationService(engine).claim(ENV, verifier, spec_id=expiry.spec_id) is None
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and (
        state.snapshot()["restricted"]
        or datetime.now(UTC) <= datetime.fromisoformat(expiry.binding["not_before"])
    ):
        time.sleep(0.05)
    assert state.snapshot()["restricted"] is False and state.expirations == 1
    assert first.valid_until <= datetime.now(UTC)
    second = run_verification(
        lab, result, expiry_spec, policy=VerificationPolicy.model_validate(expiry.policy)
    )
    assert second.status == "FAIL" and second.security_status == "FAIL"
    assert set(first.evidence_ids).isdisjoint(second.evidence_ids)
    with Session(engine) as db:
        assert all(
            o.started_at >= datetime.fromisoformat(expiry.binding["not_before"])
            for o in db.scalars(
                select(VerificationObservationRow).where(VerificationObservationRow.spec_id == expiry.spec_id)
            )
        )
        assert db.get(IncidentRow, lab[-1]).status != "CLOSED"


def test_lab_parameters_and_containment_spec_cannot_weaken_frozen_acceptance():
    with pytest.raises(ValidationError):
        LabInput(epoch="a" * 32, expected_generation=0, before_digest="a" * 64, ttl_seconds=61)
    with pytest.raises(ValidationError):
        LabInput(
            epoch="a" * 32, expected_generation=0, before_digest="a" * 64, ttl_seconds=10, command="anything"
        )


@pytest.mark.postgres
def test_a11_background_saturation_preserves_critical_and_verification_capacity(lab_environment):
    from zhiyu.response.capacity import snapshot

    lab = lab_environment
    engine, principal, verifier, _, _, incident = lab
    background = principal.model_copy(update={"principal_id": "background-worker"})
    make_plan(lab)
    for number in range(8):
        with Session(engine) as db:
            DeterministicResponsePlanner(db, PlannerPolicy(policy_version=f"m6-background/{number}")).create(
                ENV, incident, expected_version=2, scope_id=SCOPE, principal=principal
            )
    with Session(engine) as db, db.begin():
        control = db.get(ResponseControlRow, ENV)
        policy = ResponsePolicy.model_validate(control.configuration).model_dump()
        policy.update(
            reserved_capacity_enabled=True,
            worker_classes={
                background.principal_id: "BACKGROUND",
                principal.principal_id: "SECURITY_CRITICAL",
                verifier.principal_id: "RECOVERY",
            },
            class_capacity={"BACKGROUND": 1, "SECURITY_CRITICAL": 1, "RECOVERY": 1},
        )
        policy["worker_sources"][background.principal_id] = "validation-a"
        control.configuration = ResponsePolicy.model_validate(policy).model_dump(mode="json")
    with Session(engine) as db:
        held = TaskScheduler(db).claim(ENV, background)
    assert held is not None
    with Session(engine) as db:
        assert TaskScheduler(db).claim(ENV, background) is None
    started = time.monotonic()
    result, *_ = dispatch(lab)
    assert result["execution_outcome"] == "EXECUTION_SUCCESS"
    verdict = run_verification(lab, result)
    assert verdict.status == "PASS"
    recovery_latency = time.monotonic() - started
    assert recovery_latency > 0
    with Session(engine) as db:
        stats = snapshot(db, ENV)
        assert stats["classes"]["BACKGROUND"]["running"] == 1
        assert stats["classes"]["BACKGROUND"]["queue_depth"] == 23
        assert stats["classes"]["BACKGROUND"]["deferred"] > 0
        assert stats["classes"]["SECURITY_CRITICAL"]["completed"] == 1
        assert stats["classes"]["RECOVERY"]["completed"] == 3
        assert stats["dropped"] == 0
        assert db.scalar(select(func.count()).select_from(TaskRow)) == 25
        assert AuditRepository(db).verify_chain(ENV)
