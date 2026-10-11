"""PostgreSQL scheduling, bounded read-only recovery and fenced worker identity."""

from datetime import datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.core.errors import ConflictError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.models import ActionAttemptRow, EnvironmentRow, TaskRow, WorkerLeaseRow
from zhiyu.db.response_authority import ActionControlRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.response_planning import TaskRuntimeRow
from zhiyu.response.authorization import current_lease, managed_policy
from zhiyu.response.capacity import available, workload
from zhiyu.response.catalog import INPUTS
from zhiyu.response.lab_protocol import CAPABILITY
from zhiyu.response.planner import emit
from zhiyu.response.registry import CapabilityRegistry
from zhiyu.response.task_graph import move, refresh_dependencies


class TaskScheduler:
    def __init__(self, db: Session) -> None:
        self.db = db

    def claim(
        self, environment_id: str, principal: ServicePrincipal, *, now: datetime | None = None
    ) -> dict[str, Any] | None:
        principal.require("response:execute", environment_id)
        start = perf_counter()
        db = self.db
        with db.begin():
            if (
                db.scalar(
                    select(EnvironmentRow)
                    .where(EnvironmentRow.environment_id == environment_id)
                    .with_for_update()
                )
                is None
            ):
                raise ReferenceError("environment missing")
            instant = now or db.scalar(select(func.clock_timestamp()))
            assert instant is not None
            _, policy = managed_policy(db, environment_id, instant)
            managed = list(
                db.scalars(
                    select(TaskRow)
                    .join(TaskRuntimeRow, TaskRuntimeRow.task_id == TaskRow.task_id)
                    .where(
                        TaskRow.environment_id == environment_id,
                        TaskRow.status.in_(["RUNNING", "FAILED", "TIMED_OUT"]),
                    )
                    .order_by(TaskRow.task_id)
                    .with_for_update(of=TaskRow)
                )
            )
            for task in managed:
                runtime = db.get(TaskRuntimeRow, task.task_id)
                assert runtime is not None
                if task.status == "RUNNING":
                    lease = db.get(WorkerLeaseRow, task.active_lease_id) if task.active_lease_id else None
                    if lease is not None and lease.expires_at > instant:
                        continue
                    if task.capability_id == CAPABILITY:
                        self.mark_interrupted(task, instant)
                        runtime.retry_allowed = False
                        continue
                    runtime.failure_code = "lease_expired"
                    runtime.retry_allowed = self.safe_retry(task)
                    move(
                        db,
                        task,
                        "timeout",
                        instant,
                        principal.principal_id,
                        "worker lease expired; execution outcome tracked separately",
                    )
                    runtime.ready_at = instant + timedelta(
                        seconds=policy.retry_backoff_seconds * 2 ** max(0, task.attempt_count - 1)
                    )
                    self.mark_interrupted(task, instant)
                if (
                    task.status in {"FAILED", "TIMED_OUT"}
                    and runtime.retry_allowed
                    and task.attempt_count < task.max_attempts
                    and runtime.ready_at <= instant
                ):
                    if not self.safe_retry(task):
                        runtime.retry_allowed = False
                        continue
                    task.active_lease_id, task.worker_id = None, None
                    action_state = db.scalar(
                        select(ActionControlRow).where(
                            ActionControlRow.task_id == task.task_id,
                            ActionControlRow.environment_id == environment_id,
                        )
                    )
                    if action_state and action_state.status in {"FAILED", "AUTHORIZED", "RECONCILING"}:
                        # A new ActionAttempt starts at PROPOSED; the prior immutable request/attempt history stays.
                        action_state.status, action_state.authorization_id = "PROPOSED", None
                    move(db, task, "retry", instant, principal.principal_id, "bounded read-only retry")
            refresh_dependencies(db, environment_id, instant, principal.principal_id)
            candidates = db.scalars(
                select(TaskRow)
                .join(TaskRuntimeRow, TaskRuntimeRow.task_id == TaskRow.task_id)
                .where(
                    TaskRow.environment_id == environment_id,
                    TaskRow.status == "QUEUED",
                    TaskRuntimeRow.ready_at <= instant,
                    TaskRow.attempt_count < TaskRow.max_attempts,
                )
                .order_by(TaskRow.priority, TaskRow.queued_at, TaskRow.task_id)
                .with_for_update(skip_locked=True, of=TaskRow)
            )
            for task in candidates:
                runtime = db.get(TaskRuntimeRow, task.task_id)
                assert runtime is not None
                kind = workload(runtime)
                if not available(db, environment_id, policy, principal, kind, instant):
                    if runtime.failure_code != "reserved_capacity_deferred":
                        runtime.failure_code = "reserved_capacity_deferred"
                        emit(
                            db,
                            environment_id,
                            "Task",
                            task.task_id + ":deferred",
                            "WorkloadDeferred",
                            "durable backlog; reserved class capacity or worker binding",
                            principal.principal_id,
                        )
                    continue
                if (
                    policy.reserved_capacity_enabled
                    and kind == "BACKGROUND"
                    and db.scalar(
                        select(TaskRow.task_id)
                        .join(TaskRuntimeRow, TaskRuntimeRow.task_id == TaskRow.task_id)
                        .where(
                            TaskRow.environment_id == environment_id,
                            TaskRow.capability_id == task.capability_id,
                            TaskRow.status == "QUEUED",
                            TaskRuntimeRow.task_type == "SECURITY_CRITICAL",
                        )
                        .limit(1)
                    )
                ):
                    runtime.failure_code = "reserved_capacity_deferred"
                    continue
                try:
                    definition, _ = CapabilityRegistry(db).resolve(
                        task.capability_id, task.capability_version
                    )
                except (ConflictError, ReferenceError):
                    runtime = db.get(TaskRuntimeRow, task.task_id)
                    assert runtime is not None
                    runtime.failure_code, runtime.retry_allowed = "capability_unavailable", False
                    move(
                        db,
                        task,
                        "cancel",
                        instant,
                        principal.principal_id,
                        "unknown or inactive managed capability",
                    )
                    refresh_dependencies(db, environment_id, instant, principal.principal_id)
                    continue
                if any(p not in principal.permissions for p in definition.required_permissions):
                    continue
                running_count = db.scalar(
                    select(func.count())
                    .select_from(TaskRow)
                    .join(WorkerLeaseRow, WorkerLeaseRow.lease_id == TaskRow.active_lease_id)
                    .where(
                        TaskRow.environment_id == environment_id,
                        TaskRow.capability_id == task.capability_id,
                        TaskRow.capability_version == task.capability_version,
                        TaskRow.status == "RUNNING",
                        WorkerLeaseRow.expires_at > instant,
                    )
                )
                if (running_count or 0) >= definition.max_concurrency:
                    continue
                # A QUEUED flag cannot bypass relational prerequisite checks.
                from zhiyu.db.response_planning import TaskEdgeRow

                dependencies = list(
                    db.scalars(
                        select(TaskRow)
                        .join(TaskEdgeRow, TaskEdgeRow.depends_on == TaskRow.task_id)
                        .where(
                            TaskEdgeRow.environment_id == environment_id, TaskEdgeRow.task_id == task.task_id
                        )
                    )
                )
                if any(t.status != "SUCCEEDED" for t in dependencies):
                    move(
                        db,
                        task,
                        "dependencies_pending",
                        instant,
                        principal.principal_id,
                        "prerequisite incomplete",
                    )
                    continue
                runtime = db.get(TaskRuntimeRow, task.task_id)
                assert runtime is not None
                runtime.generation += 1
                lease = WorkerLeaseRow(
                    lease_id="lease-" + uuid4().hex,
                    task_id=task.task_id,
                    worker_id=principal.principal_id,
                    generation=runtime.generation,
                    acquired_at=instant,
                    expires_at=instant + timedelta(seconds=policy.lease_seconds),
                    renewed_at=None,
                )
                db.add(lease)
                db.flush()
                task.active_lease_id, task.worker_id = lease.lease_id, lease.worker_id
                task.attempt_count += 1
                runtime.retry_allowed, runtime.failure_code = False, None
                move(
                    db, task, "claim", instant, principal.principal_id, "current PostgreSQL lease generation"
                )
                emit(
                    db,
                    environment_id,
                    "WorkerLease",
                    lease.lease_id,
                    "TaskLeased",
                    f"generation={lease.generation}",
                    principal.principal_id,
                )
                return {
                    "task_id": task.task_id,
                    "lease_id": lease.lease_id,
                    "generation": lease.generation,
                    "worker_id": lease.worker_id,
                    "expires_at": lease.expires_at.isoformat(),
                    "lease_ms": (perf_counter() - start) * 1000,
                }
            return None

    def safe_retry(self, task: TaskRow) -> bool:
        try:
            definition, config = CapabilityRegistry(self.db).resolve(
                task.capability_id, task.capability_version
            )
        except (ConflictError, ReferenceError):
            return False
        return (
            task.capability_id in INPUTS
            and definition.operation_kind in {"PASSIVE_READ", "ACTIVE_CHECK"}
            and config.retry_policy.get("kind") == "READ_ONLY_REPLAY"
        )

    def mark_interrupted(self, task: TaskRow, now: datetime) -> None:
        state = self.db.scalar(
            select(ActionControlRow).where(
                ActionControlRow.task_id == task.task_id,
                ActionControlRow.environment_id == task.environment_id,
            )
        )
        if state is None or state.status not in {"DISPATCHED", "EXECUTING"}:
            return
        pending = self.db.scalars(
            select(ActionAttemptRow)
            .join(ActionDispatchRow, ActionDispatchRow.attempt_id == ActionAttemptRow.attempt_id)
            .outerjoin(ActionResultRow, ActionResultRow.attempt_id == ActionAttemptRow.attempt_id)
            .where(ActionAttemptRow.action_id == state.action_id, ActionResultRow.attempt_id.is_(None))
        )
        for attempt in pending:
            attempt.status, attempt.reconciliation_state, attempt.error_code = (
                "EXECUTION_UNKNOWN",
                "PENDING",
                "lease_expired",
            )
        state.status = "RECONCILING"
        # Only these read-only adapters have no persistent state changes by construction.
        state.status = (
            "EXECUTION_UNKNOWN"
            if task.capability_id == CAPABILITY
            else "AUTHORIZED"
            if self.safe_retry(task)
            else "NEEDS_MANUAL"
        )
        emit(
            self.db,
            task.environment_id,
            "ActionRequest",
            f"{state.action_id}:recovery:{task.attempt_count}",
            "ActionRecovery",
            "previous read receipt unavailable; explicit READ_ONLY_REPLAY policy"
            if state.status == "AUTHORIZED"
            else "manual reconciliation required",
            "scheduler",
        )

    def renew(
        self,
        environment_id: str,
        task_id: str,
        generation: int,
        principal: ServicePrincipal,
        *,
        now: datetime | None = None,
    ) -> datetime:
        principal.require("response:execute", environment_id)
        with self.db.begin():
            self.db.scalar(
                select(EnvironmentRow)
                .where(EnvironmentRow.environment_id == environment_id)
                .with_for_update()
            )
            task = self.db.get(TaskRow, task_id)
            if task is None or task.environment_id != environment_id:
                raise ReferenceError("task missing")
            instant = now or self.db.scalar(select(func.clock_timestamp()))
            assert instant is not None
            _, policy = managed_policy(self.db, environment_id, instant)
            lease = current_lease(self.db, task, principal.principal_id, generation, instant)
            # Renewal never extends beyond this attempt's task timeout plus dispatch allowance.
            deadline = lease.acquired_at + timedelta(seconds=policy.lease_seconds)
            if instant >= deadline:
                raise ConflictError("attempt deadline exhausted")
            lease.renewed_at, lease.expires_at = instant, deadline
            return deadline

    def cancel(
        self,
        environment_id: str,
        task_id: str,
        expected_version: int,
        principal: ServicePrincipal,
        *,
        now: datetime | None = None,
    ) -> None:
        principal.require("response:admin", environment_id)
        with self.db.begin():
            self.db.scalar(
                select(EnvironmentRow)
                .where(EnvironmentRow.environment_id == environment_id)
                .with_for_update()
            )
            task = self.db.get(TaskRow, task_id)
            if task is None or task.environment_id != environment_id:
                raise ReferenceError("task missing")
            if task.row_version != expected_version or task.status not in {
                "QUEUED",
                "BLOCKED",
                "WAITING_APPROVAL",
            }:
                raise ConflictError("task cannot be cancelled at this version/state")
            instant = now or self.db.scalar(select(func.clock_timestamp()))
            assert instant is not None
            move(
                self.db,
                task,
                "rejected" if task.status == "WAITING_APPROVAL" else "cancel",
                instant,
                principal.principal_id,
                "authorized cancellation before dispatch",
            )
            refresh_dependencies(self.db, environment_id, instant, principal.principal_id)
