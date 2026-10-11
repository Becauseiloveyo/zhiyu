"""Task state operations; all callers must own the environment/task transaction locks."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.core.errors import ConflictError
from zhiyu.db.models import TaskRow
from zhiyu.db.response_planning import TaskEdgeRow, TaskRuntimeRow
from zhiyu.response.planner import emit

TRANSITIONS = {
    ("QUEUED", "dependencies_pending"): "BLOCKED",
    ("BLOCKED", "dependencies_ready"): "QUEUED",
    ("QUEUED", "needs_approval"): "WAITING_APPROVAL",
    ("WAITING_APPROVAL", "approved"): "QUEUED",
    ("WAITING_APPROVAL", "rejected"): "CANCELLED",
    ("QUEUED", "claim"): "RUNNING",
    ("RUNNING", "output_valid"): "SUCCEEDED",
    ("RUNNING", "known_failure"): "FAILED",
    ("RUNNING", "timeout"): "TIMED_OUT",
    ("TIMED_OUT", "retry"): "QUEUED",
    ("FAILED", "retry"): "QUEUED",
    ("QUEUED", "cancel"): "CANCELLED",
    ("BLOCKED", "cancel"): "CANCELLED",
    ("RUNNING", "cancel_confirmed"): "CANCELLED",
}


def next_status(status: str, event: str) -> str:
    try:
        return TRANSITIONS[status, event]
    except KeyError as error:
        raise ConflictError("illegal task transition") from error


def move(db: Session, task: TaskRow, event: str, now: datetime, actor: str, reason: str) -> None:
    task.status = next_status(task.status, event)
    if task.status in {"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED"}:
        task.finished_at = now
    if task.status == "QUEUED":
        task.queued_at, task.finished_at = now, None
    if task.status == "RUNNING":
        task.claimed_at, task.started_at = now, now
    db.flush()
    event_name = {
        "RUNNING": "TaskStarted",
        "SUCCEEDED": "TaskSucceeded",
        "FAILED": "TaskFailed",
        "TIMED_OUT": "TaskFailed",
    }.get(task.status, "TaskStateChanged")
    emit(db, task.environment_id, "Task", f"{task.task_id}:v{task.row_version}", event_name, reason, actor)


def refresh_dependencies(db: Session, environment_id: str, now: datetime, actor: str) -> int:
    changed = 0
    tasks = list(
        db.scalars(
            select(TaskRow)
            .join(TaskRuntimeRow, TaskRuntimeRow.task_id == TaskRow.task_id)
            .where(TaskRow.environment_id == environment_id, TaskRow.status == "BLOCKED")
            .order_by(TaskRow.task_id)
        )
    )
    # Iterate to propagate a terminal failed dependency through the whole DAG.
    for _ in range(len(tasks) + 1):
        progress = False
        for task in tasks:
            if task.status != "BLOCKED":
                continue
            deps = list(
                db.scalars(
                    select(TaskRow)
                    .join(TaskEdgeRow, TaskEdgeRow.depends_on == TaskRow.task_id)
                    .where(TaskEdgeRow.environment_id == environment_id, TaskEdgeRow.task_id == task.task_id)
                )
            )
            dependency_runtime = {d.task_id: db.get(TaskRuntimeRow, d.task_id) for d in deps}
            terminal_failure = any(
                d.status == "CANCELLED"
                or (
                    d.status in {"FAILED", "TIMED_OUT"}
                    and (
                        d.attempt_count >= d.max_attempts
                        or not (
                            (dep_runtime := dependency_runtime[d.task_id]) is not None
                            and dep_runtime.retry_allowed
                        )
                    )
                )
                for d in deps
            )
            if terminal_failure:
                runtime = db.get(TaskRuntimeRow, task.task_id)
                assert runtime is not None
                runtime.failure_code = "dependency_failed"
                move(db, task, "cancel", now, actor, "terminal prerequisite failure")
            elif deps and all(d.status == "SUCCEEDED" for d in deps):
                move(db, task, "dependencies_ready", now, actor, "all prerequisites succeeded")
            else:
                continue
            changed += 1
            progress = True
        if not progress:
            break
    return changed
