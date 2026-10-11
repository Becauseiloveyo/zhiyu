"""Deterministic planning with persisted input identity and relational dependencies."""

from dataclasses import asdict, dataclass
from datetime import datetime
from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ConflictError, ReferenceError, StaleVersionError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import (
    CapabilityRow,
    ContextRow,
    EnvironmentRow,
    EventRow,
    EvidenceRow,
    IncidentRow,
    PlanRow,
    ResourceRow,
    ScopeRow,
    TaskRow,
)
from zhiyu.db.response_planning import ResponsePlanRow, TaskEdgeRow, TaskRuntimeRow
from zhiyu.domain.contracts import (
    AIPlan,
    ContextBundle,
    Hypothesis,
    SecurityIncident,
    Task,
    TaskStatus,
)
from zhiyu.response.catalog import CAPABILITY_VERSION, PASSIVE_CAPABILITIES, validate_input
from zhiyu.response.lab_protocol import CAPABILITY
from zhiyu.services.event_intelligence import publish_change


@dataclass(frozen=True)
class PlannerPolicy:
    planner_version: str = "deterministic-response/1.0.0"
    policy_version: str = "response-plan/1.0.0"
    include_http_probe: bool = False
    max_attempts: int = 3
    max_replans: int = 0
    lab_target: str | None = None
    lab_parameters: dict | None = None


def identity(prefix: str, value: object) -> str:
    return prefix + "-" + canonical_hash(value)


def emit(
    db: Session, environment: str, kind: str, object_id: str, event: str, reason: str, actor: str
) -> None:
    publish_change(
        db,
        environment_id=environment,
        kind=kind,
        object_id=object_id,
        event_type=event,
        reference=f"db://{kind}/{object_id}",
        reason=reason,
        actor=actor,
        trace=object_id,
    )


class TaskGraphValidator:
    def validate(self, db: Session, plan: AIPlan, instant: datetime) -> None:
        plan = AIPlan.model_validate(plan.model_dump())
        env = db.get(EnvironmentRow, plan.environment_id)
        if env is None:
            raise ReferenceError("environment missing")
        incident = db.get(IncidentRow, plan.incident_id)
        if incident is None or incident.environment_id != plan.environment_id:
            raise ReferenceError("incident missing in environment")
        scopes: dict[str, ScopeRow | None] = {}
        for task in plan.tasks:
            if len(task.dependencies) != len(set(task.dependencies)):
                raise ConflictError("duplicate dependency")
            existing = db.get(TaskRuntimeRow, task.task_id)
            if existing and existing.plan_id != plan.plan_id:
                raise ConflictError("cross-plan task")
            cap = db.get(CapabilityRow, (task.capability_id, task.capability_version))
            if cap is None or cap.integration_status == "DESIGN":
                raise ReferenceError("capability missing or not adapted")
            try:
                validate_input(task.capability_id, task.parameters)
            except ValueError as error:
                raise ConflictError("invalid structured capability input") from error
            scope = scopes.setdefault(task.scope_id, db.get(ScopeRow, (task.scope_id, plan.environment_id)))
            if (
                scope is None
                or scope.scope_id not in env.scope_ids
                or not scope.valid_from <= instant < scope.valid_until
            ):
                raise ConflictError("inactive or unauthorized scope")
            if (
                task.capability_id not in scope.allowed_capabilities
                or task.capability_id not in env.capability_allowlist
            ):
                raise ConflictError("capability outside scope")
            for target in task.target_resource_ids:
                resource = db.get(ResourceRow, (target, plan.environment_id))
                if (
                    resource is None
                    or target not in scope.target_resource_ids
                    or target not in incident.affected_asset_ids
                ):
                    raise ReferenceError("target outside scope")
            if task.timeout_seconds > cap.timeout_seconds or task.max_attempts > 3:
                raise ConflictError("task exceeds managed budget")


