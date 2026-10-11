# ruff: noqa: F811
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_response_authorization import authority_environment  # noqa: F401
from test_response_gateway import claim, execute
from test_response_planner import ENV, INSTANT, response_environment  # noqa: F401
from test_verification_runtime import AT, collect, verification_environment, verifier  # noqa: F401

from zhiyu.db.mapping import contract_from
from zhiyu.db.models import (
    ActionRow,
    AuthorizationDecisionRow,
    IncidentRow,
    PlanRow,
    SensorHealthRow,
    StateEntityRow,
)
from zhiyu.db.response_execution import ActionResultRow
from zhiyu.db.response_planning import TaskRuntimeRow
from zhiyu.db.verification_replan import ReplanDecisionRow, ResponseCycleRow
from zhiyu.domain.contracts import ActionRequest
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.replan import DeterministicReplanner, ReplanBudget, activate
from zhiyu.verification.runtime import default_spec


@pytest.fixture
def closed_loop_environment(request, monkeypatch):
    import test_response_authorization as authority
    import test_verification_runtime as verification

    original_create = authority.create_plan
    original_execute = verification.execute
    budget = getattr(request, "param", ReplanBudget())

    def bounded(fixture, **kwargs):
        kwargs["policy"] = replace(kwargs["policy"], max_replans=2)
        return original_create(fixture, **kwargs)

    def activate_first(engine, lease):
        with Session(engine) as db:
            plan_id = db.get(TaskRuntimeRow, lease["task_id"]).plan_id
        principal = verifier().model_copy(
            update={"permissions": verifier().permissions | {"incidents:write"}}
        )
        activate(engine, ENV, plan_id, principal, budget, now=INSTANT)
        return original_execute(engine, lease)

    monkeypatch.setattr(authority, "create_plan", bounded)
    monkeypatch.setattr(verification, "execute", activate_first)
    fixture = request.getfixturevalue("verification_environment")
    engine = fixture[0]
    for _ in range(3):
        receipt, _ = execute(engine, claim(engine))
        assert receipt["execution_outcome"] == "EXECUTION_SUCCESS"
    with Session(engine) as db:
        assert db.scalar(select(IncidentRow)).status == "EXECUTING"
    return fixture


def decide(environment, outcome="PASS"):
    engine, _, _, spec, _ = environment
    if outcome == "FAIL":
        spec.checks[0].assertions[0].expected = 999
    if outcome == "INCONCLUSIVE":
        with Session(engine) as db, db.begin():
            db.scalar(select(SensorHealthRow)).status = "OFFLINE"
    collect(environment)
    result = VerificationEngine(engine).decide(ENV, spec.verification_spec_id, verifier(), now=AT)
    assert result.status == outcome
    return result


pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("outcome", ["PASS", "FAIL", "INCONCLUSIVE"])
def test_state_and_bounded_replan(closed_loop_environment, outcome):
    engine = closed_loop_environment[0]
    result = decide(closed_loop_environment, outcome)
    response = DeterministicReplanner(engine).handle(ENV, result.verification_id, verifier(), now=AT)
    assert response["status"] == ("NO_REPLAN" if outcome == "PASS" else "CREATED")
    assert response == DeterministicReplanner(engine).handle(ENV, result.verification_id, verifier(), now=AT)
    with Session(engine) as db:
        assert db.scalar(select(IncidentRow)).status == ("VERIFYING" if outcome == "PASS" else "PLANNED")
        facts = list(db.scalars(select(StateEntityRow)))
        assert {f.claim_kind for f in facts} == {"OBSERVATION", "INFERENCE"}
        assert all(f.evidence_ids and f.observed_at and f.state_version >= 1 for f in facts)
        if response["new_plan_id"]:
            new = db.get(PlanRow, response["new_plan_id"])
            assert new.model_run_id is None and new.total_model_calls == 0
            assert new.tasks[0]["capability_id"] == (
                "query_incident_evidence" if outcome == "FAIL" else "collect_resource_context"
            )
            assert db.get(ResponseCycleRow, new.plan_id).parent_plan_id == response["parent_plan_id"]


