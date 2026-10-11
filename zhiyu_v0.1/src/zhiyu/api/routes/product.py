"""Versioned read API. It cannot create Tasks, Actions or model requests."""

from collections.abc import Iterator
from threading import BoundedSemaphore, Lock
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Query as Parameter
from sqlalchemy import text
from sqlalchemy.orm import Session

from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.session import get_db, get_engine
from zhiyu.product import projections, queries, reports, snapshots
from zhiyu.product.access import authorize, product_settings, read_grant
from zhiyu.product.budgets import response_budget
from zhiyu.product.contracts import (
    GraphProjection,
    Health,
    IncidentPage,
    Overview,
    Query,
    Snapshot,
    TimelinePage,
)
from zhiyu.product.sessions import require_product_principal as require_principal

router = APIRouter(prefix="/v1/product", tags=["product"])
_budget_lock = Lock()
_budgets: dict[str, BoundedSemaphore] = {}


def get_product_db(
    request: Request, principal: Annotated[ServicePrincipal, Depends(require_principal)]
) -> Iterator[Session]:
    env = request.query_params.get("environment_id", "")
    child_query = bool(product_settings.demo_profiles) and env.startswith("m6-real-demo-")
    if "product:read" not in principal.permissions:
        raise HTTPException(403, "product_read_not_granted")
    if not child_query:
        principal.require("product:read", env)
        if env not in product_settings.grants.get(principal.principal_id, {}):
            raise HTTPException(403, "product_read_not_granted")
    with _budget_lock:
        user_budget = _budgets.setdefault("user:" + principal.principal_id, BoundedSemaphore(2))
        env_budget = _budgets.setdefault(
            "demo-children" if child_query else "env:" + env, BoundedSemaphore(8)
        )
    if not user_budget.acquire(blocking=False):
        raise HTTPException(429, "reader_capacity_exceeded", headers={"Retry-After": "2"})
    if not env_budget.acquire(blocking=False):
        user_budget.release()
        raise HTTPException(429, "environment_read_capacity_exceeded", headers={"Retry-After": "2"})
    try:
        with get_engine().connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                connection.execute(text("SET LOCAL statement_timeout = '2000ms'"))
                with Session(bind=connection) as db:
                    read_grant(db, principal, env)
                    yield db
    finally:
        env_budget.release()
        user_budget.release()


DB = Annotated[Session, Depends(get_product_db)]
Principal = Annotated[ServicePrincipal, Depends(require_principal)]
Params = Annotated[Query, Parameter()]


