"""Single dispatch boundary for managed, freshly authorized, read-only capabilities."""

from datetime import datetime, timedelta
from time import perf_counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ConflictError, DomainError, LeaseLostError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import (
    ActionAttemptRow,
    ActionRow,
    AuthorizationContextRow,
    AuthorizationDecisionRow,
    EnvironmentRow,
    ScopeRow,
    TaskRow,
)
from zhiyu.db.response_authority import ActionControlRow, AuthorizationSnapshotRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.response_planning import TaskRuntimeRow
from zhiyu.domain.contracts import ActionRequest, action_digest
from zhiyu.response.authorization import AuthorizationService, current_lease, managed_policy
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.dispatch_guard import assert_current
from zhiyu.response.executors import ExecutorOutput, ExecutorRegistry
from zhiyu.response.lab_protocol import CAPABILITY
from zhiyu.response.planner import emit, identity
from zhiyu.response.registry import CapabilityRegistry
from zhiyu.response.task_graph import move, refresh_dependencies


def receipt(row: ActionResultRow, action_id: str, digest: str, *, duplicate: bool = False) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "action_digest": digest,
        "attempt_id": row.attempt_id,
        "disposition": "DUPLICATE" if duplicate else "RECORDED",
        "execution_outcome": row.execution_outcome,
        "executor": row.executor,
        "executor_version": row.executor_version,
        "started_at": row.started_at.isoformat(),
        "completed_at": row.completed_at.isoformat(),
        "executor_ms": row.executor_ms,
        "output": row.output,
        "error_code": row.error_code,
        "retryable": row.retryable,
        "side_effect": row.side_effect,
        "evidence_refs": [f"db://action_execution_results/{row.attempt_id}"],
        "semantics": "execution result only; security success not evaluated",
    }


