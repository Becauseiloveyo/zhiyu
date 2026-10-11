"""Scoped continuous verification and lineage APIs; bounded pagination."""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.api.security import require_principal
from zhiyu.core.errors import ConflictError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import ActionRow, IncidentRow, PlanRow, VerificationResultRow, VerificationSpecRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.response_planning import ResponsePlanRow
from zhiyu.db.session import get_db, get_engine
from zhiyu.db.verification_decisions import EffectivenessRow
from zhiyu.db.verification_replan import ReplanDecisionRow, VerificationStateUpdateRow
from zhiyu.db.verification_runtime import (
    VerificationCheckRow,
    VerificationObservationRow,
    VerificationRuntimeRow,
)
from zhiyu.domain.contracts import AIPlan, VerificationResult, VerificationSpec
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy, identity
from zhiyu.services.incident_queries import cursor_filter, page
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.policy import VerificationPolicy
from zhiyu.verification.replan import DeterministicReplanner, ReplanBudget, activate
from zhiyu.verification.runtime import VerificationService

router = APIRouter(prefix="/v1", tags=["continuous-verification"])


class EnvironmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment_id: str = Field(min_length=1, max_length=128)


class VerificationRequest(EnvironmentRequest):
    action_result_id: str
    spec: VerificationSpec
    policy: VerificationPolicy = VerificationPolicy()


class ContinuousPlanRequest(EnvironmentRequest):
    incident_id: str
    expected_version: int = Field(ge=1)
    scope_id: str
    include_http_probe: bool = True
    budget: ReplanBudget = ReplanBudget()


def record(row: Any) -> dict[str, Any] | None:
    return None if row is None else {c.name: getattr(row, c.name) for c in row.__table__.columns}


def scoped(db: Session, spec_id: str, principal: ServicePrincipal) -> VerificationRuntimeRow:
    row = db.get(VerificationRuntimeRow, spec_id)
    if row is None or row.environment_id not in principal.environment_ids:
        raise HTTPException(404, "verification not found")
    principal.require("verification:read", row.environment_id)
    return row