@pytest.mark.parametrize(
    "closed_loop_environment,expected",
    [
        (ReplanBudget(max_replans=0), "REPLAN_EXHAUSTED"),
        (ReplanBudget(max_total_actions=4), "REPLAN_EXHAUSTED"),
        (ReplanBudget(risk_ceiling="R0"), "REQUIRE_APPROVAL"),
    ],
    indirect=["closed_loop_environment"],
)
def test_budget_and_risk_ceiling(closed_loop_environment, expected):
    result = decide(closed_loop_environment, "FAIL")
    response = DeterministicReplanner(closed_loop_environment[0]).handle(
        ENV, result.verification_id, verifier(), now=AT
    )
    assert response["status"] == expected and response["new_plan_id"] is None


@pytest.mark.parametrize("new_fact", [False, True])
def test_replan_new_authorization_and_no_new_evidence_stop(closed_loop_environment, new_fact):
    engine, service, _, _, _ = closed_loop_environment
    result = decide(closed_loop_environment, "FAIL")
    replan = DeterministicReplanner(engine).handle(ENV, result.verification_id, verifier(), now=AT)
    lease = claim(engine, now=AT)
    receipt, decision = execute(engine, lease, now=AT)
    assert receipt["execution_outcome"] == "EXECUTION_SUCCESS"
    with Session(engine) as db:
        action = contract_from(
            db.scalar(select(ActionRow).where(ActionRow.task_id == lease["task_id"])), ActionRequest
        )
        assert decision.action_id == action.action_id
        assert len(list(db.scalars(select(AuthorizationDecisionRow)))) >= 10
        result_row = db.scalar(select(ActionResultRow).order_by(ActionResultRow.completed_at.desc()))
        result_id = result_row.attempt_id
        sensors = list(db.scalars(select(SensorHealthRow.sensor_id)))
    spec = default_spec(action, sensors)
    spec.checks[0].assertions[0].expected = 999
    if new_fact:
        from zhiyu.db.models import ResourceRow

        with Session(engine) as db, db.begin():
            db.get(ResourceRow, (action.target.resource_id, ENV)).binding_version += 1
    next_environment = (engine, service, result_id, spec, {})
    collect(next_environment, now=AT + timedelta(seconds=1))
    failed = VerificationEngine(engine).decide(
        ENV, spec.verification_spec_id, verifier(), now=AT + timedelta(seconds=1)
    )
    assert failed.status == "FAIL"
    stopped = DeterministicReplanner(engine).handle(
        ENV, failed.verification_id, verifier(), now=AT + timedelta(seconds=1)
    )
    assert stopped["status"] == "REPLAN_EXHAUSTED"
    assert ("repeated plan/action" if new_fact else "no new semantic evidence") in stopped["reason"]
    assert stopped["parent_plan_id"] == replan["new_plan_id"]


def test_replan_crash_rollback_and_two_workers(closed_loop_environment, monkeypatch):
    engine = closed_loop_environment[0]
    result = decide(closed_loop_environment, "FAIL")
    service = DeterministicReplanner(engine)
    original = service.create_plan

    def crash(*args):
        original(*args)
        raise RuntimeError("simulated crash before transaction commit")

    monkeypatch.setattr(service, "create_plan", crash)
    with pytest.raises(RuntimeError):
        service.handle(ENV, result.verification_id, verifier(), now=AT)
    with Session(engine) as db:
        assert db.get(ReplanDecisionRow, result.verification_id) is None
        assert db.scalar(select(IncidentRow)).status == "VERIFYING"

    def worker(_):
        return DeterministicReplanner(engine).handle(ENV, result.verification_id, verifier(), now=AT)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(worker, range(2)))
    assert responses[0] == responses[1] and responses[0]["status"] == "CREATED"


@pytest.mark.parametrize("closed_loop_environment", [ReplanBudget(max_elapsed_time=10)], indirect=True)
def test_elapsed_replan_budget(closed_loop_environment):
    result = decide(closed_loop_environment, "FAIL")
    stopped = DeterministicReplanner(closed_loop_environment[0]).handle(
        ENV, result.verification_id, verifier(), now=AT + timedelta(seconds=11)
    )
    assert stopped["status"] == "REPLAN_EXHAUSTED" and "time budget" in stopped["reason"]