class ActionGateway:
    def __init__(self, engine: Engine, executors: ExecutorRegistry | None = None) -> None:
        self.engine, self.executors = engine, executors or ExecutorRegistry(engine)

    def dispatch(
        self,
        environment_id: str,
        task_id: str,
        generation: int,
        authorization_id: str,
        principal: ServicePrincipal,
        *,
        submitted_digest: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        principal.require("response:execute", environment_id)
        stage_start = perf_counter()
        attempt_id = ""
        with Session(self.engine) as db, db.begin():
            db.scalar(
                select(EnvironmentRow)
                .where(EnvironmentRow.environment_id == environment_id)
                .with_for_update()
            )
            task = db.get(TaskRow, task_id)
            state = db.scalar(
                select(ActionControlRow).where(
                    ActionControlRow.environment_id == environment_id, ActionControlRow.task_id == task_id
                )
            )
            if task is None or task.environment_id != environment_id or state is None:
                raise ReferenceError("managed task action not found")
            row = db.get(ActionRow, state.action_id)
            decision = db.get(AuthorizationDecisionRow, authorization_id)
            if row is None or decision is None or decision.action_id != state.action_id:
                raise ReferenceError("authorization not bound to action")
            context = db.get(AuthorizationContextRow, decision.authorization_context_id)
            if context is None or context.principal_id != principal.principal_id:
                raise ConflictError("authorization principal mismatch")
            action = contract_from(row, ActionRequest)
            definition, _ = CapabilityRegistry(db).resolve(action.capability_id, action.capability_version)
            for permission in definition.required_permissions:
                principal.require(permission, environment_id)
            if action_digest(action) != row.action_digest or decision.action_digest != row.action_digest:
                raise ConflictError("stored action authorization digest mismatch")
            if submitted_digest is not None and submitted_digest != row.action_digest:
                emit(
                    db,
                    environment_id,
                    "ActionRequest",
                    state.action_id + ":mutation:" + identity("request", submitted_digest),
                    "ActionRejected",
                    "action_digest_mismatch",
                    principal.principal_id,
                )
                return {
                    "action_id": action.action_id,
                    "execution_outcome": "DENIED",
                    "error_code": "action_digest_mismatch",
                    "executor_called": False,
                }
            latest = db.scalar(
                select(ActionResultRow)
                .join(ActionDispatchRow, ActionDispatchRow.attempt_id == ActionResultRow.attempt_id)
                .where(ActionDispatchRow.action_id == action.action_id)
                .order_by(ActionResultRow.completed_at.desc(), ActionResultRow.attempt_id)
                .limit(1)
            )
            if state.status == "EXECUTED" and latest:
                return receipt(latest, action.action_id, row.action_digest, duplicate=True)
            instant = now or db.scalar(select(func.clock_timestamp()))
            assert instant is not None
            lease = current_lease(db, task, principal.principal_id, generation, instant)
            attempt_id = identity("attempt", [action.action_id, generation])
            previous_dispatch = db.get(ActionDispatchRow, attempt_id)
            if previous_dispatch:
                previous_result = db.get(ActionResultRow, attempt_id)
                return (
                    receipt(previous_result, action.action_id, row.action_digest, duplicate=True)
                    if previous_result
                    else {
                        "action_id": action.action_id,
                        "attempt_id": attempt_id,
                        "disposition": "IN_PROGRESS",
                        "executor_called": False,
                    }
                )
            denials = []
            if decision.outcome not in {"ALLOW", "REQUIRE_APPROVAL"}:
                denials.append("policy_not_allow")
            if decision.valid_until <= instant or context.created_at > instant:
                denials.append("stale_authorization")
            if state.authorization_id != authorization_id or state.status not in {
                "AUTHORIZED",
                "WAITING_APPROVAL",
            }:
                denials.append("authorization_or_action_state_changed")
            snapshot = db.get(AuthorizationSnapshotRow, decision.authorization_context_id)
            if (
                snapshot is None
                or snapshot.inputs["generation"] != generation
                or snapshot.inputs["lease_id"] != lease.lease_id
            ):
                denials.append("authorization_lease_binding_mismatch")
            control, policy = managed_policy(db, environment_id, instant)
            if (lease.expires_at - instant).total_seconds() < task.timeout_seconds + 1:
                denials.append("insufficient_lease_time")
            if (definition.operation_kind == "STATE_CHANGE" and action.capability_id != CAPABILITY) or int(
                definition.base_risk.value[1:]
            ) >= 3:
                denials.append("executor_risk_not_supported")
            if definition.operation_kind != "PASSIVE_READ" and control.next_probe_at > instant:
                denials.append("scope_rate_budget_exhausted")
            fresh = AuthorizationService(db).evaluate(
                action, task, generation, principal, instant, extra_denials=denials
            )
            if fresh.outcome == "REQUIRE_APPROVAL":
                # ai.5 has no RUNNING -> WAITING_APPROVAL edge. End this non-executed
                # attempt, requeue, then park it through the frozen transitions.
                runtime = db.get(TaskRuntimeRow, task_id)
                assert runtime is not None
                runtime.failure_code, runtime.retry_allowed = "approval_required", False
                for event in ("known_failure", "retry", "needs_approval"):
                    move(
                        db,
                        task,
                        event,
                        instant,
                        principal.principal_id,
                        "approval required; no executor called",
                    )
                task.active_lease_id, task.worker_id = None, None
                state.status, state.authorization_id = "WAITING_APPROVAL", fresh.authorization_id
                return {
                    "action_id": action.action_id,
                    "action_digest": row.action_digest,
                    "execution_outcome": "DENIED",
                    "error_code": "approval_required",
                    "executor_called": False,
                    "task_status": "WAITING_APPROVAL",
                }
            effective_outcome = "STALE" if "stale_authorization" in fresh.reasons else "DENIED"
            if fresh.outcome != "ALLOW":
                db.add(
                    ActionAttemptRow(
                        attempt_id=attempt_id,
                        action_id=action.action_id,
                        status="DENIED",
                        fencing_generation=generation,
                        worker_id=principal.principal_id,
                        started_at=instant,
                        finished_at=instant,
                        device_receipt_id=None,
                        reconciliation_state="NOT_NEEDED",
                        evidence_ids=[],
                        error_code=fresh.reasons[0],
                        error_class="AUTHORIZATION",
                        device_response_hash=None,
                    )
                )
                db.flush()
                db.add(
                    ActionDispatchRow(
                        attempt_id=attempt_id,
                        environment_id=environment_id,
                        action_id=action.action_id,
                        task_id=task_id,
                        lease_id=lease.lease_id,
                        generation=generation,
                        authorization_id=fresh.authorization_id,
                        gateway_ms=(perf_counter() - stage_start) * 1000,
                    )
                )
                db.flush()
                denial_output = {"reasons": fresh.reasons, "executor_called": False}
                result = ActionResultRow(
                    attempt_id=attempt_id,
                    execution_outcome=effective_outcome,
                    executor="NOT_DISPATCHED",
                    executor_version="none",
                    started_at=instant,
                    completed_at=instant,
                    executor_ms=0,
                    output=denial_output,
                    output_hash=canonical_hash(denial_output),
                    error_code=fresh.reasons[0],
                    retryable=False,
                    side_effect="NONE",
                )
                db.add(result)
                state.status = "EXPIRED" if effective_outcome == "STALE" else "DENIED"
                runtime = db.get(TaskRuntimeRow, task_id)
                assert runtime is not None
                runtime.failure_code, runtime.retry_allowed, runtime.result_ref = (
                    fresh.reasons[0],
                    False,
                    f"db://action_execution_results/{attempt_id}",
                )
                move(
                    db,
                    task,
                    "known_failure",
                    instant,
                    principal.principal_id,
                    "authorization failed; executor not called",
                )
                emit(
                    db,
                    environment_id,
                    "ActionAttempt",
                    attempt_id,
                    "ActionFailed",
                    "authorization rejected before dispatch",
                    principal.principal_id,
                )
                refresh_dependencies(db, environment_id, instant, principal.principal_id)
                return receipt(result, action.action_id, row.action_digest)
            try:
                executor = self.executors.resolve(action)
            except ValueError as error:
                raise ConflictError("executor is not registered") from error
            if definition.operation_kind != "PASSIVE_READ":
                scope = db.get(ScopeRow, (action.scope_id, environment_id))
                assert scope is not None
                control.next_probe_at = instant + timedelta(seconds=1 / scope.max_requests_per_second)
            from zhiyu.verification.lifecycle import dispatch_transition

            dispatch_transition(db, task, action, instant, principal.principal_id)
            state.status = "DISPATCHED"
            db.add(
                ActionAttemptRow(
                    attempt_id=attempt_id,
                    action_id=action.action_id,
                    status="EXECUTING",
                    fencing_generation=generation,
                    worker_id=principal.principal_id,
                    started_at=instant,
                    finished_at=None,
                    device_receipt_id=None,
                    reconciliation_state="NOT_NEEDED",
                    evidence_ids=[],
                    error_code=None,
                    error_class=None,
                    device_response_hash=None,
                )
            )
            db.flush()
            db.add(
                ActionDispatchRow(
                    attempt_id=attempt_id,
                    environment_id=environment_id,
                    action_id=action.action_id,
                    task_id=task_id,
                    lease_id=lease.lease_id,
                    generation=generation,
                    authorization_id=fresh.authorization_id,
                    gateway_ms=(perf_counter() - stage_start) * 1000,
                )
            )
            state.status = "EXECUTING"
            emit(
                db,
                environment_id,
                "ActionAttempt",
                attempt_id,
                "ActionStarted",
                "fresh authority and current fencing generation; registered bounded executor",
                principal.principal_id,
            )
        # Intent is durable before invoking the registered executor. No shell or URL dispatch exists.
        executor_ms = 0.0
        try:
            # A paused worker must recheck its live lease immediately before invoking the adapter.
            with Session(self.engine) as db, db.begin():
                db.scalar(
                    select(EnvironmentRow)
                    .where(EnvironmentRow.environment_id == environment_id)
                    .with_for_update()
                )
                task_row = db.get(TaskRow, task_id)
                assert task_row is not None
                dispatch_time = now or db.scalar(select(func.clock_timestamp()))
                assert dispatch_time is not None
                assert_current(
                    db,
                    action,
                    task_row,
                    fresh.authorization_id,
                    principal.principal_id,
                    generation,
                    dispatch_time,
                )
                execute_start = perf_counter()
                try:
                    output = executor.execute(action)
                finally:
                    executor_ms = (perf_counter() - execute_start) * 1000
            if output.side_effect != "NONE" and not (
                action.capability_id == CAPABILITY and output.side_effect == "LAB_PATH"
            ):
                output = ExecutorOutput("EXECUTION_FAILURE", {}, "invalid_executor_side_effect_declaration")
        except LeaseLostError:
            raise
        except DomainError:
            output = ExecutorOutput(
                "EXECUTION_FAILURE", {"executor_called": False}, "dispatch_authority_changed", False
            )
        except TimeoutError:
            if action.capability_id == CAPABILITY:
                return self.unknown(environment_id, attempt_id, principal, "lab_receipt_timeout")
            output = ExecutorOutput("TIMEOUT", {}, "executor_timeout", True)
        except Exception:
            if action.capability_id == CAPABILITY:
                return self.unknown(environment_id, attempt_id, principal, "lab_receipt_unconfirmed")
            # Failure is explicit and durable; no raw exception/credential/URL body leaks into result.
            output = ExecutorOutput("EXECUTION_FAILURE", {}, "executor_failure", True)
        completed = self.complete(
            environment_id,
            attempt_id,
            generation,
            principal,
            output,
            executor_name=action.capability_id,
            executor_version=executor.version,
            executor_ms=executor_ms,
            now=now,
        )
        completed["action_digest"] = action_digest(action)
        completed["gateway_overhead_ms"] = max(0.0, (perf_counter() - stage_start) * 1000 - executor_ms)
        return completed

    def unknown(self, env: str, attempt_id: str, principal: ServicePrincipal, reason: str) -> dict[str, Any]:
        """No execution verdict when a mutating request may have reached its target."""
        principal.require("response:execute", env)
        with Session(self.engine) as db, db.begin():
            db.scalar(select(EnvironmentRow).where(EnvironmentRow.environment_id == env).with_for_update())
            dispatch = db.get(ActionDispatchRow, attempt_id)
            if not dispatch or dispatch.environment_id != env:
                raise ReferenceError("attempt not found")
            attempt = db.get(ActionAttemptRow, attempt_id)
            state = db.get(ActionControlRow, dispatch.action_id)
            runtime = db.get(TaskRuntimeRow, dispatch.task_id)
            assert attempt and state and runtime
            if not db.get(ActionResultRow, attempt_id):
                attempt.status, attempt.reconciliation_state = "EXECUTION_UNKNOWN", "PENDING"
                attempt.error_code = reason
                state.status = "EXECUTION_UNKNOWN"
                runtime.retry_allowed, runtime.failure_code = False, reason
                emit(
                    db,
                    env,
                    "ActionAttempt",
                    attempt_id + ":unknown",
                    "ActionRecovery",
                    "UNKNOWN; read reconciliation required; mutation replay forbidden",
                    principal.principal_id,
                )
            return {
                "attempt_id": attempt_id,
                "execution_outcome": "EXECUTION_UNKNOWN",
                "executor_called": True,
            }

    def reconcile(
        self, env: str, attempt_id: str, principal: ServicePrincipal, *, now: datetime | None = None
    ) -> dict[str, Any]:
        from zhiyu.response.lab_reconcile import reconcile

        return reconcile(self.engine, env, attempt_id, principal, now=now)

    def complete(
        self,
        environment_id: str,
        attempt_id: str,
        generation: int,
        principal: ServicePrincipal,
        output: ExecutorOutput,
        *,
        executor_name: str,
        executor_version: str,
        executor_ms: float,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        principal.require("response:execute", environment_id)
        with Session(self.engine) as db, db.begin():
            db.scalar(
                select(EnvironmentRow)
                .where(EnvironmentRow.environment_id == environment_id)
                .with_for_update()
            )
            dispatch = db.get(ActionDispatchRow, attempt_id)
            if (
                dispatch is None
                or dispatch.environment_id != environment_id
                or dispatch.generation != generation
            ):
                raise LeaseLostError("attempt identity or generation mismatch")
            task = db.get(TaskRow, dispatch.task_id)
            assert task is not None
            instant = now or db.scalar(select(func.clock_timestamp()))
            assert instant is not None
            current_lease(db, task, principal.principal_id, generation, instant)
            if db.get(ActionResultRow, attempt_id):
                raise ConflictError("attempt already acknowledged")
            attempt = db.get(ActionAttemptRow, attempt_id)
            state = db.get(ActionControlRow, dispatch.action_id)
            runtime = db.get(TaskRuntimeRow, task.task_id)
            assert attempt is not None and state is not None and runtime is not None
            if (
                attempt.worker_id != principal.principal_id
                or attempt.status != "EXECUTING"
                or state.status != "EXECUTING"
            ):
                raise LeaseLostError("attempt is no longer executing")
            dispatch_decision = db.get(AuthorizationDecisionRow, dispatch.authorization_id)
            assert dispatch_decision is not None
            dispatch_snapshot = db.get(AuthorizationSnapshotRow, dispatch_decision.authorization_context_id)
            assert dispatch_snapshot is not None
            # Revocation prevents new dispatch, but cannot erase an already obtained execution receipt.
            policy = ResponsePolicy.model_validate(dispatch_snapshot.inputs["policy"])
            digest = canonical_hash(output.output)
            result = ActionResultRow(
                attempt_id=attempt_id,
                execution_outcome=output.execution_outcome,
                executor=executor_name,
                executor_version=executor_version,
                started_at=attempt.started_at,
                completed_at=instant,
                executor_ms=executor_ms,
                output=output.output,
                output_hash=digest,
                error_code=output.error_code,
                retryable=output.retryable,
                side_effect=output.side_effect,
            )
            db.add(result)
            success = output.execution_outcome == "EXECUTION_SUCCESS"
            attempt.status = "EXECUTED" if success else "FAILED"
            attempt.finished_at, attempt.device_response_hash = instant, digest
            attempt.device_receipt_id = f"db://action_execution_results/{attempt_id}"
            attempt.error_code, attempt.error_class = (
                output.error_code,
                None if success else output.execution_outcome,
            )
            state.status = attempt.status
            runtime.result_ref = attempt.device_receipt_id
            runtime.failure_code, runtime.retry_allowed = output.error_code, output.retryable and not success
            runtime.ready_at = instant + timedelta(
                seconds=policy.retry_backoff_seconds * 2 ** max(0, task.attempt_count - 1)
            )
            move(
                db,
                task,
                "output_valid"
                if success
                else "timeout"
                if output.execution_outcome == "TIMEOUT"
                else "known_failure",
                instant,
                principal.principal_id,
                "executor output valid; no security verdict"
                if success
                else output.error_code or "executor failed",
            )
            emit(
                db,
                environment_id,
                "ActionAttempt",
                attempt_id,
                "ActionSucceeded" if success else "ActionFailed",
                "execution receipt only" if success else output.error_code or "executor failed",
                principal.principal_id,
            )
            refresh_dependencies(db, environment_id, instant, principal.principal_id)
            db.flush()
            action_row = db.get(ActionRow, dispatch.action_id)
            assert action_row is not None
            return receipt(result, dispatch.action_id, action_row.action_digest)
