"""Transactional state observations and finite deterministic re-plans."""

from datetime import datetime
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ConflictError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import (
    ContextRow,
    EvidenceRow,
    IncidentRow,
    PlanRow,
    StateEntityRow,
    TaskRow,
    VerificationResultRow,
)
from zhiyu.db.response_planning import ResponsePlanRow, TaskRuntimeRow
from zhiyu.db.verification_decisions import EffectivenessRow
from zhiyu.db.verification_replan import (
    ReplanBudgetRow,
    ReplanDecisionRow,
    ResponseCycleRow,
    VerificationStateUpdateRow,
)
from zhiyu.db.verification_runtime import VerificationObservationRow, VerificationRuntimeRow
from zhiyu.domain.contracts import AIPlan, ContextBundle, StateEntity, Task, TaskStatus
from zhiyu.response.planner import TaskGraphValidator, emit, identity
from zhiyu.services.incident_lifecycle import transition
from zhiyu.verification.lifecycle import move, semantic_hash
from zhiyu.verification.runtime import instant, lock_environment


class ReplanBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_replans: int = Field(default=2, ge=0, le=3)
    max_total_actions: int = Field(default=12, ge=1, le=100)
    max_elapsed_time: int = Field(default=600, ge=10, le=3600)
    max_risk_escalation: int = Field(default=0, ge=0, le=0)
    risk_ceiling: str = Field(default="R2", pattern=r"^R[012]$")
    policy_version: str = "replan/1.0.0"


