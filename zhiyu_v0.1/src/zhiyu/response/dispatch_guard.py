"""Recheck the persisted authority at the adapter boundary while holding the environment lock."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.core.errors import ConflictError
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import (
    AuthorizationDecisionRow,
    CapabilityHealthRow,
    EnvironmentRow,
    EvidenceRow,
    IncidentRow,
    ResourceRow,
    ScopeRow,
    SensorHealthRow,
    TaskRow,
)
from zhiyu.db.response_authority import AuthorizationSnapshotRow, ResponseBudgetRow
from zhiyu.domain.contracts import (
    ActionRequest,
    CapabilityHealth,
    EnvironmentProfile,
    ResourceRef,
    ScopeDefinition,
    SensorHealth,
    Task,
)
from zhiyu.response.authorization import current_lease, managed_policy
from zhiyu.response.registry import CapabilityRegistry


def assert_current(
    db: Session,
    action: ActionRequest,
    task: TaskRow,
    decision_id: str,
    worker: str,
    generation: int,
    now: datetime,
) -> None:
    current_lease(db, task, worker, generation, now)
    decision = db.get(AuthorizationDecisionRow, decision_id)
    if (
        decision is None
        or decision.outcome != "ALLOW"
        or (decision.valid_until - now).total_seconds() < task.timeout_seconds
    ):
        raise ConflictError("authorization expired at executor boundary")
    snapshot = db.get(AuthorizationSnapshotRow, decision.authorization_context_id)
    if snapshot is None:
        raise ConflictError("authorization snapshot unavailable")
    facts = snapshot.inputs
    if contract_from(task, Task).model_dump(mode="json") != facts["task"]:
        raise ConflictError("task changed at executor boundary")
    control, policy = managed_policy(db, action.environment_id, now)
    if control.policy_version != action.policy_version or policy.model_dump(mode="json") != facts["policy"]:
        raise ConflictError("policy changed at executor boundary")
    env = db.get(EnvironmentRow, action.environment_id)
    scope = db.get(ScopeRow, (action.scope_id, action.environment_id))
    target = db.get(ResourceRow, (action.target.resource_id, action.environment_id))
    incident = db.get(IncidentRow, action.incident_id)
    if (
        env is None
        or scope is None
        or target is None
        or incident is None
        or contract_from(env, EnvironmentProfile).model_dump(mode="json") != facts["environment"]
        or contract_from(scope, ScopeDefinition).model_dump(mode="json") != facts["scope"]
        or contract_from(target, ResourceRef) != action.target
        or incident.state_version != action.expected_state_version
        or not scope.valid_from <= now < scope.valid_until
        or action.expires_at <= now
    ):
        raise ConflictError("environment scope target or incident changed at executor boundary")
    if action.source:
        source = db.get(ResourceRow, (action.source.resource_id, action.environment_id))
        if source is None or contract_from(source, ResourceRef) != action.source:
            raise ConflictError("source changed at executor boundary")
    definition, config = CapabilityRegistry(db).resolve(action.capability_id, action.capability_version)
    if (
        definition.model_dump(mode="json") != facts["capability"]
        or config.row_version != facts["capability_config_version"]
    ):
        raise ConflictError("capability changed at executor boundary")
    health = db.get(
        CapabilityHealthRow,
        (action.capability_id, action.capability_version, action.environment_id, policy.worker_pool),
    )
    if (
        health is None
        or not 0 <= (now - health.checked_at).total_seconds() <= policy.health_ttl_seconds
        or contract_from(health, CapabilityHealth).model_dump(mode="json")
        != facts["capability_health_snapshot"]
    ):
        raise ConflictError("capability health changed at executor boundary")
    sensors = list(
        db.scalars(
            select(SensorHealthRow).where(
                SensorHealthRow.environment_id == action.environment_id,
                SensorHealthRow.sensor_id.in_(env.required_sensor_ids),
            )
        )
    )
    current_sensors = sorted(
        [contract_from(s, SensorHealth).model_dump(mode="json") for s in sensors],
        key=lambda s: s["sensor_id"],
    )
    if current_sensors != sorted(facts["sensors"], key=lambda s: s["sensor_id"]) or any(
        not 0 <= (now - s.last_heartbeat_at).total_seconds() <= policy.health_ttl_seconds for s in sensors
    ):
        raise ConflictError("sensor state changed at executor boundary")
    for item in facts["evidence"]:
        evidence = db.get(EvidenceRow, item["evidence_id"])
        if (
            evidence is None
            or evidence.incident_id != action.incident_id
            or evidence.environment_id != action.environment_id
            or evidence.valid_until <= now
            or evidence.integrity_hash != item["integrity_hash"]
            or evidence.trust_status != "VERIFIED_ORIGIN"
        ):
            raise ConflictError("evidence changed at executor boundary")
    budget = db.get(ResponseBudgetRow, facts["budget"]["id"])
    if budget is None or budget.valid_until <= now or budget.used_actions > budget.max_actions:
        raise ConflictError("execution budget expired")
