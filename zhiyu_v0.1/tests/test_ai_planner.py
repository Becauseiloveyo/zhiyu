"""Gate D: AI outputs are scripted fault fixtures; authorization still uses v0.3."""

# ruff: noqa: F811
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_ai_analysis import grounded
from test_ai_context import AT, ai_principal, build
from test_ai_gateway import http_provider  # noqa: F401
from test_response_authorization import authority_environment, authorize, claim_fixture  # noqa: F401
from test_response_planner import ENV, response_environment  # noqa: F401

from zhiyu.ai.analysis import AISituationAnalyzer
from zhiyu.ai.gateway import ModelGateway
from zhiyu.ai.planner import AIPlanner
from zhiyu.ai.policy import AIBudget, AIPolicy
from zhiyu.db.ai_gateway import AIIncidentBudgetRow
from zhiyu.db.ai_planning import AIProposalRow
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import (
    ActionRow,
    CapabilityHealthRow,
    CapabilityRow,
    EnvironmentRow,
    PlanRow,
    ScopeRow,
    TaskRow,
)
from zhiyu.domain.contracts import AIPlan


@pytest.fixture
def ai_environment(request, monkeypatch):
    import test_response_authorization as authority

    # Reuse the measured authorization fixture setup, without its deterministic plan.
    monkeypatch.setattr(
        authority, "create_plan", lambda fixture, **kwargs: SimpleNamespace(incident_id=fixture[1])
    )
    return request.getfixturevalue("authority_environment")


def proposal_output(ctx, capability="collect_resource_context"):
    return {
        "objective": "Collect bounded context",
        "reasoning_summary": "Evidence needs independent validation",
        "evidence_refs": [ctx["body"]["trusted_facts"][0]["evidence_id"]],
        "proposed_tasks": [
            {
                "task_key": "collect",
                "dependencies": [],
                "capability_id": capability,
                "target_resource_id": ctx["manifest"]["resource_ids"][0],
                "parameters": {},
                "reason": "Collect supporting observations",
                "expected_outcome": "Execution receipt, not proof of remediation",
                "verification_required": "INDEPENDENT_THREE_DIMENSION",
            }
        ],
        "risk_notes": ["Independent verification required"],
        "success_is_unverified": True,
    }


def setup_ai(fixture, provider, *, mode="ASSISTED", budget=AIBudget()):
    state, config = provider
    ctx = build(fixture)
    gateway = ModelGateway(
        fixture[0], AIPolicy(enabled=True, mode=mode, provider_id=config.provider, budget=budget), config
    )
    state["output"] = grounded(ctx)
    analysis = AISituationAnalyzer(fixture[0], gateway).analyze(
        ENV, ctx["context_id"], ai_principal(), now=AT
    )
    assert analysis["status"] == "REFERENCE_GROUNDED"
    state["output"] = proposal_output(ctx)
    return ctx, analysis, gateway, AIPlanner(fixture[0], gateway)


@pytest.mark.postgres
def test_valid_proposal_existing_authorization_replay_and_immutability(ai_environment, http_provider):
    engine, _ = ai_environment
    ctx, analysis, gateway, service = setup_ai(ai_environment, http_provider)
    result = service.propose(ENV, analysis["analysis_id"], ai_principal(), now=AT)
    assert result["status"] == "ACCEPTED" and result["validation"]["authorization"] == "NOT_GRANTED"
    engine.dispose()
    assert service.propose(ENV, analysis["analysis_id"], ai_principal(), now=AT) == result
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0
        plan = contract_from(db.get(PlanRow, result["plan_id"]), AIPlan)
        assert plan.model_run_id and plan.total_model_calls == 2 and len(plan.tasks) == 1
        assert plan.tasks[0].max_attempts == 1
    task = claim_fixture((engine, plan))
    decision = authorize(engine, task, now=AT)
    assert decision.outcome == "ALLOW"
    for table, key, identifier in [
        ("ai_plan_proposals", "proposal_id", result["proposal_id"]),
        ("plans", "plan_id", plan.plan_id),
    ]:
        with pytest.raises(DBAPIError), engine.begin() as c:
            c.execute(text(f"DELETE FROM {table} WHERE {key}=:id"), {"id": identifier})