class DeterministicResponsePlanner:
    def __init__(self, db: Session, policy: PlannerPolicy = PlannerPolicy()) -> None:
        self.db, self.policy = db, policy

    def create(
        self,
        environment_id: str,
        incident_id: str,
        *,
        expected_version: int,
        scope_id: str,
        principal: ServicePrincipal,
        now: datetime | None = None,
    ) -> AIPlan:
        principal.require("response:plan", environment_id)
        start = perf_counter()
        db, policy = self.db, self.policy
        if policy.lab_parameters is not None:
            principal.require("response:admin", environment_id)
            principal.require("capability:" + CAPABILITY, environment_id)
            validate_input(CAPABILITY, policy.lab_parameters)
            if not policy.lab_target:
                raise ConflictError("explicit Lab target required")
        with db.begin():
            db.scalar(
                select(EnvironmentRow)
                .where(EnvironmentRow.environment_id == environment_id)
                .with_for_update()
            )
            row = db.scalar(
                select(IncidentRow)
                .where(IncidentRow.environment_id == environment_id, IncidentRow.incident_id == incident_id)
                .with_for_update()
            )
            if row is None:
                raise ReferenceError("incident not found")
            if row.state_version != expected_version:
                raise StaleVersionError("incident changed")
            incident = contract_from(row, SecurityIncident)
            if (
                incident.status not in {"TRIAGED", "INVESTIGATING"}
                or not incident.affected_asset_ids
                or not incident.evidence_ids
            ):
                raise ConflictError("incident not ready for planning")
            snapshot = incident.model_dump(mode="json")
            plan_id = identity(
                "plan",
                [
                    environment_id,
                    incident_id,
                    expected_version,
                    policy.planner_version,
                    policy.policy_version,
                ],
            )
            previous = db.get(ResponsePlanRow, plan_id)
            if previous:
                if (
                    previous.snapshot_hash != canonical_hash(snapshot)
                    or previous.scope_id != scope_id
                    or previous.configuration != asdict(policy)
                ):
                    raise ConflictError("planning identity reused with different inputs")
                stored = db.get(PlanRow, plan_id)
                assert stored is not None
                return contract_from(stored, AIPlan)
            instant = now or db.scalar(select(func.clock_timestamp()))
            assert instant is not None
            events = list(
                db.scalars(
                    select(EventRow).where(
                        EventRow.environment_id == environment_id,
                        EventRow.event_id.in_(incident.related_event_ids),
                    )
                )
            )
            if not events or not any(e.activity_category == "authentication" for e in events):
                raise ConflictError("unsupported incident activity")
            evidence = list(
                db.scalars(
                    select(EvidenceRow).where(
                        EvidenceRow.environment_id == environment_id,
                        EvidenceRow.incident_id == incident_id,
                        EvidenceRow.evidence_id.in_(incident.evidence_ids),
                    )
                )
            )
            if len(evidence) != len(set(incident.evidence_ids)) or any(
                e.valid_until <= instant for e in evidence
            ):
                raise ConflictError("missing or stale planning evidence")
            if len(set(incident.affected_asset_ids)) > 16:
                raise ConflictError("planning target budget exceeded")
            tasks = []
            for target in sorted(set(incident.affected_asset_ids)):
                if policy.lab_parameters is not None and target != policy.lab_target:
                    continue
                capabilities = list(PASSIVE_CAPABILITIES)
                if policy.include_http_probe:
                    capabilities.append("safe_http_probe")
                if policy.lab_parameters is not None:
                    capabilities = [CAPABILITY]
                root = identity("task", [plan_id, target, capabilities[0]])
                read_tasks = [identity("task", [plan_id, target, c]) for c in capabilities[1:3]]
                for index, capability in enumerate(capabilities):
                    parameters = validate_input(
                        capability, policy.lab_parameters or {} if capability == CAPABILITY else {}
                    )
                    dependencies = [] if index == 0 else read_tasks if index == 3 else [root]
                    tasks.append(
                        Task(
                            task_id=identity("task", [plan_id, target, capability]),
                            incident_id=incident_id,
                            environment_id=environment_id,
                            dependencies=dependencies,
                            capability_id=capability,
                            capability_version=CAPABILITY_VERSION,
                            target_resource_ids=[target],
                            scope_id=scope_id,
                            parameters=parameters,
                            status=TaskStatus.BLOCKED if dependencies else TaskStatus.QUEUED,
                            priority=incident.priority,
                            timeout_seconds=5,
                            max_attempts=1 if capability == CAPABILITY else policy.max_attempts,
                            attempt_count=0,
                            expected_output="Structured execution receipt; does not establish security success",
                            evidence_ids=sorted(incident.evidence_ids),
                            created_at=instant,
                            queued_at=instant,
                        )
                    )
            context = ContextBundle(
                context_id=identity("context", plan_id),
                environment_id=environment_id,
                incident_id=incident_id,
                state_version=expected_version,
                evidence_ids=sorted(incident.evidence_ids),
                excluded_evidence_reasons={},
                unresolved_conflicts=["Authentication signals do not establish hostile intent"],
                sensor_health_ids=[],
                capability_ids=sorted({t.capability_id for t in tasks}),
                policy_version=policy.policy_version,
                token_budget=1,
                data_classification="SENSITIVE",
                egress_allowed=False,
                summary_version=policy.planner_version,
                prompt_version="NOT_USED_NO_MODEL",
                created_at=instant,
            )
            plan = AIPlan(
                plan_id=plan_id,
                incident_id=incident_id,
                environment_id=environment_id,
                context_id=context.context_id,
                hypotheses=[
                    Hypothesis(
                        hypothesis_id=identity("hyp", plan_id),
                        claim="Authentication signals warrant scoped context collection; hostile intent is unproven",
                        evidence_ids=sorted(incident.evidence_ids),
                        counter_evidence_ids=[],
                        missing_evidence=["Independent security verification"],
                        model_confidence=None,
                    )
                ],
                tasks=tasks,
                stop_conditions=[
                    "scope/policy/identity becomes stale",
                    "budget exhausted",
                    "authorization denied",
                ],
                max_replans=min(3, max(0, policy.max_replans)),
                total_model_calls=0,
            )
            TaskGraphValidator().validate(db, plan, instant)
            generated = (perf_counter() - start) * 1000
            graph_start = perf_counter()
            db.add(ContextRow(**values_for(context, ContextRow)))
            db.flush()
            db.add(PlanRow(**values_for(plan, PlanRow)))
            db.flush()
            metadata = ResponsePlanRow(
                plan_id=plan_id,
                environment_id=environment_id,
                incident_id=incident_id,
                incident_version=expected_version,
                planner_version=policy.planner_version,
                policy_version=policy.policy_version,
                scope_id=scope_id,
                snapshot_hash=canonical_hash(snapshot),
                inputs={"incident": snapshot},
                configuration=asdict(policy),
                reasons=[
                    "authentication context collection",
                    "no security verdict or direct execution",
                    "all tasks require fresh authorization",
                ],
                created_by=principal.principal_id,
                created_at=instant,
                generation_ms=generated,
                graph_ms=0,
            )
            db.add(metadata)
            db.flush()
            for task in tasks:
                db.add(TaskRow(**values_for(task, TaskRow)))
            db.flush()
            for task in tasks:
                db.add(
                    TaskRuntimeRow(
                        task_id=task.task_id,
                        environment_id=environment_id,
                        plan_id=plan_id,
                        task_type="SECURITY_CRITICAL"
                        if task.capability_id == CAPABILITY
                        else "READ_ONLY_PROBE"
                        if task.capability_id == "safe_http_probe"
                        else "PASSIVE_CONTEXT",
                        ready_at=instant,
                        failure_code=None,
                        result_ref=None,
                        generation=0,
                    )
                )
            db.flush()
            for task in tasks:
                for dependency in task.dependencies:
                    db.add(
                        TaskEdgeRow(
                            environment_id=environment_id,
                            plan_id=plan_id,
                            task_id=task.task_id,
                            depends_on=dependency,
                        )
                    )
                emit(
                    db,
                    environment_id,
                    "Task",
                    task.task_id,
                    "TaskCreated",
                    "deterministic graph",
                    principal.principal_id,
                )
            emit(
                db,
                environment_id,
                "AIPlan",
                plan_id,
                "PlanCreated",
                ";".join(metadata.reasons),
                principal.principal_id,
            )
            metadata.graph_ms = (perf_counter() - graph_start) * 1000
            db.flush()
            return plan
