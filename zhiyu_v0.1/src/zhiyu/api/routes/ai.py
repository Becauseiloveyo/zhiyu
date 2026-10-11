"""Scoped bounded AI APIs. Provider, keys, mode and budgets are operator configuration."""

import base64
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.ai.analysis import AISituationAnalyzer
from zhiyu.ai.brain import DecisionBrain
from zhiyu.ai.context import ContextManager
from zhiyu.ai.gateway import ModelGateway
from zhiyu.ai.planner import AIPlanner
from zhiyu.ai.policy import AIPolicy
from zhiyu.api.routes.response import EnvironmentRequest
from zhiyu.api.security import require_principal
from zhiyu.core.config import settings
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.ai_analysis import SituationAnalysisRow
from zhiyu.db.ai_context import DecisionContextRow
from zhiyu.db.ai_decisions import AIDecisionRow
from zhiyu.db.ai_gateway import ModelReceiptRow, ModelRequestRow
from zhiyu.db.ai_planning import AIProposalRow
from zhiyu.db.models import ModelRunRow
from zhiyu.db.session import get_db, get_engine
from zhiyu.services.incident_queries import cursor_filter

router = APIRouter(prefix="/v1", tags=["ai-decision"])


class ContextRequest(EnvironmentRequest):
    scope_id: str = Field(min_length=1, max_length=128)


class ReplanRequest(EnvironmentRequest):
    verification_id: str = Field(min_length=1, max_length=128)


def gateway(env: str) -> ModelGateway:
    policy = settings.ai_policies.get(env, AIPolicy())
    return ModelGateway(get_engine(), policy, settings.ai_providers.get(policy.provider_id or ""))


def scoped(row: Any, principal: ServicePrincipal) -> Any:
    if row is None or row.environment_id not in principal.environment_ids:
        raise HTTPException(404, "AI object not found")
    principal.require("ai:read", row.environment_id)
    return row


def record(row: Any) -> dict[str, Any]:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


