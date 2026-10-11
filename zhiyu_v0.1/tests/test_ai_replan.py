"""AI replan shares original lifecycle, authorization and finite root budgets."""

# ruff: noqa: F811
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_ai_analysis import grounded
from test_ai_context import AT
from test_ai_gateway import http_provider  # noqa: F401
from test_ai_planner import proposal_output
from test_response_authorization import authority_environment  # noqa: F401
from test_response_gateway import claim, execute
from test_response_planner import ENV, SCOPE, response_environment  # noqa: F401
from test_verification_replan import closed_loop_environment, decide  # noqa: F401
from test_verification_runtime import verification_environment, verifier  # noqa: F401

from zhiyu.ai.analysis import AISituationAnalyzer
from zhiyu.ai.context import ContextManager
from zhiyu.ai.gateway import ModelGateway
from zhiyu.ai.planner import AIPlanner
from zhiyu.ai.policy import AIBudget, AIPolicy
from zhiyu.db.ai_gateway import AIIncidentBudgetRow
from zhiyu.db.models import IncidentRow, PlanRow
from zhiyu.db.verification_replan import ReplanBudgetRow, ReplanDecisionRow, ResponseCycleRow
from zhiyu.verification.replan import DeterministicReplanner


@pytest.mark.postgres
@pytest.mark.parametrize("ai_limit", [0, 1])
def test_bounded_ai_replan_or_deterministic_fallback(closed_loop_environment, http_provider, ai_limit):
    engine = closed_loop_environment[0]
    result = decide(closed_loop_environment, "FAIL")
    p = verifier().model_copy(
        update={
            "permissions": verifier().permissions
            | {"ai:context", "ai:analyze", "ai:plan", "ai:read", "incidents:write"}
        }
    )
    with Session(engine) as db:
        incident = db.scalar(select(IncidentRow)).incident_id
    ctx = ContextManager(engine).build(ENV, incident, SCOPE, p, now=AT)
    state, config = http_provider
    gateway = ModelGateway(
        engine,
        AIPolicy(
            enabled=True,
            mode="ASSISTED",
            provider_id=config.provider,
            budget=AIBudget(max_ai_replans=ai_limit),
        ),
        config,
    )
    state["output"] = grounded(ctx)
    analysis = AISituationAnalyzer(engine, gateway).analyze(ENV, ctx["context_id"], p, now=AT)
    assert analysis["status"] == "REFERENCE_GROUNDED"
    state["output"] = proposal_output(ctx, "query_event_history")
    planner = AIPlanner(engine, gateway)
    proposal = planner.propose(
        ENV, analysis["analysis_id"], p, parent_verification_id=result.verification_id, now=AT
    )
    assert proposal["status"] == ("ACCEPTED" if ai_limit else "FALLBACK")
    assert (
        planner.propose(
            ENV, analysis["analysis_id"], p, parent_verification_id=result.verification_id, now=AT
        )
        == proposal
    )
    if not ai_limit:
        fallback = DeterministicReplanner(engine).handle(ENV, result.verification_id, p, now=AT)
        assert fallback["status"] == "CREATED"
    with Session(engine) as db:
        decision = db.get(ReplanDecisionRow, result.verification_id)
        new = db.get(PlanRow, decision.new_plan_id)
        cycle = db.get(ResponseCycleRow, new.plan_id)
        assert bool(new.model_run_id) is bool(ai_limit)
        assert db.get(ReplanBudgetRow, cycle.root_plan_id).current_replan_count == 1
        assert db.scalar(select(AIIncidentBudgetRow.ai_replans)) == ai_limit
        assert db.scalar(select(IncidentRow)).status == "PLANNED"
    execute_at = AT + timedelta(seconds=1)
    receipt, auth = execute(engine, claim(engine, now=execute_at), now=execute_at)
    assert auth.outcome == "ALLOW" and receipt["execution_outcome"] == "EXECUTION_SUCCESS"


@pytest.mark.postgres
def test_ai_cannot_replan_passing_verification(closed_loop_environment, http_provider):
    engine = closed_loop_environment[0]
    result = decide(closed_loop_environment, "PASS")
    p = verifier().model_copy(
        update={"permissions": verifier().permissions | {"ai:context", "ai:analyze", "ai:plan"}}
    )
    with Session(engine) as db:
        incident = db.scalar(select(IncidentRow)).incident_id
    ctx = ContextManager(engine).build(ENV, incident, SCOPE, p, now=AT)
    state, config = http_provider
    gateway = ModelGateway(
        engine, AIPolicy(enabled=True, mode="ASSISTED", provider_id=config.provider), config
    )
    state["output"] = grounded(ctx)
    analysis = AISituationAnalyzer(engine, gateway).analyze(ENV, ctx["context_id"], p, now=AT)
    state["output"] = proposal_output(ctx)
    proposal = AIPlanner(engine, gateway).propose(
        ENV, analysis["analysis_id"], p, parent_verification_id=result.verification_id, now=AT
    )
    assert proposal["status"] == "REJECTED"
    assert "verification_requires_no_replan_or_expired" in proposal["validation"]["reasons"]
    with Session(engine) as db:
        assert db.get(ReplanDecisionRow, result.verification_id) is None