@router.post("/continuous-plans")
def create_plan(
    body: ContinuousPlanRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    principal.require("verification:write", body.environment_id)
    principal.require("response:plan", body.environment_id)
    policy = PlannerPolicy(include_http_probe=body.include_http_probe, max_replans=body.budget.max_replans)
    plan_id = identity(
        "plan",
        [
            body.environment_id,
            body.incident_id,
            body.expected_version,
            policy.planner_version,
            policy.policy_version,
        ],
    )
    with Session(get_engine()) as db:
        previous = db.get(ResponsePlanRow, plan_id)
        plan_row = db.get(PlanRow, plan_id)
        if previous and (previous.scope_id != body.scope_id or previous.configuration != asdict(policy)):
            raise ConflictError("continuous plan identity reused with different configuration")
        plan = contract_from(plan_row, AIPlan) if plan_row else None
    if plan is None:
        with Session(get_engine()) as db:
            plan = DeterministicResponsePlanner(db, policy).create(
                body.environment_id,
                body.incident_id,
                expected_version=body.expected_version,
                scope_id=body.scope_id,
                principal=principal,
            )
    activate(get_engine(), body.environment_id, plan.plan_id, principal, body.budget)
    return plan.model_dump(mode="json")


@router.post("/verifications")
def create_spec(
    body: VerificationRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, str]:
    return {
        "verification_spec_id": VerificationService(get_engine()).create(
            body.environment_id, body.action_result_id, body.spec, principal, body.policy
        )
    }


@router.post("/verifications/{spec_id}/tick")
def tick(
    spec_id: str, body: EnvironmentRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    service = VerificationService(get_engine())
    lease = service.claim(body.environment_id, principal, spec_id=spec_id)
    return (
        {"status": "IDLE"}
        if lease is None
        else {"lease": lease, "result": service.run_claim(body.environment_id, lease, principal)}
    )


@router.post("/verifications/{spec_id}/decide")
def decide(
    spec_id: str, body: EnvironmentRequest, principal: ServicePrincipal = Depends(require_principal)
) -> VerificationResult:
    return VerificationEngine(get_engine()).decide(body.environment_id, spec_id, principal)


@router.post("/verification-results/{verification_id}/apply")
def apply_result(
    verification_id: str, body: EnvironmentRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    return DeterministicReplanner(get_engine()).handle(body.environment_id, verification_id, principal)


@router.get("/verifications/{identifier}")
def get_verification(
    identifier: str, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> dict[str, Any]:
    result = db.get(VerificationResultRow, identifier)
    runtime = scoped(db, result.verification_spec_id if result else identifier, principal)
    result = result or db.scalar(
        select(VerificationResultRow).where(VerificationResultRow.verification_spec_id == runtime.spec_id)
    )
    return {
        "spec": record(db.get(VerificationSpecRow, runtime.spec_id)),
        "runtime": record(runtime),
        "result": record(result),
        "effectiveness": record(db.get(EffectivenessRow, result.verification_id)) if result else None,
        "state_update": record(db.get(VerificationStateUpdateRow, result.verification_id))
        if result
        else None,
        "replan": record(db.get(ReplanDecisionRow, result.verification_id)) if result else None,
    }


@router.get("/verifications/{spec_id}/checks")
def checks(
    spec_id: str,
    after: str = "",
    limit: int = Query(default=50, ge=1, le=200),
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    scoped(db, spec_id, principal)
    rows = list(
        db.scalars(
            select(VerificationCheckRow)
            .where(VerificationCheckRow.spec_id == spec_id, VerificationCheckRow.check_id > after)
            .order_by(VerificationCheckRow.check_id)
            .limit(limit + 1)
        )
    )
    return {
        "items": [
            {
                "check": record(row),
                "observation": record(db.get(VerificationObservationRow, (spec_id, row.check_id))),
            }
            for row in rows[:limit]
        ],
        "next_cursor": rows[limit - 1].check_id if len(rows) > limit else None,
    }


@router.get("/incidents/{incident_id}/verifications")
def incident_verifications(
    incident_id: str,
    environment_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    principal.require("verification:read", environment_id)
    return page(
        db,
        select(VerificationResultRow).where(
            VerificationResultRow.incident_id == incident_id,
            VerificationResultRow.environment_id == environment_id,
        ),
        environment_id=environment_id,
        row_type=VerificationResultRow,
        contract_type=VerificationResult,
        time_field="started_at",
        id_field="verification_id",
        limit=limit,
        cursor=cursor,
    )


@router.get("/incidents/{incident_id}/timeline")
def timeline(
    incident_id: str,
    environment_id: str,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = None,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    import base64
    import json

    principal.require("verification:read", environment_id)
    incident = db.get(IncidentRow, incident_id)
    if not incident or incident.environment_id != environment_id:
        raise HTTPException(404, "incident not found")
    rows = list(
        db.scalars(
            select(ResponsePlanRow)
            .where(
                ResponsePlanRow.incident_id == incident_id,
                ResponsePlanRow.environment_id == environment_id,
                cursor_filter(cursor, environment_id, ResponsePlanRow.created_at, ResponsePlanRow.plan_id),
            )
            .order_by(ResponsePlanRow.created_at, ResponsePlanRow.plan_id)
            .limit(limit + 1)
        )
    )
    items = []
    for row in rows[:limit]:
        plan = db.get(PlanRow, row.plan_id)
        assert plan is not None
        actions = list(
            db.scalars(
                select(ActionRow).where(
                    ActionRow.environment_id == environment_id,
                    ActionRow.task_id.in_([t["task_id"] for t in plan.tasks]),
                )
            )
        )
        receipts = list(
            db.scalars(
                select(ActionResultRow)
                .join(ActionDispatchRow)
                .where(ActionDispatchRow.action_id.in_([a.action_id for a in actions]))
            )
        )
        verifications = list(
            db.scalars(select(VerificationRuntimeRow).where(VerificationRuntimeRow.plan_id == row.plan_id))
        )
        items.append(
            {
                "plan": record(plan),
                "metadata": record(row),
                "actions": [record(a) for a in actions],
                "action_results": [record(r) for r in receipts],
                "verifications": [record(v) for v in verifications],
            }
        )
    last = rows[limit - 1] if len(rows) > limit else None
    return {
        "incident": record(incident),
        "items": items,
        "next_cursor": base64.urlsafe_b64encode(
            json.dumps([environment_id, last.created_at.isoformat(), last.plan_id]).encode()
        ).decode()
        if last
        else None,
    }


@router.get("/verification-metrics")
def metrics(
    environment_id: str,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    principal.require("verification:read", environment_id)
    counts: dict[str, int] = dict(
        db.execute(
            select(VerificationResultRow.status, func.count())
            .where(VerificationResultRow.environment_id == environment_id)
            .group_by(VerificationResultRow.status)
        )
        .tuples()
        .all()
    )
    replans: dict[str, int] = dict(
        db.execute(
            select(ReplanDecisionRow.status, func.count())
            .join(VerificationResultRow)
            .where(VerificationResultRow.environment_id == environment_id)
            .group_by(ReplanDecisionRow.status)
        )
        .tuples()
        .all()
    )
    dimension = VerificationCheckRow.definition["dimension"].astext
    check_counts: dict[str, int] = dict(
        db.execute(
            select(dimension, func.count())
            .join(VerificationObservationRow)
            .where(
                VerificationCheckRow.environment_id == environment_id,
                VerificationObservationRow.assertion_status == "FAIL",
            )
            .group_by(dimension)
        )
        .tuples()
        .all()
    )
    total_checks = db.scalar(
        select(func.count())
        .select_from(VerificationCheckRow)
        .where(VerificationCheckRow.environment_id == environment_id)
    )
    evidence_count = db.scalar(
        select(func.count())
        .select_from(VerificationObservationRow)
        .join(VerificationRuntimeRow, VerificationRuntimeRow.spec_id == VerificationObservationRow.spec_id)
        .where(VerificationRuntimeRow.environment_id == environment_id)
    )
    mean = db.scalar(
        select(
            func.avg(
                func.extract("epoch", VerificationResultRow.finished_at - VerificationResultRow.started_at)
                * 1000
            )
        ).where(VerificationResultRow.environment_id == environment_id)
    )
    return {
        "verification_total": sum(counts.values()),
        "verification_pass": counts.get("PASS", 0),
        "verification_fail": counts.get("FAIL", 0),
        "verification_inconclusive": counts.get("INCONCLUSIVE", 0),
        "check_total": total_checks,
        "security_check_fail": check_counts.get("SECURITY", 0),
        "business_check_fail": check_counts.get("BUSINESS", 0),
        "observability_check_fail": check_counts.get("OBSERVATION", 0),
        "replan_total": replans.get("CREATED", 0),
        "replan_exhausted": replans.get("REPLAN_EXHAUSTED", 0),
        "mean_verification_latency_ms": float(mean) if mean is not None else None,
        "verification_evidence_count": (evidence_count or 0) + sum(counts.values()),
    }
