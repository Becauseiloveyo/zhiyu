"""Admission reservations use existing runtime metadata and DB leases, not a second queue."""

from collections import Counter
from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.core.errors import AccessDenied, ConflictError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.models import EnvironmentRow, TaskRow, WorkerLeaseRow
from zhiyu.db.response_planning import TaskRuntimeRow
from zhiyu.db.verification_runtime import VerificationCheckRow
from zhiyu.response.config import ResponsePolicy, WorkloadClass
from zhiyu.response.planner import emit


def workload(runtime: TaskRuntimeRow) -> WorkloadClass:
    return (
        cast(WorkloadClass, runtime.task_type)
        if runtime.task_type in {"SECURITY_CRITICAL", "RECOVERY"}
        else "BACKGROUND"
    )


def active(db: Session, env: str, now: datetime) -> Counter[str]:
    counts: Counter[str] = Counter()
    for runtime in db.scalars(
        select(TaskRuntimeRow)
        .join(TaskRow, TaskRow.task_id == TaskRuntimeRow.task_id)
        .join(WorkerLeaseRow, WorkerLeaseRow.lease_id == TaskRow.active_lease_id)
        .where(TaskRow.environment_id == env, TaskRow.status == "RUNNING", WorkerLeaseRow.expires_at > now)
    ):
        counts[workload(runtime)] += 1
    counts["RECOVERY"] += (
        db.scalar(
            select(func.count())
            .select_from(VerificationCheckRow)
            .where(
                VerificationCheckRow.environment_id == env,
                VerificationCheckRow.status == "RUNNING",
                VerificationCheckRow.lease_until > now,
            )
        )
        or 0
    )
    return counts


def available(
    db: Session,
    env: str,
    policy: ResponsePolicy,
    principal: ServicePrincipal,
    kind: WorkloadClass,
    now: datetime,
) -> bool:
    if not policy.reserved_capacity_enabled:
        return True
    return (
        policy.worker_classes.get(principal.principal_id) == kind
        and active(db, env, now)[kind] < policy.class_capacity[kind]
    )


def classify(db: Session, env: str, task_id: str, kind: WorkloadClass, principal: ServicePrincipal) -> None:
    principal.require("response:admin", env)
    if kind not in {"BACKGROUND", "SECURITY_CRITICAL", "RECOVERY"}:
        raise AccessDenied("unknown workload class")
    with db.begin():
        db.scalar(select(EnvironmentRow).where(EnvironmentRow.environment_id == env).with_for_update())
        task, runtime = db.get(TaskRow, task_id), db.get(TaskRuntimeRow, task_id)
        if not task or task.environment_id != env or not runtime or task.status not in {"QUEUED", "BLOCKED"}:
            raise ConflictError("only queued managed work can be classified")
        runtime.task_type = kind
        emit(db, env, "Task", task_id + ":class:" + kind, "WorkloadClassified", kind, principal.principal_id)


def snapshot(db: Session, env: str) -> dict[str, Any]:
    classes: dict[str, dict[str, int]] = {
        k: {
            "queue_depth": 0,
            "admitted": 0,
            "deferred": 0,
            "running": 0,
            "completed": 0,
            "cancelled": 0,
            "dropped": 0,
        }
        for k in ("BACKGROUND", "SECURITY_CRITICAL", "RECOVERY")
    }
    for task, runtime in db.execute(
        select(TaskRow, TaskRuntimeRow)
        .join(TaskRuntimeRow, TaskRow.task_id == TaskRuntimeRow.task_id)
        .where(TaskRow.environment_id == env)
    ):
        stats = classes[workload(runtime)]
        stats["admitted"] += task.attempt_count
        stats["queue_depth"] += task.status in {"QUEUED", "BLOCKED", "WAITING_APPROVAL"}
        stats["deferred"] += runtime.failure_code == "reserved_capacity_deferred"
        stats["running"] += task.status == "RUNNING"
        stats["completed"] += task.status in {"SUCCEEDED", "FAILED", "TIMED_OUT"}
        stats["cancelled"] += task.status == "CANCELLED"
    for job in db.scalars(select(VerificationCheckRow).where(VerificationCheckRow.environment_id == env)):
        stats = classes["RECOVERY"]
        stats["queue_depth"] += job.status == "PENDING"
        stats["admitted"] += job.generation
        stats["running"] += job.status == "RUNNING"
        stats["completed"] += job.status in {"SUCCEEDED", "FAILED", "TIMEOUT", "INCONCLUSIVE"}
        stats["cancelled"] += job.status == "CANCELLED"
    return {
        "classes": classes,
        "queue_depth": sum(s["queue_depth"] for s in classes.values()),
        "dropped": 0,
        "loss_semantics": "durable rows; explicit cancellation and deferral; no queue eviction",
    }
