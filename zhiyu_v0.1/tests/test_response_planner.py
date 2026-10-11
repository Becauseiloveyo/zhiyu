"""Gate A tests; task state fixtures do not dispatch executors or claim security success."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta

import pytest
from conftest import ROOT
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_adapters import NOW
from test_event_intelligence import process
from test_incident_engine import advance, chain, incident_id, promote

from zhiyu.core.errors import ConflictError, ReferenceError, StaleVersionError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import values_for
from zhiyu.db.models import (
    ActionRow,
    AuditEntryRow,
    CapabilityRow,
    EnvironmentRow,
    IncidentRow,
    PlanRow,
    ScopeRow,
    TaskRow,
)
from zhiyu.db.response_planning import ResponsePlanRow, TaskEdgeRow, TaskRuntimeRow
from zhiyu.response.catalog import INPUTS, manifest
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy, TaskGraphValidator
from zhiyu.response.task_graph import TRANSITIONS, next_status, refresh_dependencies

INSTANT = NOW + timedelta(seconds=110)
ENV = "lab-zhiyu-01"
SCOPE = "scope-lab-web"


def response_principal():
    return ServicePrincipal(
        principal_id="response-operator",
        environment_ids={ENV},
        permissions={
            "response:plan",
            "response:read",
            "response:execute",
            "response:admin",
            *["capability:" + c for c in INPUTS],
        },
    )


@pytest.fixture
def response_environment(bootstrapped):
    chain(bootstrapped)
    process(bootstrapped)
    promote(bootstrapped)
    ident = incident_id(bootstrapped)
    advance(bootstrapped, ident, "TRIAGED", 1)
    with Session(bootstrapped) as db, db.begin():
        env = db.get(EnvironmentRow, ENV)
        env.capability_allowlist = list(INPUTS)
        scope = db.get(ScopeRow, (SCOPE, ENV))
        scope.allowed_capabilities = list(INPUTS)
        scope.capability_source_ids = {c: ["validation-a"] for c in INPUTS}
        scope.valid_from, scope.valid_until = NOW - timedelta(days=1), NOW + timedelta(days=1)
        for capability in INPUTS:
            db.add(CapabilityRow(**values_for(manifest(capability), CapabilityRow)))
    return bootstrapped, ident


def create_plan(fixture, *, expected=2, policy=PlannerPolicy()):
    engine, ident = fixture
    with Session(engine) as db:
        return DeterministicResponsePlanner(db, policy).create(
            ENV, ident, expected_version=expected, scope_id=SCOPE, principal=response_principal(), now=INSTANT
        )


@pytest.mark.postgres
def test_deterministic_plan_idempotency_restart_and_relations(response_environment):
    engine, ident = response_environment
    plan = create_plan(response_environment)
    engine.dispose()
    assert create_plan(response_environment) == plan
    assert plan.model_run_id is None and plan.total_model_calls == 0
    assert len(plan.tasks) == 3 and sum(len(t.dependencies) for t in plan.tasks) == 2
    with Session(engine) as db:
        for row, count in [
            (PlanRow, 1),
            (ResponsePlanRow, 1),
            (TaskRow, 3),
            (TaskRuntimeRow, 3),
            (TaskEdgeRow, 2),
            (ActionRow, 0),
        ]:
            assert db.scalar(select(func.count()).select_from(row)) == count
        metadata = db.get(ResponsePlanRow, plan.plan_id)
        assert metadata.inputs["incident"]["state_version"] == 2
        assert metadata.generation_ms > 0 and metadata.graph_ms > 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEntryRow)
                .where(AuditEntryRow.operation == "PlanCreated")
            )
            == 1
        )


@pytest.mark.postgres
def test_plan_versions_stale_incident_and_policy_identity(response_environment):
    engine, ident = response_environment
    first = create_plan(response_environment)
    second = create_plan(
        response_environment, policy=replace(PlannerPolicy(), policy_version="response-plan/2")
    )
    assert first.plan_id != second.plan_id
    with pytest.raises(ConflictError):
        create_plan(response_environment, policy=replace(PlannerPolicy(), include_http_probe=True))
    with Session(engine) as db, db.begin():
        row = db.get(IncidentRow, ident)
        row.state_version += 1
    with pytest.raises(StaleVersionError):
        create_plan(response_environment)
    assert create_plan(response_environment, expected=3).plan_id not in {first.plan_id, second.plan_id}


@pytest.mark.postgres
def test_planner_invalid_incident_scope_and_input_boundaries(response_environment):
    engine, ident = response_environment
    with Session(engine) as db, db.begin():
        db.get(IncidentRow, ident).status = "NEW"
    with pytest.raises(ConflictError):
        create_plan(response_environment)
    with Session(engine) as db, db.begin():
        db.get(IncidentRow, ident).status = "TRIAGED"
        db.get(ScopeRow, (SCOPE, ENV)).valid_until = NOW
    with pytest.raises(ConflictError):
        create_plan(response_environment)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(PlanRow)) == 0


@pytest.mark.postgres
def test_task_graph_cycle_missing_dependency_cross_plan_and_capability(response_environment):
    engine, _ = response_environment
    plan = create_plan(response_environment)
    for mutation in ["cycle", "missing", "environment", "capability", "parameters", "target", "cross_plan"]:
        changed = plan.model_copy(deep=True)
        if mutation == "cycle":
            changed.tasks[0].dependencies = [changed.tasks[1].task_id]
        elif mutation == "missing":
            changed.tasks[0].dependencies = ["missing"]
        elif mutation == "environment":
            changed.tasks[0].environment_id = "outside"
        elif mutation == "capability":
            changed.tasks[0].capability_id = "arbitrary_shell"
        elif mutation == "parameters":
            changed.tasks[0].parameters = {"command": "not allowed"}
        elif mutation == "target":
            changed.tasks[0].target_resource_ids = ["not-in-scope"]
        else:
            changed.plan_id = "another-plan"
        with Session(engine) as db, pytest.raises((ConflictError, ReferenceError, ValidationError)):
            TaskGraphValidator().validate(db, changed, INSTANT)


@pytest.mark.postgres
def test_graph_fk_enforces_same_plan_and_missing_dependency(response_environment):
    engine, _ = response_environment
    first = create_plan(response_environment)
    second = create_plan(
        response_environment, policy=replace(PlannerPolicy(), policy_version="response-plan/2")
    )
    for dependency in [second.tasks[0].task_id, "missing"]:
        with Session(engine) as db, pytest.raises(IntegrityError), db.begin():
            db.add(
                TaskEdgeRow(
                    environment_id=ENV,
                    plan_id=first.plan_id,
                    task_id=first.tasks[0].task_id,
                    depends_on=dependency,
                )
            )


@pytest.mark.postgres
def test_planning_concurrency_and_rollback(response_environment, monkeypatch):
    engine, _ = response_environment
    import zhiyu.response.planner as module

    original = module.emit

    def fail(*args, **kwargs):
        raise RuntimeError("injected audit failure")

    monkeypatch.setattr(module, "emit", fail)
    with pytest.raises(RuntimeError, match="injected"):
        create_plan(response_environment)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(PlanRow)) == 0
        assert db.scalar(select(func.count()).select_from(TaskRow)) == 0
    monkeypatch.setattr(module, "emit", original)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create_plan(response_environment), range(2)))
    assert results[0] == results[1]


def test_task_state_machine_exact_ai5_and_illegal_transition():
    frozen = json.loads((ROOT / "baseline/ai5/state_machines.json").read_text())
    expected = {(t["from"], t["event"]): t["to"] for t in frozen["machines"]["Task"]["transitions"]}
    assert TRANSITIONS == expected
    for (state, event), target in expected.items():
        assert next_status(state, event) == target
    for state, event in [("BLOCKED", "claim"), ("SUCCEEDED", "retry"), ("QUEUED", "output_valid")]:
        with pytest.raises(ConflictError):
            next_status(state, event)


@pytest.mark.postgres
@pytest.mark.parametrize("success", [True, False])
def test_dependency_readiness_and_terminal_failure_propagation(response_environment, success):
    engine, _ = response_environment
    plan = create_plan(response_environment)
    with Session(engine) as db, db.begin():
        assert refresh_dependencies(db, ENV, INSTANT, "test-state-fixture") == 0
        root = db.get(TaskRow, plan.tasks[0].task_id)
        root.status = "SUCCEEDED" if success else "FAILED"
        root.attempt_count = root.max_attempts
        db.flush()
        assert refresh_dependencies(db, ENV, INSTANT, "test-state-fixture") == 2
        assert {db.get(TaskRow, t.task_id).status for t in plan.tasks[1:]} == (
            {"QUEUED"} if success else {"CANCELLED"}
        )
