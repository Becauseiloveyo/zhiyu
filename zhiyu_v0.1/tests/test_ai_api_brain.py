"""API isolation and coordinator persistence over real PostgreSQL."""

# ruff: noqa: F811
import hashlib
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_ai_context import AT, ai_principal
from test_ai_gateway import http_provider  # noqa: F401
from test_ai_planner import ai_environment, setup_ai  # noqa: F401
from test_api_boundaries import TOKEN
from test_response_authorization import authority_environment  # noqa: F401
from test_response_gateway import claim, execute
from test_response_planner import ENV, SCOPE, response_environment  # noqa: F401

from zhiyu.ai.brain import DecisionBrain
from zhiyu.api.routes import ai
from zhiyu.core.config import settings
from zhiyu.core.errors import ConflictError
from zhiyu.db.ai_decisions import AIDecisionRow
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import ActionRow, EnvironmentRow, IncidentRow, PlanRow, ScopeRow
from zhiyu.db.session import get_db
from zhiyu.domain.contracts import ScopeDefinition
from zhiyu.main import app
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy


def brain_principal():
    p = ai_principal()
    return p.model_copy(
        update={
            "permissions": p.permissions | {"verification:write", "verification:replan", "incidents:write"}
        }
    )


@pytest.mark.postgres
@pytest.mark.parametrize("mismatch", ["scope", "configuration"])
def test_fallback_cannot_reuse_plan_with_different_inputs(ai_environment, http_provider, mismatch):
    engine = ai_environment[0]
    ctx, _, gateway, _ = setup_ai(ai_environment, http_provider)
    scope_id = SCOPE
    if mismatch == "scope":
        scope_id = "different-fallback-scope"
        with Session(engine) as db, db.begin():
            scope = contract_from(db.get(ScopeRow, (SCOPE, ENV)), ScopeDefinition)
            db.add(ScopeRow(**values_for(scope.model_copy(update={"scope_id": scope_id}), ScopeRow)))
            profile = db.get(EnvironmentRow, ENV)
            profile.scope_ids = [*profile.scope_ids, scope_id]
    policy = PlannerPolicy(max_replans=1 if mismatch == "configuration" else 2)
    with Session(engine) as db:
        DeterministicResponsePlanner(db, policy).create(
            ENV,
            ctx["body"]["incident"]["incident_id"],
            expected_version=ctx["body"]["incident"]["state_version"],
            scope_id=scope_id,
            principal=brain_principal(),
            now=AT,
        )
    http_provider[0]["fault"] = "http500"
    with pytest.raises(ConflictError, match="fallback identity reused"):
        DecisionBrain(engine, gateway).decide(ENV, ctx["context_id"], brain_principal(), now=AT)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AIDecisionRow)) == 0
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0
        assert db.scalar(select(IncidentRow)).status == "TRIAGED"


@pytest.mark.postgres
@pytest.mark.parametrize(
    "mode,fault,expected",
    [
        ("ASSISTED", None, "AI_ASSISTED"),
        ("SHADOW", None, "SHADOW"),
        ("ASSISTED", "http500", "DETERMINISTIC_FALLBACK"),
        ("ASSISTED", "hallucination", "REJECTED"),
    ],
)
def test_brain_replay_after_activation_keeps_one_plan(ai_environment, http_provider, mode, fault, expected):
    engine = ai_environment[0]
    ctx, _, gateway, _ = setup_ai(ai_environment, http_provider, mode=mode)
    if fault == "hallucination":
        http_provider[0]["output"]["proposed_tasks"][0]["capability_id"] = "disable_entire_network"
    else:
        http_provider[0]["fault"] = fault
    brain = DecisionBrain(engine, gateway)
    result = brain.decide(ENV, ctx["context_id"], brain_principal(), now=AT)
    assert result["status"] == expected
    engine.dispose()
    assert brain.decide(ENV, ctx["context_id"], brain_principal(), now=AT + timedelta(seconds=300)) == result
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AIDecisionRow)) == 1
        assert db.scalar(select(func.count()).select_from(PlanRow)) == (0 if expected == "REJECTED" else 1)
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0
        assert db.scalar(select(IncidentRow)).status == ("TRIAGED" if expected == "REJECTED" else "PLANNED")
    if expected != "REJECTED":
        at = AT + timedelta(seconds=1)
        receipt, auth = execute(engine, claim(engine, now=at), now=at)
        assert auth.outcome == "ALLOW" and receipt["execution_outcome"] == "EXECUTION_SUCCESS"


@pytest.mark.postgres
def test_scoped_api_pagination_metrics_and_configuration_not_caller_controlled(
    ai_environment, http_provider, monkeypatch
):
    engine = ai_environment[0]
    ctx, analysis, gateway, planner = setup_ai(ai_environment, http_provider)
    result = planner.propose(ENV, analysis["analysis_id"], ai_principal(), now=AT)
    monkeypatch.setattr(ai, "get_engine", lambda: engine)
    monkeypatch.setattr(
        settings, "service_tokens", {hashlib.sha256(TOKEN.encode()).hexdigest(): brain_principal()}
    )

    def session():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app, headers={"Authorization": "Bearer " + TOKEN}) as client:
            paths = [
                "contexts/" + ctx["context_id"],
                "analyses/" + analysis["analysis_id"],
                "plan-proposals/" + result["proposal_id"],
                "model-runs/" + result["model_run_id"],
            ]
            for path in paths:
                assert client.get("/v1/" + path).status_code == 200
            for path, count in [
                ("model-runs", 2),
                ("ai-analyses", 1),
                ("ai-proposals", 1),
                ("ai-contexts", 1),
            ]:
                params, items = {"environment_id": ENV, "limit": 1}, []
                while True:
                    page = client.get("/v1/" + path, params=params).json()
                    items += page["items"]
                    if not page["next_cursor"]:
                        break
                    params["cursor"] = page["next_cursor"]
                assert len(items) == count
                assert (
                    client.get("/v1/" + path, params={"environment_id": ENV, "limit": 101}).status_code == 422
                )
                assert (
                    client.get("/v1/" + path, params={"environment_id": ENV, "cursor": "invalid"}).status_code
                    == 422
                )
            metrics = client.get("/v1/ai-metrics", params={"environment_id": ENV}).json()
            assert (
                metrics["model_calls"] == 2 and metrics["input_tokens"] == 200 and metrics["cost_usd"] is None
            )
            assert metrics["mean_ms"]["provider"] >= 0 and metrics["mean_context_chars"] > 0
            assert (
                client.post(
                    "/v1/contexts/" + ctx["context_id"] + "/ai-decision",
                    json={"environment_id": ENV, "mode": "ASSISTED", "provider": "untrusted"},
                ).status_code
                == 422
            )
            monkeypatch.setattr(
                settings,
                "service_tokens",
                {
                    hashlib.sha256(TOKEN.encode()).hexdigest(): brain_principal().model_copy(
                        update={"environment_ids": {"other"}}
                    )
                },
            )
            for path in paths:
                assert client.get("/v1/" + path).status_code == 404
            assert client.get("/v1/ai-metrics", params={"environment_id": ENV}).status_code == 403
    finally:
        app.dependency_overrides.clear()
