"""Browser-facing fixed demo intents. Only a separately configured lab worker executes steps."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi import Query as Parameter
from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.api.routes.product import DB, Params, Principal
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.demo_control import DemoRunRow
from zhiyu.db.session import get_db
from zhiyu.product import demo_control as controller
from zhiyu.product import queries
from zhiyu.product.access import authorize, product_settings
from zhiyu.product.budgets import response_budget
from zhiyu.product.contracts import Query
from zhiyu.product.demo_contracts import (
    TEMPLATES,
    DemoCommand,
    DemoMutationResponse,
    DemoRunPage,
    DemoRunResponse,
    StartDemo,
    template_hash,
)
from zhiyu.product.sessions import require_mutation

router = APIRouter(prefix="/v1/product/demos", tags=["product-demo"])
WriteDB = Annotated[Session, Depends(get_db)]
Operator = Annotated[ServicePrincipal, Depends(require_mutation)]


@router.get("/catalog")
def catalog(db: DB, principal: Principal, query: Params) -> dict:
    access = authorize(db, principal, query)
    profiles = [
        {
            "profile_id": key,
            "scope_id": value.scope_id,
            "scenarios": sorted(value.scenarios),
            "enabled": value.enabled,
        }
        for key, value in sorted(product_settings.demo_profiles.items())
        if value.environment_id == access.environment_id
        and (access.unrestricted or value.scope_id in access.scope_ids)
    ][:50]
    return response_budget(
        {
            **queries.envelope(query, access, datetime.now(UTC)),
            "items": [
                {"scenario_id": key, "version": "0.9.0", "template_sha256": template_hash(key), **value}
                for key, value in TEMPLATES.items()
            ],
            "profiles": profiles,
            "can_run": "demo:run" in principal.permissions,
            "worker_health": "UNKNOWN",
            "dispatch_semantics": "DURABLE_INTENT_REQUIRES_SEPARATE_WORKER",
        }
    )


@router.get("/runs", response_model=DemoRunPage)
def runs(
    db: DB, principal: Principal, query: Annotated[Query, Depends()], limit: int = Parameter(20, ge=1, le=50)
) -> dict:
    access = authorize(db, principal, query)
    rows = list(
        db.scalars(
            select(DemoRunRow)
            .where(*controller.visible(access))
            .order_by(DemoRunRow.created_at.desc(), DemoRunRow.run_id)
            .limit(limit + 1)
        )
    )
    return response_budget(
        {
            **queries.envelope(query, access, datetime.now(UTC)),
            "items": [controller.public_run(db, row) for row in rows[:limit]],
            "truncated": len(rows) > limit,
        }
    )


@router.get("/runs/{run_id}", response_model=DemoRunResponse)
def run_status(run_id: str, db: DB, principal: Principal, query: Params) -> dict:
    access = authorize(db, principal, query)
    return response_budget(
        {
            **queries.envelope(query, access, datetime.now(UTC)),
            "run": controller.public_run(db, controller.read_run(db, run_id, access)),
        }
    )


@router.post("/runs", status_code=202, response_model=DemoMutationResponse)
def start_run(body: StartDemo, db: WriteDB, principal: Operator, query: Params) -> dict:
    with db.begin():
        result = controller.public_run(db, controller.start(db, principal, query, body))
    return {"run": result}


@router.post("/runs/{run_id}/{operation}", status_code=202, response_model=DemoMutationResponse)
def run_command(
    run_id: str,
    operation: Literal["cancel", "cleanup", "reset"],
    body: DemoCommand,
    db: WriteDB,
    principal: Operator,
    query: Params,
) -> dict:
    with db.begin():
        result = controller.public_run(db, controller.command(db, principal, query, run_id, operation, body))
    return {"run": result}
