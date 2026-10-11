"""Durable intent and crash fencing for fixed lab scenarios. No security execution here."""

import re
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.demo_control import DemoRunRow, DemoStepRow
from zhiyu.product.access import Access, authorize, product_settings
from zhiyu.product.contracts import Query
from zhiyu.product.demo_contracts import (
    STEPS,
    TEMPLATES,
    DemoCommand,
    Scenario,
    StartDemo,
    StepOutput,
    WorkItem,
    source_environment,
    template_hash,
)
from zhiyu.product.snapshots import digest
from zhiyu.repositories.audit import AuditRepository

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "NEEDS_RECONCILIATION"}
LEASE_SECONDS = 180
MAX_STEP_SECONDS = 600


def clock(db: Session) -> datetime:
    return db.execute(select(func.clock_timestamp())).scalar_one()


def audit(db: Session, run: DemoRunRow, actor: str, operation: str) -> None:
    AuditRepository(db).append(
        environment_id=run.environment_id,
        trace_id=run.run_id,
        actor_id=actor,
        object_kind="DemoRun",
        object_id=run.run_id,
        operation=operation,
        reason=f"template={run.template_sha256};version={run.version};request={run.request_sha256}",
    )


def public_run(db: Session, row: DemoRunRow) -> dict:
    columns = (
        "run_id environment_id scope_id scenario_id template_sha256 profile_id actor_id predecessor_id "
        "run_mode model_source status cleanup_status cancel_requested version step_index created_at updated_at "
        "deadline error_code actual_outcome"
    ).split()
    result = {key: getattr(row, key) for key in columns}
    result["source_environment_id"] = source_environment(row.run_id)
    result["expected_outcome"] = TEMPLATES[row.scenario_id]["expected"]
    result["planned_model_source"] = TEMPLATES[row.scenario_id]["model_source"]
    result["steps"] = [
        {
            "position": step.position,
            "operation": step.operation,
            "status": step.status,
            "generation": step.generation,
            "started_at": step.started_at,
            "finished_at": step.finished_at,
            "output": step.output,
        }
        for step in db.scalars(
            select(DemoStepRow)
            .where(DemoStepRow.run_id == row.run_id)
            .order_by(DemoStepRow.position)
            .limit(5)
        )
    ]
    result["completion_semantics"] = "SCENARIO_COMPLETION_NOT_SECURITY_PASS"
    return result


def visible(access: Access) -> list[Any]:
    clauses = [DemoRunRow.environment_id == access.environment_id]
    if not access.unrestricted:
        clauses.append(DemoRunRow.scope_id.in_(access.scope_ids))
    return clauses


def read_run(db: Session, identifier: str, access: Access, *, lock: bool = False) -> DemoRunRow:
    stmt = select(DemoRunRow).where(*visible(access), DemoRunRow.run_id == identifier)
    row = db.scalar(stmt.with_for_update() if lock else stmt)
    if row is None:
        raise HTTPException(404, "demo_run_not_found")
    return row


def start(
    db: Session, principal: ServicePrincipal, query: Query, body: StartDemo, predecessor: str | None = None
) -> DemoRunRow:
    principal.require("demo:run", query.environment_id)
    access = authorize(db, principal, query)
    profile = product_settings.demo_profiles.get(body.profile_id)
    if (
        not profile
        or not profile.enabled
        or profile.environment_id != access.environment_id
        or (not access.unrestricted and profile.scope_id not in access.scope_ids)
        or body.scenario_id not in profile.scenarios
    ):
        raise HTTPException(403, "demo_profile_not_granted")
    # Serialize create/reset in a registered profile. This is metadata locking, not an Action lease.
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": "demo-profile:" + profile.environment_id + ":" + body.profile_id},
    )
    request_hash = digest([body.model_dump(mode="json"), profile.model_dump(mode="json"), predecessor])
    existing = db.scalar(
        select(DemoRunRow).where(
            DemoRunRow.environment_id == query.environment_id,
            DemoRunRow.actor_id == principal.principal_id,
            DemoRunRow.idempotency_key == body.idempotency_key,
        )
    )
    if existing:
        if existing.request_sha256 != request_hash:
            raise HTTPException(409, "demo_idempotency_conflict")
        return existing
    if db.scalar(
        select(DemoRunRow.run_id)
        .where(
            DemoRunRow.environment_id == query.environment_id,
            DemoRunRow.profile_id == body.profile_id,
            DemoRunRow.cleanup_status != "CLEAN",
        )
        .limit(1)
    ):
        raise HTTPException(409, "demo_profile_requires_cleanup")
    now = clock(db)
    row = DemoRunRow(
        run_id="demo-" + uuid4().hex,
        environment_id=query.environment_id,
        scope_id=profile.scope_id,
        scenario_id=body.scenario_id,
        template_sha256=template_hash(body.scenario_id),
        profile_id=body.profile_id,
        actor_id=principal.principal_id,
        idempotency_key=body.idempotency_key,
        request_sha256=request_hash,
        predecessor_id=predecessor,
        run_mode="LIVE",
        model_source="NONE",
        status="QUEUED",
        cleanup_status="NOT_STARTED",
        cancel_requested=False,
        version=1,
        step_index=0,
        created_at=now,
        updated_at=now,
        deadline=now + timedelta(minutes=30),
        actual_outcome="UNKNOWN",
    )
    db.add(row)
    db.flush()
    audit(db, row, principal.principal_id, "DemoRunRequested")
    return row