def activate(
    engine: Engine,
    env: str,
    plan_id: str,
    principal: ServicePrincipal,
    budget: ReplanBudget = ReplanBudget(),
    *,
    now: datetime | None = None,
) -> None:
    principal.require("verification:write", env)
    with Session(engine) as db:
        plan_row = db.get(PlanRow, plan_id)
        if not plan_row or plan_row.environment_id != env:
            raise ReferenceError("plan not found in environment")
        incident = db.get(IncidentRow, plan_row.incident_id)
        assert incident is not None
        incident_id, version, status = incident.incident_id, incident.state_version, incident.status
    if status == "TRIAGED":
        with Session(engine) as db:
            transition(
                db,
                environment_id=env,
                incident_id=incident_id,
                target="INVESTIGATING",
                expected_version=version,
                principal=principal,
                now=now,
            )
    with Session(engine) as db, db.begin():
        environment = lock_environment(db, env)
        existing = db.get(ResponseCycleRow, plan_id)
        if existing:
            old = db.get(ReplanBudgetRow, existing.root_plan_id)
            if old and old.configuration != budget.model_dump(mode="json"):
                raise ConflictError("cycle budget cannot be silently replaced")
            return
        ts = instant(db, now)
        plan_row = db.get(PlanRow, plan_id)
        incident = db.get(IncidentRow, incident_id)
        metadata = db.get(ResponsePlanRow, plan_id)
        assert plan_row is not None and incident is not None and metadata is not None
        plan = contract_from(plan_row, AIPlan)
        if (
            incident.status != "INVESTIGATING"
            or budget.max_replans > plan.max_replans
            or len(plan.tasks) > budget.max_total_actions
        ):
            raise ConflictError("cycle exceeds plan or lifecycle budget")
        frozen = metadata.inputs["incident"]
        if semantic_hash(incident) != canonical_hash(
            {
                k: frozen[k]
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
        ):
            raise ConflictError("incident semantic snapshot changed")
        if budget.risk_ceiling > environment.max_auto_risk:
            raise ConflictError("replan ceiling exceeds initial environment authority")
        TaskGraphValidator().validate(db, plan, ts)
        if any(
            (evidence := db.get(EvidenceRow, eid)) is None
            or evidence.valid_until <= ts
            or evidence.trust_status != "VERIFIED_ORIGIN"
            for eid in incident.evidence_ids
        ):
            raise ConflictError("fresh attested evidence required for cycle activation")
        move(
            db,
            incident,
            "PLANNED",
            ts,
            principal.principal_id,
            "validated plan, scope, DAG and bounded replan policy",
        )
        db.add(
            ResponseCycleRow(
                plan_id=plan_id,
                environment_id=env,
                incident_id=incident_id,
                expected_version=incident.state_version,
                semantic_hash=semantic_hash(incident),
                root_plan_id=plan_id,
                parent_plan_id=None,
                created_at=ts,
            )
        )
        db.add(
            ReplanBudgetRow(
                root_plan_id=plan_id,
                configuration=budget.model_dump(mode="json"),
                current_replan_count=0,
                reserved_actions=len(plan.tasks),
                started_at=ts,
            )
        )


def update_state(
    db: Session, result: VerificationResultRow, runtime: VerificationRuntimeRow, now: datetime, actor: str
) -> None:
    if db.get(VerificationStateUpdateRow, result.verification_id):
        return
    start = perf_counter()
    ids = []
    observations = db.scalars(
        select(VerificationObservationRow).where(VerificationObservationRow.spec_id == runtime.spec_id)
    )
    for observation in observations:
        evidence = db.get(EvidenceRow, observation.evidence_id)
        assert evidence is not None
        entity_id = identity("state-observation", [result.verification_id, observation.check_id])
        row = StateEntity(
            entity_id=entity_id,
            environment_id=result.environment_id,
            entity_type="VERIFICATION_OBSERVATION",
            state_version=1,
            claim_kind="OBSERVATION",
            attributes={
                "check_id": observation.check_id,
                "values": observation.samples,
                "source": observation.executor_version,
                "execution_status": observation.execution_status,
                "quality": "MEASURED" if observation.execution_status == "SUCCEEDED" else "INCOMPLETE",
                "resource_ids": result.target_ids,
                "verification_id": result.verification_id,
            },
            evidence_ids=[observation.evidence_id],
            observed_at=observation.checked_at,
            valid_until=evidence.valid_until,
        )
        db.add(StateEntityRow(**values_for(row, StateEntityRow)))
        ids.append(entity_id)
    effect = db.get(EffectivenessRow, result.verification_id)
    assert effect is not None
    entity_id = identity("state-inference", result.verification_id)
    inferred = StateEntity(
        entity_id=entity_id,
        environment_id=result.environment_id,
        entity_type="VERIFICATION_INFERENCE",
        state_version=1,
        claim_kind="INFERENCE",
        attributes={"effectiveness": effect.decision, "verification_status": result.status},
        evidence_ids=result.evidence_ids,
        observed_at=now,
        valid_until=result.valid_until,
    )
    db.add(StateEntityRow(**values_for(inferred, StateEntityRow)))
    ids.append(entity_id)
    db.flush()
    db.add(
        VerificationStateUpdateRow(
            verification_id=result.verification_id,
            entity_ids=ids,
            updated_at=now,
            latency_ms=(perf_counter() - start) * 1000,
        )
    )
    emit(
        db,
        result.environment_id,
        "StateEntity",
        result.verification_id,
        "EnvironmentStateUpdated",
        "Immutable observed values separate from effect inference",
        actor,
    )


class DeterministicReplanner:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def handle(
        self, env: str, verification_id: str, principal: ServicePrincipal, *, now: datetime | None = None
    ) -> dict[str, Any]:
        principal.require("verification:replan", env)
        principal.require("response:plan", env)
        start = perf_counter()
        with Session(self.engine) as db, db.begin():
            environment = lock_environment(db, env)
            result = db.get(VerificationResultRow, verification_id)
            if not result or result.environment_id != env:
                raise ReferenceError("verification not found in environment")
            prior = db.get(ReplanDecisionRow, verification_id)
            if prior:
                return self.receipt(prior)
            runtime = db.get(VerificationRuntimeRow, result.verification_spec_id)
            assert runtime is not None
            cycle = db.get(ResponseCycleRow, runtime.plan_id)
            if not cycle:
                raise ConflictError("plan did not opt into continuous verification")
            budget_row = db.get(ReplanBudgetRow, cycle.root_plan_id)
            assert budget_row is not None
            policy = ReplanBudget.model_validate(budget_row.configuration)
            ts = instant(db, now)
            incident = db.get(IncidentRow, result.incident_id)
            assert incident is not None
            if incident.status != "VERIFYING" or incident.state_version != cycle.expected_version:
                raise ConflictError("verification callback belongs to a stale incident cycle")
            update_state(db, result, runtime, ts, principal.principal_id)
            observations = list(
                db.scalars(
                    select(VerificationObservationRow).where(
                        VerificationObservationRow.spec_id == runtime.spec_id
                    )
                )
            )
            # Semantic data fingerprint excludes IDs/times/latency so repeated identical reads aren't new evidence.
            evidence_fp = canonical_hash(
                [
                    {
                        "check": o.check_id,
                        "data": [
                            {k: v for k, v in sample.items() if k not in {"latency_ms", "endpoint"}}
                            for sample in o.samples
                        ],
                    }
                    for o in sorted(observations, key=lambda row: row.check_id)
                ]
            )
            capability = "query_incident_evidence" if result.status == "FAIL" else "collect_resource_context"
            action_fp = canonical_hash(
                [capability, sorted(result.target_ids), runtime.scope_id, {"limit": 50}]
            )
            plan_fp = canonical_hash([action_fp, result.status])
            history = list(
                db.scalars(
                    select(ReplanDecisionRow).where(
                        ReplanDecisionRow.root_plan_id == cycle.root_plan_id,
                        ReplanDecisionRow.status == "CREATED",
                    )
                )
            )
            status, reason = (
                "CREATED",
                "diagnose trustworthy failure"
                if result.status == "FAIL"
                else "collect additional observation",
            )
            if result.status == "PASS":
                status, reason = (
                    "NO_REPLAN",
                    "Temporary CONTAINMENT verified; root cause remains; TTL review pending; no remediation or closure claim"
                    if result.objective_type == "CONTAINMENT"
                    else "DETECTION verified; residual risk remains; no containment or closure claim",
                )
            elif (
                budget_row.current_replan_count >= policy.max_replans
                or budget_row.reserved_actions + len(result.target_ids) > policy.max_total_actions
                or (ts - budget_row.started_at).total_seconds() >= policy.max_elapsed_time
            ):
                status, reason = "REPLAN_EXHAUSTED", "bounded count/action/time budget exhausted"
            elif result.valid_until <= ts or not observations or not any(o.samples for o in observations):
                status, reason = "REPLAN_EXHAUSTED", "no current independent observation"
            elif any(h.evidence_fingerprint == evidence_fp for h in history):
                status, reason = "REPLAN_EXHAUSTED", "no new semantic evidence; repeated observation loop"
            elif any(h.action_fingerprint == action_fp or h.plan_fingerprint == plan_fp for h in history):
                status, reason = (
                    "REPLAN_EXHAUSTED",
                    "repeated plan/action fingerprint; finite alternatives exhausted",
                )
            elif (
                "R1" > min(policy.risk_ceiling, environment.max_auto_risk)
                and capability == "query_incident_evidence"
            ):
                status, reason = "REQUIRE_APPROVAL", "requested R1 exceeds initial or current risk ceiling"
            new_plan = None
            emit(db, env, "Replan", verification_id, "ReplanRequested", reason, principal.principal_id)
            if status == "CREATED":
                move(
                    db,
                    incident,
                    "INVESTIGATING",
                    ts,
                    principal.principal_id,
                    "verification_fail"
                    if result.status == "FAIL"
                    else "observation_missing; repair observation first",
                )
                new_plan = self.create_plan(
                    db, runtime, cycle, incident, result, capability, policy, principal, ts
                )
                budget_row.current_replan_count += 1
                budget_row.reserved_actions += len(result.target_ids)
            elif status == "REPLAN_EXHAUSTED":
                move(db, incident, "HUMAN_REVIEW", ts, principal.principal_id, reason)
            elif status == "REQUIRE_APPROVAL":
                # No tasks are emitted, so a raised ceiling cannot accidentally be dispatched.
                move(
                    db,
                    incident,
                    "HUMAN_REVIEW",
                    ts,
                    principal.principal_id,
                    "budget_exhausted; risk escalation needs human review",
                )
            incident.residual_risks = result.residual_risks
            decision = ReplanDecisionRow(
                verification_id=verification_id,
                root_plan_id=cycle.root_plan_id,
                parent_plan_id=cycle.plan_id,
                new_plan_id=new_plan,
                status=status,
                reason=reason,
                replan_count=budget_row.current_replan_count,
                policy_version=policy.policy_version,
                plan_fingerprint=plan_fp,
                action_fingerprint=action_fp,
                evidence_fingerprint=evidence_fp,
                created_at=ts,
                latency_ms=(perf_counter() - start) * 1000,
            )
            db.add(decision)
            emit(
                db,
                env,
                "Replan",
                verification_id,
                "ReplanCreated"
                if status == "CREATED"
                else "ReplanBudgetExhausted"
                if status == "REPLAN_EXHAUSTED"
                else "ReplanBlocked",
                reason,
                principal.principal_id,
            )
            return self.receipt(decision)

    @staticmethod
    def create_plan(
        db: Session,
        runtime: VerificationRuntimeRow,
        cycle: ResponseCycleRow,
        incident: IncidentRow,
        result: VerificationResultRow,
        capability: str,
        policy: ReplanBudget,
        principal: ServicePrincipal,
        now: datetime,
    ) -> str:
        old = db.get(PlanRow, cycle.plan_id)
        assert old is not None
        source = contract_from(old, AIPlan)
        context_row = db.get(ContextRow, source.context_id)
        assert context_row is not None
        plan_id = identity("replan", result.verification_id)
        context = contract_from(context_row, ContextBundle).model_copy(
            update={
                "context_id": identity("context", plan_id),
                "state_version": incident.state_version,
                "created_at": now,
                "policy_version": policy.policy_version,
            }
        )
        # Response authorization continues using attested incident input evidence, not verification-derived claims.
        if any(
            (e := db.get(EvidenceRow, eid)) is None or e.valid_until <= now for eid in incident.evidence_ids
        ):
            raise ConflictError("fresh attested incident evidence is required for a new action plan")
        tasks = [
            Task(
                task_id=identity("task", [plan_id, target]),
                incident_id=incident.incident_id,
                environment_id=incident.environment_id,
                dependencies=[],
                capability_id=capability,
                capability_version="1.0.0",
                target_resource_ids=[target],
                scope_id=runtime.scope_id,
                parameters={"limit": 50},
                status=TaskStatus.QUEUED,
                priority=source.tasks[0].priority,
                timeout_seconds=5,
                max_attempts=3,
                attempt_count=0,
                expected_output="Additional independent context; not proof of remediation",
                evidence_ids=incident.evidence_ids,
                created_at=now,
                queued_at=now,
            )
            for target in result.target_ids
        ]
        plan = AIPlan(
            plan_id=plan_id,
            incident_id=incident.incident_id,
            environment_id=incident.environment_id,
            context_id=context.context_id,
            hypotheses=source.hypotheses,
            tasks=tasks,
            stop_conditions=[
                "bounded budget",
                "no new evidence",
                "repeated plan",
                "fresh authorization denied",
            ],
            max_replans=policy.max_replans,
            total_model_calls=0,
        )
        TaskGraphValidator().validate(db, plan, now)
        db.add(ContextRow(**values_for(context, ContextRow)))
        db.flush()
        db.add(PlanRow(**values_for(plan, PlanRow)))
        db.flush()
        from zhiyu.domain.contracts import SecurityIncident

        snapshot = contract_from(incident, SecurityIncident).model_dump(mode="json")
        db.add(
            ResponsePlanRow(
                plan_id=plan_id,
                environment_id=incident.environment_id,
                incident_id=incident.incident_id,
                incident_version=incident.state_version,
                planner_version="deterministic-replanner/1.0.0",
                policy_version=policy.policy_version,
                scope_id=runtime.scope_id,
                snapshot_hash=canonical_hash(snapshot),
                inputs={"incident": snapshot, "verification_id": result.verification_id},
                configuration=policy.model_dump(mode="json"),
                reasons=[result.recommended_next_step],
                created_by=principal.principal_id,
                created_at=now,
                generation_ms=0,
                graph_ms=0,
            )
        )
        db.flush()
        for task in tasks:
            db.add(TaskRow(**values_for(task, TaskRow)))
        db.flush()
        for task in tasks:
            db.add(
                TaskRuntimeRow(
                    task_id=task.task_id,
                    environment_id=task.environment_id,
                    plan_id=plan_id,
                    task_type="PASSIVE_CONTEXT",
                    ready_at=now,
                    generation=0,
                )
            )
            emit(
                db,
                task.environment_id,
                "Task",
                task.task_id,
                "TaskCreated",
                "new authorization required",
                principal.principal_id,
            )
        move(db, incident, "PLANNED", now, principal.principal_id, "bounded new plan validated")
        db.add(
            ResponseCycleRow(
                plan_id=plan_id,
                environment_id=incident.environment_id,
                incident_id=incident.incident_id,
                expected_version=incident.state_version,
                semantic_hash=semantic_hash(incident),
                root_plan_id=cycle.root_plan_id,
                parent_plan_id=cycle.plan_id,
                created_at=now,
            )
        )
        return plan_id

    @staticmethod
    def receipt(row: ReplanDecisionRow) -> dict[str, Any]:
        return {
            k: getattr(row, k)
            for k in ("verification_id", "parent_plan_id", "new_plan_id", "status", "reason", "replan_count")
        }