@pytest.mark.postgres
@pytest.mark.parametrize(
    "fault",
    [
        "capability",
        "target",
        "command",
        "parameter",
        "cycle",
        "dependency",
        "duplicates",
        "count",
        "active_checks",
        "state_change",
        "risk",
        "scope",
        "health",
        "stale",
        "production",
        "autonomy",
    ],
)
def test_invalid_proposals_never_become_tasks(ai_environment, http_provider, fault):
    engine, _ = ai_environment
    state, _ = http_provider
    ctx, analysis, gateway, service = setup_ai(ai_environment, http_provider)
    output = state["output"]
    task = output["proposed_tasks"][0]
    if fault == "capability":
        task["capability_id"] = "disable_entire_network"
    elif fault == "target":
        task["target_resource_id"] = "another-tenant-target"
    elif fault == "command":
        task["parameters"]["command"] = "shell disable firewall"
    elif fault == "parameter":
        task["parameters"]["protocol"] = "https"
    elif fault == "cycle":
        task["dependencies"] = ["collect"]
    elif fault == "dependency":
        task["dependencies"] = ["invented"]
    elif fault in {"duplicates", "count", "active_checks"}:
        if fault == "active_checks":
            task["capability_id"] = "safe_http_probe"
        output["proposed_tasks"] = [
            dict(deepcopy(task), task_key="t" + str(i)) for i in range(5 if fault == "count" else 2)
        ]
    elif fault == "risk":
        task["capability_id"] = "query_event_history"
    elif fault == "autonomy":
        task["capability_id"] = "safe_http_probe"
    receipt = gateway.propose_plan(
        ENV, ctx["context_id"], ai_principal(), analysis=analysis["output"], now=AT
    )
    with Session(engine) as db, db.begin():
        if fault == "state_change":
            db.get(CapabilityRow, (task["capability_id"], "1.0.0")).operation_kind = "STATE_CHANGE"
        if fault == "risk":
            db.get(EnvironmentRow, ENV).max_auto_risk = "R0"
        if fault == "scope":
            db.get(ScopeRow, ("scope-lab-web", ENV)).allowed_capabilities = ["query_event_history"]
        if fault == "health":
            db.get(CapabilityHealthRow, (task["capability_id"], "1.0.0", ENV, "response")).status = "OFFLINE"
        if fault == "production":
            db.get(EnvironmentRow, ENV).deployment_stage = "PRODUCTION"
        if fault == "autonomy":
            db.get(EnvironmentRow, ENV).autonomy_mode = "OBSERVE_ONLY"
    result = service.record(
        ENV,
        analysis["analysis_id"],
        receipt["request_id"],
        ai_principal(),
        now=AT + timedelta(seconds=150) if fault == "stale" else AT,
    )
    assert result["status"] == "REJECTED" and result["plan_id"] is None
    required_reason = {
        "count": "aggregate_action_count",
        "duplicates": "repeated_action_fingerprint",
        "active_checks": "cumulative_active_checks",
        "risk": "risk_ceiling_require_approval_or_deny",
    }.get(fault)
    if required_reason:
        assert required_reason in result["validation"]["reasons"]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(PlanRow)) == 0
        assert db.scalar(select(func.count()).select_from(TaskRow)) == 0
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0


@pytest.mark.postgres
def test_shadow_budget_and_provider_failure_leave_deterministic_available(ai_environment, http_provider):
    engine, fake = ai_environment
    _, analysis, gateway, service = setup_ai(
        ai_environment, http_provider, mode="SHADOW", budget=AIBudget(max_calls=1)
    )
    result = service.propose(ENV, analysis["analysis_id"], ai_principal(), now=AT)
    assert result["status"] == "FALLBACK" and result["plan_id"] is None
    from test_response_planner import create_plan

    deterministic = create_plan((engine, fake.incident_id))
    assert deterministic.model_run_id is None
    with Session(engine) as db:
        assert db.scalar(select(AIIncidentBudgetRow.call_count)) == 1


@pytest.mark.postgres
def test_valid_shadow_creates_proposal_without_task(ai_environment, http_provider):
    _, analysis, _, service = setup_ai(ai_environment, http_provider, mode="SHADOW")
    result = service.propose(ENV, analysis["analysis_id"], ai_principal(), now=AT)
    assert result["status"] == "SHADOW" and result["plan_id"] is None
    with Session(ai_environment[0]) as db:
        assert db.scalar(select(func.count()).select_from(TaskRow)) == 0


@pytest.mark.postgres
def test_concurrent_same_proposal_one_accepted_lineage(ai_environment, http_provider):
    _, analysis, _, service = setup_ai(ai_environment, http_provider)
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(
            pool.map(
                lambda _: service.propose(ENV, analysis["analysis_id"], ai_principal(), now=AT), range(2)
            )
        )
    assert any(r["status"] == "ACCEPTED" for r in receipts)
    with Session(ai_environment[0]) as db:
        assert db.scalar(select(func.count()).select_from(AIProposalRow)) == 1
        assert db.scalar(select(func.count()).select_from(PlanRow)) == 1
        assert db.scalar(select(func.count()).select_from(TaskRow)) == 1


def test_aggregate_rejects_state_change_even_when_labeled_r0():
    from zhiyu.ai.outputs import PlanProposalOutput
    from zhiyu.ai.plan_validation import PlanAggregateRiskValidator
    from zhiyu.response.catalog import manifest

    data = proposal_output(
        {
            "body": {"trusted_facts": [{"evidence_id": "fixture-evidence"}]},
            "manifest": {"resource_ids": ["fixture-resource"]},
        }
    )
    proposal = PlanProposalOutput.model_validate(data)
    definition = manifest("collect_resource_context").model_copy(update={"operation_kind": "STATE_CHANGE"})
    result = PlanAggregateRiskValidator().validate(proposal, {definition.capability_id: definition})
    assert not result["valid"] and result["aggregate_risk"] == "R3" and result["state_changes"] == 1
