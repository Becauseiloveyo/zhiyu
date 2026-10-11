"""Persist intent and fresh authorization before dispatch. Does not execute capabilities."""

from datetime import datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.core.errors import AccessDenied, LeaseLostError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import (
    ActionRow,
    AuthorizationContextRow,
    AuthorizationDecisionRow,
    CapabilityHealthRow,
    EnvironmentRow,
    EvidenceRow,
    IncidentRow,
    PlanRow,
    ResourceRow,
    ScopeRow,
    SensorHealthRow,
    TaskRow,
    WorkerLeaseRow,
)
from zhiyu.db.response_authority import (
    ActionControlRow,
    AuthorizationSnapshotRow,
    ResponseBudgetRow,
    ResponseControlRow,
)
from zhiyu.db.response_planning import ResponsePlanRow, TaskRuntimeRow
from zhiyu.domain.contracts import (
    ActionRequest,
    AuthorizationContext,
    AuthorizationDecision,
    CapabilityHealth,
    EnvironmentProfile,
    ResourceRef,
    ScopeDefinition,
    SensorHealth,
    Task,
    action_digest,
)
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.lab_protocol import CAPABILITY, LabInput
from zhiyu.response.planner import emit, identity
from zhiyu.response.policy import RiskPolicyGate, ScopeEvaluator
from zhiyu.response.registry import CapabilityRegistry
from zhiyu.services.incident_engine import incident_events, raw_for_events
from zhiyu.verification.lifecycle import admits, execution_version


def current_lease(
    db: Session, task: TaskRow, worker_id: str, generation: int, now: datetime
) -> WorkerLeaseRow:
    runtime = db.get(TaskRuntimeRow, task.task_id)
    lease = db.get(WorkerLeaseRow, task.active_lease_id) if task.active_lease_id else None
    if (
        task.status != "RUNNING"
        or task.worker_id != worker_id
        or runtime is None
        or lease is None
        or lease.worker_id != worker_id
        or lease.task_id != task.task_id
        or lease.generation != generation
        or runtime.generation != generation
        or lease.expires_at <= now
    ):
        raise LeaseLostError("stale worker lease")
    return lease


def managed_policy(
    db: Session, environment_id: str, now: datetime
) -> tuple[ResponseControlRow, ResponsePolicy]:
    row = db.get(ResponseControlRow, environment_id)
    if row is None or not row.enabled or not row.valid_from <= now < row.valid_until:
        raise AccessDenied("response control disabled or expired")
    return row, ResponsePolicy.model_validate(row.configuration)


class AuthorizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def authorize_task(
        self,
        environment_id: str,
        task_id: str,
        *,
        generation: int,
        principal: ServicePrincipal,
        now: datetime | None = None,
    ) -> AuthorizationDecision:
        principal.require("response:execute", environment_id)
        with self.db.begin():
            self.db.scalar(
                select(EnvironmentRow)
                .where(EnvironmentRow.environment_id == environment_id)
                .with_for_update()
            )
            task = self.db.scalar(
                select(TaskRow)
                .where(TaskRow.task_id == task_id, TaskRow.environment_id == environment_id)
                .with_for_update()
            )
            if task is None:
                raise ReferenceError("task missing in environment")
            instant = now or self.db.scalar(select(func.clock_timestamp()))
            assert instant is not None
            current_lease(self.db, task, principal.principal_id, generation, instant)
            action = self.prepare(task, principal, instant)
            return self.evaluate(action, task, generation, principal, instant)

    def prepare(self, task: TaskRow, principal: ServicePrincipal, now: datetime) -> ActionRequest:
        """Caller owns transaction and locks. Only persisted managed Task can create intent."""
        db, env_id = self.db, task.environment_id
        runtime = db.get(TaskRuntimeRow, task.task_id)
        if runtime is None:
            raise ReferenceError("task is not in a managed plan")
        definition, _ = CapabilityRegistry(db).resolve(task.capability_id, task.capability_version)
        for permission in definition.required_permissions:
            principal.require(permission, env_id)
        control, policy = managed_policy(db, env_id, now)
        existing = db.scalar(
            select(ActionControlRow).where(
                ActionControlRow.environment_id == env_id, ActionControlRow.task_id == task.task_id
            )
        )
        if existing:
            row = db.get(ActionRow, existing.action_id)
            assert row is not None
            return contract_from(row, ActionRequest)
        plan = db.get(ResponsePlanRow, runtime.plan_id)
        env = db.get(EnvironmentRow, env_id)
        scope = db.get(ScopeRow, (task.scope_id, env_id))
        target = (
            db.get(ResourceRow, (task.target_resource_ids[0], env_id))
            if len(task.target_resource_ids) == 1
            else None
        )
        if plan is None or env is None or scope is None or target is None:
            raise ReferenceError("missing action identity or single scoped target")
        source_id = policy.worker_sources.get(principal.principal_id)
        source_row = db.get(ResourceRow, (source_id, env_id)) if source_id else None
        budget_id = identity("budget", runtime.plan_id)
        budget = db.get(ResponseBudgetRow, budget_id)
        if budget is None:
            budget = ResponseBudgetRow(
                budget_id=budget_id,
                environment_id=env_id,
                plan_id=runtime.plan_id,
                max_actions=policy.max_actions_per_plan,
                used_actions=0,
                valid_until=min(control.valid_until, now + timedelta(seconds=policy.budget_seconds)),
            )
            db.add(budget)
            db.flush()
        if budget.valid_until <= now or budget.used_actions >= budget.max_actions:
            raise AccessDenied("response action budget exhausted")
        action_id = identity("action", [env_id, task.task_id])
        action = ActionRequest(
            action_id=action_id,
            incident_id=task.incident_id,
            task_id=task.task_id,
            environment_id=env_id,
            capability_id=definition.capability_id,
            capability_version=definition.version,
            source=contract_from(source_row, ResourceRef)
            if source_row and definition.operation_kind != "PASSIVE_READ"
            else None,
            target=contract_from(target, ResourceRef),
            parameters=task.parameters,
            scope_id=scope.scope_id,
            scope_version=scope.version,
            environment_profile_version=env.version,
            policy_version=control.policy_version,
            expected_state_version=execution_version(db, task, plan.incident_version),
            preconditions=["same incident snapshot", "current scope and policy", "current worker lease"],
            evidence_ids=task.evidence_ids,
            created_at=now,
            expires_at=now + timedelta(seconds=policy.action_ttl_seconds),
            ttl_seconds=LabInput.model_validate(task.parameters).ttl_seconds
            if task.capability_id == CAPABILITY
            else 0,
            idempotency_key=action_id,
            ownership_tag=("zhiyu-lab:" + (task.parameters.get("prior_action_id") or action_id))
            if task.capability_id == CAPABILITY
            else "zhiyu-read-only:" + task.task_id,
            rollback_policy_id=definition.rollback_policy,
        )
        db.add(ActionRow(**values_for(action, ActionRow), action_digest=action_digest(action)))
        budget.used_actions += 1
        db.flush()
        db.add(
            ActionControlRow(
                action_id=action_id,
                environment_id=env_id,
                task_id=task.task_id,
                budget_id=budget_id,
                status="PROPOSED",
                authorization_id=None,
                created_at=now,
            )
        )
        db.flush()
        emit(
            db,
            env_id,
            "ActionRequest",
            action_id,
            "ActionRequested",
            "immutable structured intent from managed task",
            principal.principal_id,
        )
        return action

    def evaluate(
        self,
        action: ActionRequest,
        task: TaskRow,
        generation: int,
        principal: ServicePrincipal,
        now: datetime,
        *,
        extra_denials: list[str] | None = None,
    ) -> AuthorizationDecision:
        """Build snapshot from authoritative rows. Caller owns transaction; denial is persisted."""
        start = perf_counter()
        db, env_id = self.db, task.environment_id
        lease = current_lease(db, task, principal.principal_id, generation, now)
        control, policy = managed_policy(db, env_id, now)
        definition, config = CapabilityRegistry(db).resolve(action.capability_id, action.capability_version)
        env = db.get(EnvironmentRow, env_id)
        scope = db.get(ScopeRow, (action.scope_id, env_id))
        target = db.get(ResourceRow, (action.target.resource_id, env_id))
        source_row = db.get(ResourceRow, (action.source.resource_id, env_id)) if action.source else None
        incident = db.get(IncidentRow, action.incident_id)
        runtime = db.get(TaskRuntimeRow, task.task_id)
        state = db.get(ActionControlRow, action.action_id)
        if (
            env is None
            or scope is None
            or target is None
            or incident is None
            or runtime is None
            or state is None
        ):
            raise ReferenceError("authorization identity is missing")
        budget = db.get(ResponseBudgetRow, state.budget_id)
        stored = db.get(ActionRow, action.action_id)
        plan = db.get(PlanRow, runtime.plan_id)
        assert budget is not None and stored is not None and plan is not None
        denied = list(extra_denials or [])
        if action.capability_id == CAPABILITY:
            from zhiyu.response.lab_client import binding_for

            try:
                binding_for(action)
                parameters = LabInput.model_validate(action.parameters)
                if parameters.operation == "compensate":
                    original = db.get(ActionRow, parameters.prior_action_id)
                    if (
                        original is None
                        or original.capability_id != CAPABILITY
                        or original.environment_id != env_id
                        or original.scope_id != action.scope_id
                        or original.target != action.target.model_dump(mode="json")
                        or original.parameters.get("operation", "contain") != "contain"
                    ):
                        denied.append("invalid_compensation_owner")
            except (ValueError, KeyError):
                denied.append("unconfigured_lab_target")
            if (
                env.deployment_stage != "LAB"
                or env.asset_domain != "IT"
                or env.active_validation != "ISOLATED_ONLY"
                or env.autonomy_mode != "CONTROLLED_AUTONOMY"
            ):
                denied.append("lab_containment_not_enabled")
        stored_action = contract_from(stored, ActionRequest)
        if action_digest(action) != stored.action_digest:
            denied.append("action_digest_mismatch")
        # Bind even rejected mutation attempts to the original immutable ActionRequest FK.
        action = stored_action
        expected_task = next((t for t in plan.tasks if t["task_id"] == task.task_id), None)
        if expected_task is None or any(
            expected_task[k] != getattr(task, k)
            for k in [
                "capability_id",
                "capability_version",
                "parameters",
                "scope_id",
                "target_resource_ids",
                "evidence_ids",
            ]
        ):
            denied.append("task_snapshot_mutation")
        if any(permission not in principal.permissions for permission in definition.required_permissions):
            denied.append("insufficient_principal_permissions")
        if (
            env_id not in principal.environment_ids
            or action.environment_id != env_id
            or incident.environment_id != env_id
        ):
            denied.append("environment_mismatch")
        if control.policy_version != env.policy_version or action.policy_version != control.policy_version:
            denied.append("policy_version_mismatch")
        if not admits(db, task, action, incident):
            denied.append("stale_incident_version")
        if action.expires_at <= now or action.created_at > now:
            denied.append("expired_policy_context")
        if budget.valid_until <= now or budget.used_actions > budget.max_actions:
            denied.append("budget_expired")
        profile = contract_from(env, EnvironmentProfile)
        scope_contract = contract_from(scope, ScopeDefinition)
        target_contract = contract_from(target, ResourceRef)
        source = contract_from(source_row, ResourceRef) if source_row else None
        denied.extend(
            ScopeEvaluator().evaluate(
                action,
                profile,
                scope_contract,
                target_contract,
                source,
                definition,
                config.supported_resource_types,
                now,
            )
        )
        if env.deployment_stage not in config.supported_profiles:
            denied.append("unsupported_environment_profile")
        autonomy = {"OBSERVE_ONLY": 0, "ASSISTED": 1, "CONTROLLED_AUTONOMY": 2, "VALIDATION": 2}
        if (
            config.minimum_autonomy not in autonomy
            or autonomy.get(env.autonomy_mode, -1) < autonomy[config.minimum_autonomy]
        ):
            denied.append("insufficient_autonomy")
        if definition.operation_kind != "PASSIVE_READ" and (
            source is None or policy.worker_sources.get(principal.principal_id) != source.resource_id
        ):
            denied.append("worker_source_binding_mismatch")
        health = db.get(
            CapabilityHealthRow, (definition.capability_id, definition.version, env_id, policy.worker_pool)
        )
        health_status = (
            health.status
            if health and 0 <= (now - health.checked_at).total_seconds() <= policy.health_ttl_seconds
            else "UNVERIFIED"
        )
        sensors = list(
            db.scalars(
                select(SensorHealthRow).where(
                    SensorHealthRow.environment_id == env_id,
                    SensorHealthRow.sensor_id.in_(env.required_sensor_ids),
                )
            )
        )
        sensors_valid = len(sensors) == len(set(env.required_sensor_ids)) and all(
            s.status == "HEALTHY"
            and s.coverage_validated
            and scope.scope_id in s.coverage_scope_ids
            and 0 <= (now - s.last_heartbeat_at).total_seconds() <= policy.health_ttl_seconds
            for s in sensors
        )
        evidence = list(
            db.scalars(
                select(EvidenceRow).where(
                    EvidenceRow.environment_id == env_id,
                    EvidenceRow.incident_id == incident.incident_id,
                    EvidenceRow.evidence_id.in_(action.evidence_ids),
                )
            )
        )
        evidence_valid = len(evidence) == len(set(action.evidence_ids)) and all(
            e.valid_until > now and e.trust_status == "VERIFIED_ORIGIN" for e in evidence
        )
        events = incident_events(db, env_id, incident.incident_id)
        raw_records = raw_for_events(db, env_id, events)
        evidence_valid = evidence_valid and all(
            len(e.source_event_ids) == 1
            and (raw := raw_records.get(e.source_event_ids[0])) is not None
            and raw.integrity_hash == e.integrity_hash
            for e in evidence
        )
        context_id = "authctx-" + uuid4().hex
        context = AuthorizationContext.model_validate(
            {
                "authorization_context_id": context_id,
                "environment_id": env_id,
                "action_id": action.action_id,
                "action_digest": stored.action_digest,
                "principal_id": principal.principal_id,
                "principal_role": "SERVICE_WORKER",
                "environment_profile_version": env.version,
                "scope_id": scope.scope_id,
                "scope_version": scope.version,
                "capability_id": definition.capability_id,
                "capability_version": definition.version,
                "target_resource_id": target.resource_id,
                "source_resource_id": source.resource_id if source else None,
                "asset_criticality": policy.asset_criticality.get(target.resource_id, "LOW"),
                "business_impact": config.business_impact,
                "evidence_quality": "HIGH" if evidence_valid else "LOW",
                "sensor_health_status": "HEALTHY" if sensors_valid else "UNKNOWN",
                "autonomy_mode": env.autonomy_mode,
                "load_mode": env.load_mode,
                "requested_risk": definition.base_risk,
                "policy_version": control.policy_version,
                "budget_id": budget.budget_id,
                "created_at": now,
            }
        )
        facts: dict[str, Any] = {
            "denied_dimensions": sorted(set(denied)),
            "operation_kind": definition.operation_kind,
            "capability_health": health_status,
            "active_validation": env.active_validation,
            "deployment_stage": env.deployment_stage,
            "asset_domain": env.asset_domain,
            "max_auto_risk": env.max_auto_risk,
            "environment": profile.model_dump(mode="json"),
            "scope": scope_contract.model_dump(mode="json"),
            "target": target_contract.model_dump(mode="json"),
            "source": source.model_dump(mode="json") if source else None,
            "capability": definition.model_dump(mode="json"),
            "capability_config_version": config.row_version,
            "capability_health_snapshot": contract_from(health, CapabilityHealth).model_dump(mode="json")
            if health
            else None,
            "sensors": [contract_from(s, SensorHealth).model_dump(mode="json") for s in sensors],
            "evidence": [
                {
                    "evidence_id": e.evidence_id,
                    "valid_until": e.valid_until.isoformat(),
                    "integrity_hash": e.integrity_hash,
                }
                for e in evidence
            ],
            "policy": policy.model_dump(mode="json"),
            "control_version": control.row_version,
            "budget": {
                "id": budget.budget_id,
                "used": budget.used_actions,
                "max": budget.max_actions,
                "valid_until": budget.valid_until.isoformat(),
            },
            "lease_id": lease.lease_id,
            "generation": generation,
            "worker_id": principal.principal_id,
            "principal": principal.model_dump(mode="json"),
            "task": contract_from(task, Task).model_dump(mode="json"),
            "incident_id": incident.incident_id,
            "incident_version": incident.state_version,
        }
        auth_ms = (perf_counter() - start) * 1000
        gate_start = perf_counter()
        decision = RiskPolicyGate().decide(
            context,
            facts,
            policy,
            decision_id="auth-" + uuid4().hex,
            valid_until=min(
                now + timedelta(seconds=policy.authorization_ttl_seconds),
                lease.expires_at,
                action.expires_at,
                control.valid_until,
                scope.valid_until,
                budget.valid_until,
            ),
        )
        policy_ms = (perf_counter() - gate_start) * 1000
        db.add(AuthorizationContextRow(**values_for(context, AuthorizationContextRow)))
        db.flush()
        db.add(AuthorizationDecisionRow(**values_for(decision, AuthorizationDecisionRow)))
        db.add(
            AuthorizationSnapshotRow(
                context_id=context_id,
                environment_id=env_id,
                action_id=action.action_id,
                budget_id=budget.budget_id,
                inputs=facts,
                rule_id=policy.rule_version,
                denied_dimensions=decision.reasons if decision.outcome == "DENY" else [],
                created_at=now,
                authorization_ms=auth_ms,
                policy_ms=policy_ms,
            )
        )
        db.flush()
        state.authorization_id = decision.authorization_id
        if state.status in {"PROPOSED", "AUTHORIZED"}:
            state.status = {"ALLOW": "AUTHORIZED", "DENY": "DENIED", "REQUIRE_APPROVAL": "WAITING_APPROVAL"}[
                decision.outcome
            ]
        emit(
            db,
            env_id,
            "AuthorizationContext",
            context_id,
            "AuthorizationEvaluated",
            ";".join(decision.reasons),
            principal.principal_id,
        )
        emit(
            db,
            env_id,
            "AuthorizationDecision",
            decision.authorization_id,
            "PolicyAllowed" if decision.outcome == "ALLOW" else "PolicyDenied",
            decision.outcome + ":" + ";".join(decision.reasons),
            principal.principal_id,
        )
        return decision