@router.get("/access")
def access_catalog(principal: Principal, db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    if "product:read" not in principal.permissions:
        raise HTTPException(403, "product_read_not_granted")
    grants = dict(product_settings.grants.get(principal.principal_id, {}))
    children = set()
    if product_settings.demo_profiles:
        from sqlalchemy import select

        from zhiyu.db.demo_control import DemoRunRow
        from zhiyu.db.models import ScopeRow
        from zhiyu.product.demo_contracts import source_environment

        rows = db.scalars(
            select(DemoRunRow)
            .where(DemoRunRow.environment_id.in_(set(grants) & principal.environment_ids))
            .order_by(DemoRunRow.created_at.desc())
            .limit(50)
        )
        for row in rows:
            child = source_environment(row.run_id)
            try:
                grant, _ = read_grant(db, principal, child)
            except HTTPException:
                continue
            if db.scalar(
                select(ScopeRow.scope_id).where(
                    ScopeRow.environment_id == child, ScopeRow.scope_id == row.scope_id
                )
            ):
                grants[child] = grant
                children.add(child)
    return {
        "principal_id": principal.principal_id,
        "environments": [
            {
                "environment_id": env,
                "scope_ids": sorted(grant.scope_ids),
                "whole_environment": grant.whole_environment,
                "version": grant.version,
            }
            for env, grant in grants.items()
            if env in principal.environment_ids | children and (grant.whole_environment or grant.scope_ids)
        ],
    }


@router.get("/demo-scenarios")
def demo_scenarios(
    db: DB,
    principal: Principal,
    environment_id: str = Parameter(min_length=1, max_length=160),
    scope_id: str | None = Parameter(None, min_length=1, max_length=160),
    limit: int = Parameter(50, ge=1, le=200),
) -> dict[str, Any]:
    """Read-only core validation registry; fixed product demos use their own catalog."""
    from datetime import UTC, datetime

    from sqlalchemy import select

    from zhiyu.db.models import ValidationScenarioRow

    query = Query(environment_id=environment_id, scope_id=scope_id)
    access = authorize(db, principal, query)
    stmt = select(
        ValidationScenarioRow.scenario_id,
        ValidationScenarioRow.version,
        ValidationScenarioRow.scope_id,
        ValidationScenarioRow.implementation_status,
    ).where(ValidationScenarioRow.environment_id == environment_id)
    if not access.unrestricted:
        stmt = stmt.where(ValidationScenarioRow.scope_id.in_(access.scope_ids))
    rows = list(
        db.execute(
            stmt.order_by(ValidationScenarioRow.scenario_id, ValidationScenarioRow.version).limit(limit + 1)
        ).mappings()
    )
    return response_budget(
        {
            **queries.envelope(query, access, datetime.now(UTC)),
            "items": [dict(row) for row in rows[:limit]],
            "truncated": len(rows) > limit,
            "browser_lifecycle": "READ_ONLY_REGISTRY",
            "demo_catalog": "/v1/product/demos/catalog",
            "execution_available": False,
        }
    )


@router.get("/incidents", response_model=IncidentPage)
def incidents(
    db: DB,
    principal: Principal,
    query: Annotated[Query, Depends()],
    limit: int = Parameter(50, ge=1, le=200),
    cursor: str | None = Parameter(None, max_length=4096),
) -> IncidentPage:
    return response_budget(queries.incident_page(db, query, authorize(db, principal, query), limit, cursor))


@router.get("/recordings")
def recording_catalog(db: DB, principal: Principal, query: Params) -> dict[str, Any]:
    from datetime import UTC, datetime

    from zhiyu.product.recordings import entries as recording_entries

    access = authorize(db, principal, query)
    entries = sorted(recording_entries(db, access).items())
    return response_budget(
        {
            **queries.envelope(query, access, datetime.now(UTC)),
            "items": [
                {
                    "recording_id": key,
                    "title": value.title,
                    "sha256": value.sha256,
                    "source_run_id": value.source_run_id,
                    "model_source": value.model_source,
                    "run_mode": "RECORDED_REPLAY",
                }
                for key, value in entries[:50]
            ],
            "truncated": len(entries) > 50,
        }
    )


@router.get("/recordings/{recording_id}/snapshot", response_model=Snapshot)
def recording_snapshot(recording_id: str, db: DB, principal: Principal, query: Params) -> Snapshot:
    from zhiyu.product.recordings import open_recording

    return open_recording(db, recording_id, query, authorize(db, principal, query))


@router.get("/overview", response_model=Overview)
def overview(db: DB, principal: Principal, query: Params) -> Overview:
    return response_budget(queries.overview(db, query, authorize(db, principal, query)), 256 * 1024)


@router.get("/runtime-health", response_model=Health)
def runtime_health(db: DB, principal: Principal, query: Params) -> Health:
    return response_budget(queries.health(db, query, authorize(db, principal, query)), 256 * 1024)


@router.get("/incidents/{incident_id}/snapshot", response_model=Snapshot)
def incident_snapshot(incident_id: str, db: DB, principal: Principal, query: Params) -> Snapshot:
    return queries.create_snapshot(db, query, authorize(db, principal, query), incident_id)


@router.get("/snapshots/{snapshot_id}", response_model=Snapshot)
def snapshot(snapshot_id: str, db: DB, principal: Principal, query: Params) -> Snapshot:
    access = authorize(db, principal, query)
    result = snapshots.get(snapshot_id, queries.binding(query, access))
    # State/bindings may change after capture. Re-check current object visibility.
    from sqlalchemy import select

    from zhiyu.db.models import IncidentRow
    from zhiyu.product.access import visible_incidents

    if (
        db.scalar(
            select(IncidentRow.incident_id).where(
                *visible_incidents(access), IncidentRow.incident_id == result.incident_id
            )
        )
        is None
    ):
        raise HTTPException(404, "snapshot_not_found")
    return result


@router.get("/snapshots/{snapshot_id}/graph", response_model=GraphProjection)
def graph_view(
    snapshot_id: str,
    db: DB,
    principal: Principal,
    query: Annotated[Query, Depends()],
    root_ref: str | None = Parameter(None, min_length=1, max_length=512),
    depth: int = Parameter(2, ge=0, le=2),
) -> GraphProjection:
    material = snapshot(snapshot_id, db, principal, query)
    return response_budget(
        GraphProjection.model_validate(projections.graph(material, root_ref=root_ref, depth=depth))
    )


@router.get("/snapshots/{snapshot_id}/timeline", response_model=TimelinePage)
def timeline_view(
    snapshot_id: str,
    db: DB,
    principal: Principal,
    query: Annotated[Query, Depends()],
    limit: int = Parameter(50, ge=1, le=200),
    cursor: str | None = Parameter(None, max_length=4096),
) -> TimelinePage:
    import time

    material = snapshot(snapshot_id, db, principal, query)
    result = projections.timeline(material)
    bound = snapshots.digest([material.snapshot_id, material.content_sha256, "timeline"])
    offset = snapshots.decode_cursor(cursor, bound)["offset"] if cursor else 0
    entries = result.pop("entries")
    result["items"] = entries[offset : offset + limit]
    result["next_cursor"] = (
        snapshots.encode_cursor({"binding": bound, "offset": offset + limit, "expires": time.time() + 300})
        if len(entries) > offset + limit
        else None
    )
    return response_budget(TimelinePage.model_validate(result))


@router.get("/snapshots/{snapshot_id}/report", response_model=reports.Report)
def incident_report(snapshot_id: str, db: DB, principal: Principal, query: Params) -> reports.Report:
    return reports.build(snapshot(snapshot_id, db, principal, query))


@router.get("/snapshots/{snapshot_id}/report-markdown")
def report_markdown(snapshot_id: str, db: DB, principal: Principal, query: Params) -> dict[str, Any]:
    return reports.markdown(incident_report(snapshot_id, db, principal, query))


@router.get("/snapshots/{snapshot_id}/report-json")
def report_json(snapshot_id: str, db: DB, principal: Principal, query: Params) -> dict[str, Any]:
    return reports.json_export(incident_report(snapshot_id, db, principal, query))


@router.get("/snapshots/{snapshot_id}/{view}")
def snapshot_view(
    snapshot_id: str,
    view: Literal["ai", "verification"],
    db: DB,
    principal: Principal,
    query: Annotated[Query, Depends()],
) -> dict[str, Any]:
    material = snapshot(snapshot_id, db, principal, query)
    if view == "ai":
        return projections.section(
            material,
            {
                "ai_context",
                "context",
                "model_request",
                "model_receipt",
                "model_run",
                "analysis",
                "proposal",
                "decision",
            },
        )
    if view == "verification":
        return projections.section(
            material,
            {
                "verification_spec",
                "check",
                "observation",
                "verification",
                "evidence",
                "state_update",
                "state",
                "replan",
            },
        )
    raise HTTPException(404, "projection_view_not_found")
