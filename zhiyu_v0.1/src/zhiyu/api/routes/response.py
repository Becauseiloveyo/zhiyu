"""Environment-scoped response APIs; all writes require an authenticated service principal."""

import base64
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from zhiyu.api.security import require_principal
from zhiyu.core.errors import ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import (
    ActionRow,
    AuthorizationContextRow,
    AuthorizationDecisionRow,
    CapabilityHealthRow,
    CapabilityRow,
    EnvironmentRow,
    PlanRow,
    TaskRow,
)
from zhiyu.db.response_authority import (
    ActionControlRow,
    AuthorizationSnapshotRow,
    CapabilityConfigRow,
    ResponseControlRow,
)
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.response_planning import ResponsePlanRow, TaskRuntimeRow
from zhiyu.db.session import get_db, get_engine
from zhiyu.domain.contracts import (
    ActionRequest,
    AIPlan,
    AuthorizationContext,
    AuthorizationDecision,
    CapabilityHealth,
    CapabilityManifest,
    Task,
    TaskStatus,
)
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.gateway import ActionGateway, receipt
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy
from zhiyu.response.registry import CapabilityRegistry
from zhiyu.response.scheduler import TaskScheduler
from zhiyu.response.worker import ResponseWorker
from zhiyu.services.incident_queries import page

router = APIRouter(prefix="/v1", tags=["response-control"])


class EnvironmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment_id: str = Field(min_length=1, max_length=128)


class PlanRequest(EnvironmentRequest):
    expected_version: int = Field(ge=1)
    scope_id: str = Field(min_length=1, max_length=128)
    include_http_probe: bool = False


class LeaseRequest(EnvironmentRequest):
    generation: int = Field(ge=1)


class ExecuteRequest(LeaseRequest):
    authorization_id: str = Field(min_length=1, max_length=128)
    action_digest: str = Field(pattern="^[0-9a-f]{64}$")


def scoped(row: Any, principal: ServicePrincipal) -> Any:
    if row is None or row.environment_id not in principal.environment_ids:
        raise HTTPException(404, "object not found")
    principal.require("response:read", row.environment_id)
    return row


