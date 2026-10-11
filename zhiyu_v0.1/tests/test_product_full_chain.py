"""Product DTOs are exercised against real core execution/AI/verification persistence.

Core fixtures are explicitly scripted/synthetic. The read clock matches their fixed fixture clock;
this is integration evidence for projection correctness, not live sensor/model acceptance.
"""

# ruff: noqa: F401, F811
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_ai_context import ai_principal
from test_ai_gateway import http_provider
from test_ai_planner import ai_environment, setup_ai
from test_response_authorization import authority_environment
from test_response_planner import ENV, INSTANT, SCOPE, response_environment
from test_verification_replan import closed_loop_environment, decide
from test_verification_runtime import AT, verification_environment, verifier

from zhiyu.db.models import ActionRow, AuditEntryRow
from zhiyu.product import projections, queries
from zhiyu.product.access import authorize, product_settings
from zhiyu.product.contracts import Query, ReadGrant
from zhiyu.verification.replan import DeterministicReplanner

pytestmark = pytest.mark.postgres


def read(engine, incident_id, monkeypatch):
    class FixtureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return AT + timedelta(seconds=3)

    monkeypatch.setattr(queries, "datetime", FixtureClock)
    principal = ai_principal().model_copy(update={"permissions": frozenset({"product:read"})})
    monkeypatch.setattr(
        product_settings,
        "grants",
        {principal.principal_id: {ENV: ReadGrant(version="integration", scope_ids={SCOPE})}},
    )
    query = Query(environment_id=ENV, scope_id=SCOPE, hours=24)
    with Session(engine) as db:
        before = db.scalar(select(func.count()).select_from(AuditEntryRow))
        result = queries.create_snapshot(db, query, authorize(db, principal, query), incident_id)
        assert db.scalar(select(func.count()).select_from(AuditEntryRow)) == before
    return result


@pytest.mark.parametrize("outcome", ["PASS", "FAIL", "INCONCLUSIVE"])
def test_all_execution_authorization_verification_facts(closed_loop_environment, monkeypatch, outcome):
    engine = closed_loop_environment[0]
    verification = decide(closed_loop_environment, outcome)
    DeterministicReplanner(engine).handle(ENV, verification.verification_id, verifier(), now=AT)
    snapshot = read(engine, verification.incident_id, monkeypatch)
    kinds = {fact.kind for fact in snapshot.facts}
    assert {"state", "state_update", "replan"} <= kinds
    assert {
        "raw",
        "normalization",
        "event",
        "group",
        "correlation",
        "incident",
        "plan",
        "task",
        "action",
        "authorization_context",
        "authorization",
        "risk",
        "attempt",
        "result",
        "verification_spec",
        "check",
        "observation",
        "verification",
        "evidence",
    } <= kinds
    result = next(fact for fact in snapshot.facts if fact.kind == "verification")
    assert result.fields["status"] == outcome
    assert all(
        f.fields["execution_outcome"] == "EXECUTION_SUCCESS" for f in snapshot.facts if f.kind == "result"
    )
    if outcome != "PASS":
        assert result.fields["status"] != "PASS"  # A successful executor cannot override independent checks.
    assert len({f.ref for f in snapshot.facts}) == len(snapshot.facts)
    for view in (projections.timeline(snapshot), projections.graph(snapshot)):
        assert (
            view["snapshot_id"] == snapshot.snapshot_id and view["content_sha256"] == snapshot.content_sha256
        )


@pytest.mark.parametrize("fault", [None, "hallucination"])
def test_scripted_ai_sources_grounding_and_zero_action_after_proposal(
    ai_environment, http_provider, monkeypatch, fault
):
    context, analysis, gateway, planner = setup_ai(ai_environment, http_provider, mode="SHADOW")
    if fault:
        http_provider[0]["output"]["proposed_tasks"][0]["capability_id"] = "nonexistent-capability"
    proposal = planner.propose(ENV, analysis["analysis_id"], ai_principal(), now=AT)
    snapshot = read(ai_environment[0], context["body"]["incident"]["incident_id"], monkeypatch)
    by_kind = {fact.kind: fact for fact in snapshot.facts}
    assert {
        "context",
        "ai_context",
        "model_request",
        "model_receipt",
        "model_run",
        "analysis",
        "proposal",
    } <= by_kind.keys()
    assert by_kind["analysis"].basis == by_kind["proposal"].basis == "MODEL_INFERENCE"
    assert by_kind["analysis"].fields["incident_summary"]
    assert by_kind["analysis"].fields["semantic_correctness"] == "NOT_VALIDATED"
    assert by_kind["proposal"].fields["status"] == proposal["status"]
    if fault:
        assert proposal["status"] == "REJECTED"
        assert "reasoning_summary" not in by_kind["proposal"].fields
    with Session(ai_environment[0]) as db:
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0
