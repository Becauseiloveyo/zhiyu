"""Opt-in cycle admission; unchanged exact-version fencing at the action boundary."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ConflictError
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import IncidentRow, PlanRow, TaskRow
from zhiyu.db.response_planning import TaskRuntimeRow
from zhiyu.db.verification_replan import ResponseCycleRow
from zhiyu.domain.contracts import ActionRequest, SecurityIncident
from zhiyu.response.planner import emit


def semantic_hash(incident: IncidentRow) -> str:
    return canonical_hash(
        {
            k: getattr(incident, k)
            for k in (
                "incident_id",
                "environment_id",
                "title",
                "priority",
                "affected_asset_ids",
                "related_event_ids",
                "event_group_ids",
                "evidence_ids",
                "open_action_ids",
                "closure_type",
                "closure_evidence_ids",
            )
        }
    )


def move(db: Session, incident: IncidentRow, target: str, now: datetime, actor: str, reason: str) -> None:
    if (incident.status, target) not in {
        ("TRIAGED", "INVESTIGATING"),
        ("INVESTIGATING", "PLANNED"),
        ("PLANNED", "EXECUTING"),
        ("EXECUTING", "VERIFYING"),
        ("VERIFYING", "INVESTIGATING"),
        ("VERIFYING", "HUMAN_REVIEW"),
    }:
        raise ConflictError("illegal continuous-verification incident transition")
    old = incident.status
    incident.status, incident.updated_at = target, now
    incident.state_version += 1
    if target == "INVESTIGATING" and incident.investigation_started_at is None:
        incident.investigation_started_at = now
    contract_from(incident, SecurityIncident)
    emit(
        db,
        incident.environment_id,
        "SecurityIncident",
        f"{incident.incident_id}:v{incident.state_version}",
        "IncidentUpdated",
        f"{old}->{target}; {reason}",
        actor,
    )


def cycle_for_task(db: Session, task: TaskRow) -> ResponseCycleRow | None:
    runtime = db.get(TaskRuntimeRow, task.task_id)
    return db.get(ResponseCycleRow, runtime.plan_id) if runtime else None


def execution_version(db: Session, task: TaskRow, fallback: int) -> int:
    cycle = cycle_for_task(db, task)
    if not cycle:
        return fallback
    incident = db.get(IncidentRow, task.incident_id)
    assert incident is not None
    return cycle.expected_version + (1 if incident.status == "PLANNED" else 0)


def admits(db: Session, task: TaskRow, action: ActionRequest, incident: IncidentRow) -> bool:
    cycle = cycle_for_task(db, task)
    if not cycle:
        return incident.state_version == action.expected_state_version and incident.status in {
            "TRIAGED",
            "INVESTIGATING",
        }
    return (
        cycle.environment_id == action.environment_id
        and cycle.incident_id == incident.incident_id
        and incident.state_version == cycle.expected_version
        and semantic_hash(incident) == cycle.semantic_hash
        and incident.status in {"PLANNED", "EXECUTING"}
        and action.expected_state_version == execution_version(db, task, 0)
    )


def dispatch_transition(db: Session, task: TaskRow, action: ActionRequest, now: datetime, actor: str) -> None:
    cycle = cycle_for_task(db, task)
    if not cycle:
        return
    incident = db.get(IncidentRow, task.incident_id)
    assert incident is not None
    if not admits(db, task, action, incident):
        raise ConflictError("response cycle changed before dispatch")
    if incident.status == "PLANNED":
        move(db, incident, "EXECUTING", now, actor, "fresh ALLOW and durable Action intent; no effect claim")
        cycle.expected_version = incident.state_version


def ready_for_verification(db: Session, cycle: ResponseCycleRow, now: datetime, actor: str) -> None:
    incident = db.get(IncidentRow, cycle.incident_id)
    plan = db.get(PlanRow, cycle.plan_id)
    assert incident is not None and plan is not None
    if incident.status == "VERIFYING" and incident.state_version == cycle.expected_version:
        return
    tasks = list(db.scalars(select(TaskRow).where(TaskRow.task_id.in_([t["task_id"] for t in plan.tasks]))))
    if len(tasks) != len(plan.tasks) or any(
        t.status not in {"SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT"} for t in tasks
    ):
        raise ConflictError("plan execution is not resolved")
    from zhiyu.db.response_authority import ActionControlRow

    if db.scalar(
        select(ActionControlRow.action_id).where(
            ActionControlRow.task_id.in_([t.task_id for t in tasks]),
            ActionControlRow.status.in_(["EXECUTION_UNKNOWN", "EXECUTING", "DISPATCHED"]),
        )
    ):
        raise ConflictError("unresolved action requires reconciliation")
    if incident.state_version != cycle.expected_version or semantic_hash(incident) != cycle.semantic_hash:
        raise ConflictError("incident changed during execution")
    move(db, incident, "VERIFYING", now, actor, "all plan tasks resolved; independent checks required")
    cycle.expected_version = incident.state_version