@router.post("/incidents/{incident_id}/contexts")
def context(
    incident_id: str, body: ContextRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    return ContextManager(get_engine()).build(body.environment_id, incident_id, body.scope_id, principal)


@router.post("/incidents/{incident_id}/ai-analysis")
def analyze_incident(
    incident_id: str, body: ContextRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    principal.require("ai:analyze", body.environment_id)
    ctx = context(incident_id, body, principal)
    return AISituationAnalyzer(get_engine(), gateway(body.environment_id)).analyze(
        body.environment_id, ctx["context_id"], principal
    )


@router.post("/contexts/{context_id}/ai-analysis")
def analyze_context(
    context_id: str, body: EnvironmentRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    return AISituationAnalyzer(get_engine(), gateway(body.environment_id)).analyze(
        body.environment_id, context_id, principal
    )


@router.post("/analyses/{analysis_id}/plan-proposals")
def proposal(
    analysis_id: str, body: EnvironmentRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    return AIPlanner(get_engine(), gateway(body.environment_id)).propose(
        body.environment_id, analysis_id, principal
    )


@router.post("/contexts/{context_id}/ai-decision")
def decide(
    context_id: str, body: EnvironmentRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    return DecisionBrain(get_engine(), gateway(body.environment_id)).decide(
        body.environment_id, context_id, principal
    )


@router.post("/contexts/{context_id}/ai-replan")
def replan(
    context_id: str, body: ReplanRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    return DecisionBrain(get_engine(), gateway(body.environment_id)).replan(
        body.environment_id, context_id, body.verification_id, principal
    )


@router.get("/model-runs/{identifier}")
def model_run(
    identifier: str, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> dict[str, Any]:
    run = scoped(db.get(ModelRunRow, identifier), principal)
    receipt = db.scalar(select(ModelReceiptRow).where(ModelReceiptRow.model_run_id == identifier))
    return {
        "model_run": record(run),
        "receipt": None
        if not receipt
        else {
            k: getattr(receipt, k)
            for k in (
                "request_id",
                "status",
                "error_code",
                "usage_known",
                "provider_ms",
                "overhead_ms",
                "schema_validation_ms",
            )
        },
    }


@router.get("/contexts/{identifier}")
def read_context(
    identifier: str, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return ContextManager._receipt(scoped(db.get(DecisionContextRow, identifier), principal))


@router.get("/analyses/{identifier}")
def read_analysis(
    identifier: str, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return AISituationAnalyzer._public(scoped(db.get(SituationAnalysisRow, identifier), principal))


@router.get("/plan-proposals/{identifier}")
def read_proposal(
    identifier: str, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return AIPlanner.public(scoped(db.get(AIProposalRow, identifier), principal))


@router.get("/model-runs")
@router.get("/ai-analyses")
@router.get("/ai-proposals")
@router.get("/ai-contexts")
def list_records(
    environment_id: str,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    principal.require("ai:read", environment_id)
    row: Any
    row, timestamp, key = {
        "model-runs": (ModelRunRow, "started_at", "run_id"),
        "ai-analyses": (SituationAnalysisRow, "created_at", "analysis_id"),
        "ai-proposals": (AIProposalRow, "created_at", "proposal_id"),
        "ai-contexts": (DecisionContextRow, "created_at", "context_id"),
    }[request.url.path.rsplit("/", 1)[-1]]
    rows = list(
        db.scalars(
            select(row)
            .where(
                row.environment_id == environment_id,
                cursor_filter(cursor, environment_id, getattr(row, timestamp), getattr(row, key)),
            )
            .order_by(getattr(row, timestamp), getattr(row, key))
            .limit(limit + 1)
        )
    )
    last = rows[limit - 1] if len(rows) > limit else None
    # Lists are summaries; a bounded detailed object is available from its own endpoint.
    return {
        "items": [
            {k: getattr(r, k) for k in (key, "environment_id", "incident_id", timestamp)}
            for r in rows[:limit]
        ],
        "next_cursor": base64.urlsafe_b64encode(
            json.dumps([environment_id, getattr(last, timestamp).isoformat(), getattr(last, key)]).encode()
        ).decode()
        if last
        else None,
    }


@router.get("/ai-metrics")
def metrics(
    environment_id: str,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    principal.require("ai:read", environment_id)

    def count(row: Any, *conditions: Any) -> int:
        return int(
            db.scalar(
                select(func.count()).select_from(row).where(row.environment_id == environment_id, *conditions)
            )
            or 0
        )

    def average(row: Any, field: Any) -> float | None:
        value = db.scalar(select(func.avg(field)).where(row.environment_id == environment_id))
        return float(value) if value is not None else None

    receipts = (
        select(ModelReceiptRow)
        .join(ModelRequestRow)
        .where(ModelRequestRow.environment_id == environment_id)
        .subquery()
    )
    return {
        "model_calls": count(ModelRunRow),
        "input_tokens": int(
            db.scalar(
                select(func.sum(ModelRunRow.input_tokens)).where(ModelRunRow.environment_id == environment_id)
            )
            or 0
        ),
        "output_tokens": int(
            db.scalar(
                select(func.sum(ModelRunRow.output_tokens)).where(
                    ModelRunRow.environment_id == environment_id
                )
            )
            or 0
        ),
        "model_failures": count(ModelRequestRow, ModelRequestRow.status == "FALLBACK"),
        "fallback_decisions": count(AIDecisionRow, AIDecisionRow.status == "DETERMINISTIC_FALLBACK"),
        "invalid_outputs": int(
            db.scalar(
                select(func.count())
                .select_from(receipts)
                .where(
                    receipts.c.error_code.in_(
                        ["SCHEMA_INVALID", "UNSAFE_MODEL_OUTPUT", "INVALID_JSON_OR_ENVELOPE"]
                    )
                )
            )
            or 0
        ),
        "rejected_proposals": count(AIProposalRow, AIProposalRow.status == "REJECTED"),
        "cost_usd": None,
        "cost_semantics": "NOT_REPORTED_BY_PROVIDER",
        "mean_ms": {
            "context": average(DecisionContextRow, DecisionContextRow.build_ms),
            "model_end_to_end": average(ModelRunRow, ModelRunRow.latency_ms),
            "provider": db.scalar(select(func.avg(receipts.c.provider_ms))),
            "gateway_overhead": db.scalar(select(func.avg(receipts.c.overhead_ms))),
            "schema": db.scalar(select(func.avg(receipts.c.schema_validation_ms))),
            "grounding": average(SituationAnalysisRow, SituationAnalysisRow.grounding_ms),
            "planning": average(AIProposalRow, AIProposalRow.planning_ms),
            "fallback": average(AIDecisionRow, AIDecisionRow.fallback_ms),
        },
        "mean_context_chars": float(
            db.scalar(
                select(func.avg(DecisionContextRow.manifest["chars"].as_integer())).where(
                    DecisionContextRow.environment_id == environment_id
                )
            )
            or 0
        ),
    }
