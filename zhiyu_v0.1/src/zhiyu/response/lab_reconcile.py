"""Read-only recovery through the existing gateway, attempt, lease, audit and receipt rows."""

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ConflictError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import (
    ActionAttemptRow,
    ActionRow,
    EnvironmentRow,
    ResourceRow,
    ScopeRow,
    TaskRow,
    WorkerLeaseRow,
)
from zhiyu.db.response_authority import ActionControlRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.response_planning import TaskRuntimeRow
from zhiyu.domain.contracts import ActionRequest, ResourceRef, action_digest
from zhiyu.response.authorization import managed_policy
from zhiyu.response.lab_client import LabClient
from zhiyu.response.lab_protocol import CAPABILITY, LabInput
from zhiyu.response.planner import emit
from zhiyu.response.task_graph import move, refresh_dependencies


def compare(action: ActionRequest, observed: dict[str, Any]) -> tuple[str, str]:
    """Never infer success merely from the desired bit; bind target, intent and receipt."""
    p = LabInput.model_validate(action.parameters)
    state, prior = observed["state"], observed["receipt"]
    if state["digest"] != canonical_hash({k: v for k, v in state.items() if k != "digest"}):
        raise ValueError("state_digest_mismatch")
    if (state["environment_id"], state["resource_id"], state["epoch"]) != (
        action.environment_id,
        action.target.resource_id,
        p.epoch,
    ):
        return "UNKNOWN", "target_epoch_or_identity_changed"
    if prior is None:
        # A POST may still be in flight. Only the target's own expired command
        # window makes absence terminal; until then a read cannot fence arrival.
        if datetime.fromisoformat(observed["observed_at"]) <= action.expires_at:
            return "UNKNOWN", "inflight_command_window_not_closed"
        return (
            ("CONFIRMED_NOT_APPLIED", "unchanged_target_no_receipt")
            if (state["generation"] == p.expected_generation and state["digest"] == p.before_digest)
            else ("UNKNOWN", "unattributed_target_change")
        )
    if (
        prior["action_id"] != action.action_id
        or prior["action_digest"] != action_digest(action)
        or prior["command_hash"] != canonical_hash(LabClient(action).command().model_dump(mode="json"))
        or prior["before"]["digest"] != p.before_digest
        or prior["after"]["generation"] != p.expected_generation + 1
        or prior["after"]["epoch"] != p.epoch
        or prior["after"]["restricted"] != (p.operation == "contain")
        or prior["after"]["owner"] != (action.ownership_tag if p.operation == "contain" else None)
    ):
        raise ValueError("receipt_intent_mismatch")
    if state["digest"] == prior["after"]["digest"]:
        return "CONFIRMED_APPLIED", "current_state_matches_intent_owner_generation"
    return "CONFIRMED_APPLIED", "applied_then_expired_or_superseded"