@router.post("/incidents/{incident_id}/plans")
def create_plan(
    incident_id: str,
    request: PlanRequest,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> AIPlan:
    policy = PlannerPolicy(
        include_http_probe=request.include_http_probe,
        policy_version="response-plan/1.0.0/probe" if request.include_http_probe else "response-plan/1.0.0",
    )
    return DeterministicResponsePlanner(db, policy).create(
        request.environment_id,
        incident_id,
        expected_version=request.expected_version,
        scope_id=request.scope_id,
        principal=principal,
    )


@router.get("/plans/{plan_id}")
def get_plan(
    plan_id: str, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> dict[str, Any]:
    row = scoped(db.get(PlanRow, plan_id), principal)
    metadata = db.get(ResponsePlanRow, plan_id)
    return {
        "plan": contract_from(row, AIPlan).model_dump(mode="json"),
        "metadata": None
        if metadata is None
        else {
            "planner_version": metadata.planner_version,
            "policy_version": metadata.policy_version,
            "incident_version": metadata.incident_version,
            "created_at": metadata.created_at.isoformat(),
            "reasons": metadata.reasons,
            "inputs": metadata.inputs,
            "generation_ms": metadata.generation_ms,
            "graph_ms": metadata.graph_ms,
        },
    }


@router.get("/tasks")
def get_tasks(
    environment_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    status: TaskStatus | None = None,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    principal.require("response:read", environment_id)
    query = (
        select(TaskRow)
        .join(TaskRuntimeRow, TaskRuntimeRow.task_id == TaskRow.task_id)
        .where(TaskRow.environment_id == environment_id)
    )
    if status:
        query = query.where(TaskRow.status == status.value)
    return page(
        db,
        query,
        environment_id=environment_id,
        row_type=TaskRow,
        contract_type=Task,
        time_field="created_at",
        id_field="task_id",
        limit=limit,
        cursor=cursor,
    )


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> dict[str, Any]:
    row = scoped(db.get(TaskRow, task_id), principal)
    runtime = db.get(TaskRuntimeRow, task_id)
    return {
        "task": contract_from(row, Task).model_dump(mode="json"),
        "runtime": None
        if runtime is None
        else {
            "plan_id": runtime.plan_id,
            "version": row.row_version,
            "generation": runtime.generation,
            "ready_at": runtime.ready_at.isoformat(),
            "failure_code": runtime.failure_code,
            "result_ref": runtime.result_ref,
            "retry_allowed": runtime.retry_allowed,
        },
    }


@router.get("/capabilities")
def get_capabilities(
    environment_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    principal.require("response:read", environment_id)
    environment = db.get(EnvironmentRow, environment_id)
    if environment is None:
        raise HTTPException(404, "environment not found")
    after: Any = True
    if cursor:
        try:
            if len(cursor) > 2048:
                raise ValueError("cursor length")
            cursor_env, cap_id, cap_version = json.loads(base64.urlsafe_b64decode(cursor))
            if cursor_env != environment_id or not all(
                isinstance(v, str) and 0 < len(v) <= 128 for v in (cap_id, cap_version)
            ):
                raise ValueError("cursor binding")
            after = or_(
                CapabilityRow.capability_id > cap_id,
                and_(CapabilityRow.capability_id == cap_id, CapabilityRow.version > cap_version),
            )
        except (ValueError, TypeError, UnicodeError) as error:
            raise ReferenceError("invalid capability page cursor") from error
    pairs = db.execute(
        select(CapabilityRow, CapabilityConfigRow)
        .join(
            CapabilityConfigRow,
            and_(
                CapabilityConfigRow.capability_id == CapabilityRow.capability_id,
                CapabilityConfigRow.version == CapabilityRow.version,
            ),
        )
        .where(CapabilityRow.capability_id.in_(environment.capability_allowlist), after)
        .order_by(CapabilityRow.capability_id, CapabilityRow.version)
        .limit(limit + 1)
    ).all()
    next_cursor = None
    if len(pairs) > limit:
        last = pairs[limit - 1][0]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps([environment_id, last.capability_id, last.version]).encode()
        ).decode()
    control = db.get(ResponseControlRow, environment_id)
    pool = ResponsePolicy.model_validate(control.configuration).worker_pool if control else "response"
    health_rows = {
        (h.capability_id, h.capability_version): h
        for h in db.scalars(
            select(CapabilityHealthRow).where(
                CapabilityHealthRow.environment_id == environment_id, CapabilityHealthRow.worker_pool == pool
            )
        )
    }
    return {
        "next_cursor": next_cursor,
        "items": [
            {
                "definition": contract_from(row, CapabilityManifest).model_dump(mode="json"),
                "active": config.active,
                "business_impact": config.business_impact,
                "minimum_autonomy": config.minimum_autonomy,
                "health": contract_from(
                    health_rows[row.capability_id, row.version], CapabilityHealth
                ).model_dump(mode="json")
                if (row.capability_id, row.version) in health_rows
                else None,
                "health_history": CapabilityRegistry(db).health_history(
                    environment_id, row.capability_id, row.version, pool
                ),
            }
            for row, config in pairs[:limit]
        ],
    }


@router.get("/actions/{action_id}")
def get_action(
    action_id: str, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> dict[str, Any]:
    row = scoped(db.get(ActionRow, action_id), principal)
    state = db.get(ActionControlRow, action_id)
    decision = (
        db.get(AuthorizationDecisionRow, state.authorization_id) if state and state.authorization_id else None
    )
    context = db.get(AuthorizationContextRow, decision.authorization_context_id) if decision else None
    snapshot = db.get(AuthorizationSnapshotRow, decision.authorization_context_id) if decision else None
    results = db.scalars(
        select(ActionResultRow)
        .join(ActionDispatchRow, ActionDispatchRow.attempt_id == ActionResultRow.attempt_id)
        .where(
            ActionDispatchRow.environment_id == row.environment_id, ActionDispatchRow.action_id == action_id
        )
        .order_by(ActionResultRow.started_at, ActionResultRow.attempt_id)
    )
    return {
        "action": contract_from(row, ActionRequest).model_dump(mode="json"),
        "action_digest": row.action_digest,
        "status": state.status if state else None,
        "policy_decision": contract_from(decision, AuthorizationDecision).model_dump(mode="json")
        if decision
        else None,
        "authorization_context": contract_from(context, AuthorizationContext).model_dump(mode="json")
        if context
        else None,
        "authorization_inputs": snapshot.inputs if snapshot else None,
        "results": [receipt(result, action_id, row.action_digest) for result in results],
    }


@router.post("/response/claim")
def claim(
    request: EnvironmentRequest,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return {"lease": TaskScheduler(db).claim(request.environment_id, principal)}


@router.post("/tasks/{task_id}/lease/renew")
def renew(
    task_id: str,
    request: LeaseRequest,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return {
        "expires_at": TaskScheduler(db).renew(request.environment_id, task_id, request.generation, principal)
    }


@router.post("/tasks/{task_id}/authorizations")
def authorize(
    task_id: str,
    request: LeaseRequest,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> AuthorizationDecision:
    return AuthorizationService(db).authorize_task(
        request.environment_id, task_id, generation=request.generation, principal=principal
    )


@router.post("/tasks/{task_id}/execute")
def execute(
    task_id: str, request: ExecuteRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    return ActionGateway(get_engine()).dispatch(
        request.environment_id,
        task_id,
        request.generation,
        request.authorization_id,
        principal,
        submitted_digest=request.action_digest,
    )


@router.post("/response/worker/tick")
def tick(
    request: EnvironmentRequest, principal: ServicePrincipal = Depends(require_principal)
) -> dict[str, Any]:
    principal.require("response:execute", request.environment_id)
    return ResponseWorker(get_engine()).tick(request.environment_id, principal)