def command(
    db: Session, principal: ServicePrincipal, query: Query, identifier: str, operation: str, body: DemoCommand
) -> DemoRunRow:
    principal.require("demo:run", query.environment_id)
    row = read_run(db, identifier, authorize(db, principal, query), lock=True)
    if operation == "reset" and body.idempotency_key and row.cleanup_status == "CLEAN":
        prior = db.scalar(
            select(DemoRunRow.run_id).where(
                DemoRunRow.environment_id == query.environment_id,
                DemoRunRow.actor_id == principal.principal_id,
                DemoRunRow.idempotency_key == body.idempotency_key,
            )
        )
        if prior is None and body.expected_version != row.version:
            raise HTTPException(409, "demo_version_conflict")
        # start() verifies the same idempotency digest even on a retry after the original reset response was lost.
        return start(
            db,
            principal,
            query,
            StartDemo(
                scenario_id=cast(Scenario, row.scenario_id),
                profile_id=row.profile_id,
                idempotency_key=body.idempotency_key,
            ),
            row.run_id,
        )
    if body.expected_version != row.version:
        raise HTTPException(409, "demo_version_conflict")
    if operation == "cancel":
        if row.status not in TERMINAL:
            row.cancel_requested = True
            if row.status == "QUEUED":
                row.status = "CANCELLED"
    elif operation == "cleanup":
        if row.status not in TERMINAL:
            raise HTTPException(409, "demo_stop_before_cleanup")
        if row.cleanup_status in {"NOT_STARTED", "QUEUED"}:
            row.cleanup_status = "QUEUED"
        elif row.cleanup_status != "CLEAN":
            raise HTTPException(409, "demo_cleanup_requires_reconciliation")
    elif operation == "reset":
        raise HTTPException(409, "demo_reset_requires_verified_cleanup_and_key")
    else:
        raise HTTPException(422, "unknown_demo_operation")
    row.version += 1
    row.updated_at = clock(db)
    audit(db, row, principal.principal_id, "Demo" + operation.title() + "Requested")
    db.flush()
    return row


def recover_expired(db: Session, profile_id: str) -> int:
    now = clock(db)
    rows = list(
        db.scalars(
            select(DemoRunRow)
            .where(DemoRunRow.profile_id == profile_id, DemoRunRow.lease_until < now)
            .limit(50)
            .with_for_update(skip_locked=True)
        )
    )
    for row in rows:
        cleanup = row.cleanup_status == "RUNNING"
        step = db.get(DemoStepRow, (row.run_id, 100 if cleanup else row.step_index))
        if step:
            step.status, step.finished_at = "UNKNOWN", now
        if cleanup:
            row.cleanup_status = "NEEDS_MANUAL"
        else:
            row.status = "NEEDS_RECONCILIATION"
        row.error_code = "WORKER_LEASE_EXPIRED_NO_REDISPATCH"
        row.lease_owner = row.lease_until = None
        row.version += 1
        row.updated_at = now
        audit(db, row, "demo-worker", "DemoLeaseExpired")
    return len(rows)