def reconcile(
    engine: Engine, env: str, attempt_id: str, principal: ServicePrincipal, *, now: datetime | None = None
) -> dict[str, Any]:
    principal.require("response:reconcile", env)
    principal.require("capability:" + CAPABILITY, env)
    with Session(engine) as db, db.begin():
        environment = db.scalar(
            select(EnvironmentRow).where(EnvironmentRow.environment_id == env).with_for_update()
        )
        dispatch = db.get(ActionDispatchRow, attempt_id)
        if not dispatch or dispatch.environment_id != env or not environment:
            raise ReferenceError("recovery attempt missing")
        from zhiyu.response.gateway import receipt

        action_row = db.get(ActionRow, dispatch.action_id)
        assert action_row is not None
        action = contract_from(action_row, ActionRequest)
        if action.capability_id != CAPABILITY:
            raise ConflictError("adapter has no Lab reconciliation")
        existing = db.get(ActionResultRow, attempt_id)
        if existing:
            return receipt(existing, action.action_id, action_row.action_digest, duplicate=True)
        ts = now or db.scalar(select(func.clock_timestamp()))
        assert ts is not None
        state = db.get(ActionControlRow, action.action_id)
        attempt = db.get(ActionAttemptRow, attempt_id)
        task = db.get(TaskRow, dispatch.task_id)
        runtime = db.get(TaskRuntimeRow, dispatch.task_id)
        assert state and attempt and task and runtime
        lease = db.get(WorkerLeaseRow, task.active_lease_id) if task.active_lease_id else None
        if state.status in {"EXECUTING", "DISPATCHED"} and lease and lease.expires_at <= ts:
            attempt.status, attempt.reconciliation_state = "EXECUTION_UNKNOWN", "PENDING"
            state.status = "EXECUTION_UNKNOWN"
            emit(
                db,
                env,
                "ActionAttempt",
                attempt_id + ":unknown",
                "ActionRecovery",
                "expired lease with lost receipt: UNKNOWN; no mutation replay",
                principal.principal_id,
            )
        if state.status not in {"EXECUTION_UNKNOWN", "NEEDS_MANUAL"} or task.status != "RUNNING":
            raise ConflictError("live or resolved action cannot be reconciled")
        scope = db.get(ScopeRow, (action.scope_id, env))
        target = db.get(ResourceRow, (action.target.resource_id, env))
        _, policy = managed_policy(db, env, ts)
        from zhiyu.response.capacity import available

        if not available(db, env, policy, principal, "RECOVERY", ts):
            return {
                "attempt_id": attempt_id,
                "execution_outcome": "EXECUTION_UNKNOWN",
                "reason": "reserved_recovery_capacity_deferred",
                "mutation_replayed": False,
            }
        source_id = policy.worker_sources.get(principal.principal_id)
        source = db.get(ResourceRow, (source_id, env)) if source_id else None
        if (
            environment.deployment_stage != "LAB"
            or environment.asset_domain != "IT"
            or not scope
            or not scope.valid_from <= ts < scope.valid_until
            or not target
            or contract_from(target, ResourceRef) != action.target
            or not source
            or not action.source
            or source.resource_id != action.source.resource_id
            or contract_from(source, ResourceRef) != action.source
            or CAPABILITY not in scope.allowed_capabilities
            or CAPABILITY not in environment.capability_allowlist
            or source.resource_id not in scope.capability_source_ids.get(CAPABILITY, [])
            or target.resource_id not in scope.target_resource_ids
            or not any(
                source.resource_id in n["source_resource_ids"]
                and target.resource_id in n["target_resource_ids"]
                and target.locator.get("port") in n["destination_ports"]
                and target.locator.get("protocol") in n["protocols"]
                for n in scope.network_constraints
            )
        ):
            raise ConflictError("reconciliation read outside current Lab scope")
        # The environment lock serializes readers; a new lease generation fences the old worker.
        runtime.generation += 1
        runtime.task_type = "RECOVERY"
        recovery = WorkerLeaseRow(
            lease_id="lease-" + uuid4().hex,
            task_id=task.task_id,
            worker_id=principal.principal_id,
            generation=runtime.generation,
            acquired_at=ts,
            expires_at=ts + timedelta(seconds=policy.lease_seconds),
            renewed_at=None,
        )
        db.add(recovery)
        db.flush()
        task.active_lease_id, task.worker_id = recovery.lease_id, principal.principal_id
        state.status = "RECONCILING"
        runtime.retry_allowed = False
        try:
            observed = LabClient(action).request("GET")
            disposition, reason = compare(action, observed)
        except (OSError, ValueError, KeyError, TypeError):
            observed, disposition, reason = {}, "UNKNOWN", "target_read_unavailable_or_invalid"
        attempt.reconciliation_state = disposition
        emit(
            db,
            env,
            "ActionAttempt",
            f"{attempt_id}:reconcile:{runtime.generation}",
            "ActionRecovery",
            disposition + ":" + reason,
            principal.principal_id,
        )
        if disposition == "UNKNOWN":
            state.status, runtime.failure_code = "NEEDS_MANUAL", reason
            return {
                "attempt_id": attempt_id,
                "execution_outcome": "EXECUTION_UNKNOWN",
                "reason": reason,
                "mutation_replayed": False,
            }
        success = disposition == "CONFIRMED_APPLIED"
        output = {
            "reconciliation": disposition,
            "reason": reason,
            "observed": observed,
            "mutation_replayed": False,
        }
        result = ActionResultRow(
            attempt_id=attempt_id,
            execution_outcome="EXECUTION_SUCCESS" if success else "EXECUTION_FAILURE",
            executor="lab-read-reconcile",
            executor_version="1.0.0",
            started_at=attempt.started_at,
            completed_at=ts,
            executor_ms=0,
            output=output,
            output_hash=canonical_hash(output),
            error_code=None if success else reason,
            retryable=False,
            side_effect="LAB_PATH" if success else "NONE",
        )
        db.add(result)
        state.status = "EXECUTED" if success else "FAILED"
        attempt.finished_at, attempt.device_response_hash = ts, result.output_hash
        attempt.device_receipt_id = f"db://action_execution_results/{attempt_id}"
        runtime.result_ref, runtime.failure_code = attempt.device_receipt_id, result.error_code
        move(
            db,
            task,
            "output_valid" if success else "known_failure",
            ts,
            principal.principal_id,
            "reconciled target receipt; current state retained separately; no security verdict",
        )
        refresh_dependencies(db, env, ts, principal.principal_id)
        db.flush()
        return receipt(result, action.action_id, action_row.action_digest)