def claim(db: Session, profile_id: str, worker_id: str) -> WorkItem | None:
    profile = product_settings.demo_profiles.get(profile_id)
    if not profile or not profile.enabled:
        return None
    row = db.scalar(
        select(DemoRunRow)
        .where(
            DemoRunRow.profile_id == profile_id,
            DemoRunRow.environment_id == profile.environment_id,
            DemoRunRow.scope_id == profile.scope_id,
            (DemoRunRow.status == "QUEUED") | (DemoRunRow.cleanup_status == "QUEUED"),
        )
        .order_by(DemoRunRow.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if row is None:
        return None
    now = clock(db)
    cleanup = row.cleanup_status == "QUEUED"
    if not cleanup:
        from zhiyu.core.config import settings

        principals = [account.principal for account in product_settings.browser_users.values()]
        principals += list(settings.service_tokens.values())
        principal = next(
            (
                actor
                for actor in principals
                if actor.principal_id == row.actor_id
                and "demo:run" in actor.permissions
                and row.environment_id in actor.environment_ids
            ),
            None,
        )
        # Current grant, profile, and template are re-evaluated before every fixed step.
        try:
            if principal is None:
                raise HTTPException(403, "demo_actor_revoked")
            authorize(db, principal, Query(environment_id=row.environment_id, scope_id=row.scope_id))
            if row.scenario_id not in profile.scenarios or row.template_sha256 != template_hash(
                row.scenario_id
            ):
                raise HTTPException(403, "demo_template_changed")
        except HTTPException:
            row.status, row.error_code = "FAILED", "DEMO_GRANT_OR_TEMPLATE_REVOKED"
        if row.deadline <= now:
            row.status, row.error_code = "FAILED", "DEMO_DEADLINE_EXCEEDED"
        if row.cancel_requested:
            row.status = "CANCELLED"
        if row.status != "QUEUED":
            row.version += 1
            row.updated_at = now
            audit(db, row, worker_id, "DemoDispatchBlocked")
            return None
    position = 100 if cleanup else row.step_index
    if db.get(DemoStepRow, (row.run_id, position)) is not None:
        raise HTTPException(409, "demo_step_requires_reconciliation")
    row.version += 1
    row.lease_owner, row.lease_until = worker_id, now + timedelta(seconds=LEASE_SECONDS)
    row.updated_at = now
    if cleanup:
        row.cleanup_status = "RUNNING"
    else:
        row.status = "RUNNING"
    operation = "CLEANUP" if cleanup else STEPS[position]
    step = DemoStepRow(
        run_id=row.run_id,
        position=position,
        operation=operation,
        status="STARTED",
        generation=row.version,
        started_at=now,
        output={},
    )
    db.add(step)
    db.flush()
    audit(db, row, worker_id, "DemoStepIntentCommitted")
    return WorkItem(
        run_id=row.run_id,
        environment_id=row.environment_id,
        scope_id=row.scope_id,
        scenario_id=cast(Scenario, row.scenario_id),
        profile_id=profile_id,
        operation=operation,
        position=position,
        generation=row.version,
        lease_owner=worker_id,
        lease_until=row.lease_until,
        deadline=row.deadline,
    )


def finish(db: Session, work: WorkItem, output: StepOutput, *, failed: bool = False) -> DemoRunRow:
    row = db.scalar(select(DemoRunRow).where(DemoRunRow.run_id == work.run_id).with_for_update())
    step = db.get(DemoStepRow, (work.run_id, work.position))
    now = clock(db)
    if (
        not row
        or not step
        or step.status != "STARTED"
        or step.generation != work.generation
        or (row.lease_owner != work.lease_owner or row.lease_until is None or row.lease_until <= now)
        or now >= step.started_at + timedelta(seconds=MAX_STEP_SECONDS)
        or (work.operation != "CLEANUP" and now >= row.deadline)
    ):
        raise HTTPException(409, "demo_worker_fenced")
    if any(not re.fullmatch(r"[a-z_]+:[A-Za-z0-9_.:-]{1,300}", ref) for ref in output.object_refs):
        raise HTTPException(422, "demo_reference_invalid")
    step.output = output.model_dump(mode="json")
    step.finished_at = now
    step.status = "FAILED" if failed else "COMPLETED"
    row.lease_owner = row.lease_until = None
    row.version += 1
    row.updated_at = now
    if work.operation == "CLEANUP":
        row.cleanup_status = (
            "CLEAN"
            if not failed and output.cleanup_verified and output.residual_count == 0
            else "NEEDS_MANUAL"
        )
    elif failed:
        row.status, row.error_code = "NEEDS_RECONCILIATION", "FIXED_STEP_FAILED_NO_REDISPATCH"
    else:
        row.step_index += 1
        if output.model_source is not None:
            row.model_source = output.model_source
        if output.outcome != "UNKNOWN":
            row.actual_outcome = output.outcome
        row.status = (
            "CANCELLED" if row.cancel_requested else "COMPLETED" if row.step_index == len(STEPS) else "QUEUED"
        )
    audit(db, row, work.lease_owner, "DemoStepResultRecorded")
    db.flush()
    return row


def renew(db: Session, work: WorkItem) -> bool:
    """Bounded heartbeat: a dead or replaced worker cannot resurrect its lease."""
    row = db.scalar(select(DemoRunRow).where(DemoRunRow.run_id == work.run_id).with_for_update())
    step = db.get(DemoStepRow, (work.run_id, work.position))
    now = clock(db)
    if not row or not step or step.status != "STARTED" or step.generation != work.generation or (
        row.lease_owner != work.lease_owner or row.lease_until is None or row.lease_until <= now
    ):
        return False
    deadline = step.started_at + timedelta(seconds=MAX_STEP_SECONDS)
    if work.operation != "CLEANUP":
        deadline = min(deadline, row.deadline)
    if deadline <= now:
        return False
    row.lease_until = min(now + timedelta(seconds=LEASE_SECONDS), deadline)
    return True
