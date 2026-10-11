"""智御 ai.5 Engineering Freeze 数据契约。

这些模型是实现基线：用于 API / DB / Adapter / Worker / AI structured output 之间的共同语言。
它们不等价于平台已实现，也不授予任何真实环境权限。
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Risk(str, Enum):
    R0 = "R0"; R1 = "R1"; R2 = "R2"; R3 = "R3"; R4 = "R4"; R5 = "R5"


class Verdict(str, Enum):
    PASS = "PASS"; FAIL = "FAIL"; INCONCLUSIVE = "INCONCLUSIVE"


class IncidentStatus(str, Enum):
    NEW = "NEW"; TRIAGED = "TRIAGED"; INVESTIGATING = "INVESTIGATING"; PLANNED = "PLANNED"
    WAITING_APPROVAL = "WAITING_APPROVAL"; EXECUTING = "EXECUTING"; VERIFYING = "VERIFYING"
    CONTAINED = "CONTAINED"; RESOLVED = "RESOLVED"; CLOSED = "CLOSED"; HUMAN_REVIEW = "HUMAN_REVIEW"; REOPENED = "REOPENED"


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"; BLOCKED = "BLOCKED"; WAITING_APPROVAL = "WAITING_APPROVAL"; RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"; FAILED = "FAILED"; CANCELLED = "CANCELLED"; TIMED_OUT = "TIMED_OUT"


class ActionStatus(str, Enum):
    PROPOSED = "PROPOSED"; WAITING_APPROVAL = "WAITING_APPROVAL"; AUTHORIZED = "AUTHORIZED"; DISPATCHED = "DISPATCHED"
    EXECUTING = "EXECUTING"; EXECUTED = "EXECUTED"; EXECUTION_UNKNOWN = "EXECUTION_UNKNOWN"; RECONCILING = "RECONCILING"
    COMPENSATING = "COMPENSATING"; COMPENSATED = "COMPENSATED"; COMPENSATION_FAILED = "COMPENSATION_FAILED"
    NEEDS_MANUAL = "NEEDS_MANUAL"; DENIED = "DENIED"; EXPIRED = "EXPIRED"; CANCELLED = "CANCELLED"; FAILED = "FAILED"


class EnvironmentProfile(Contract):
    object_type: Literal["EnvironmentProfile"] = "EnvironmentProfile"
    environment_id: str
    version: str
    deployment_stage: Literal["LAB", "PILOT", "PRODUCTION"]
    asset_domain: Literal["IT", "OT", "MIXED"]
    connectivity: Literal["CONNECTED", "RESTRICTED", "AIR_GAPPED"]
    operating_model: Literal["SINGLE_ORG", "SOC_MSSP"]
    autonomy_mode: Literal["OBSERVE_ONLY", "ASSISTED", "CONTROLLED_AUTONOMY", "VALIDATION"]
    load_mode: Literal["NORMAL", "HIGH_LOAD", "EMERGENCY"]
    model_policy: Literal["LOCAL_ONLY", "HYBRID", "CLOUD_ALLOWED"]
    data_egress_policy: Literal["DENY", "REDACT_THEN_ALLOW", "ALLOW"]
    max_auto_risk: Risk
    active_validation: Literal["DISABLED", "ISOLATED_ONLY", "SCOPED_PREAPPROVED"]
    scope_ids: list[str]
    capability_allowlist: list[str]
    required_sensor_ids: list[str]
    policy_version: str
    owner_id: str

    @model_validator(mode="after")
    def constraints(self):
        if self.max_auto_risk == Risk.R5:
            raise ValueError("R5 cannot be preauthorized for automatic execution")
        if self.connectivity == "AIR_GAPPED" and (self.model_policy != "LOCAL_ONLY" or self.data_egress_policy != "DENY"):
            raise ValueError("air-gapped profile must use local-only model and deny egress")
        if self.deployment_stage == "PRODUCTION" and self.asset_domain in ("OT", "MIXED"):
            if self.autonomy_mode not in ("OBSERVE_ONLY", "ASSISTED") or self.active_validation != "DISABLED":
                raise ValueError("OT production profile defaults to passive; IT scopes require separate profiles")
        return self


class ResourceRef(Contract):
    """跨 OS / Cloud / K8s / Identity 的统一资源引用。locator 是定位信息，不是授权本身。"""
    object_type: Literal["ResourceRef"] = "ResourceRef"
    resource_id: str
    environment_id: str
    resource_type: Literal["NETWORK_ENDPOINT", "HOST", "IDENTITY", "KUBERNETES", "CLOUD", "SAAS", "SECURITY_CONTROL"]
    binding_version: int = Field(ge=1)
    locator: dict[str, Any]
    display_name: str | None = None

    @model_validator(mode="after")
    def locator_constraints(self):
        if self.resource_type == "NETWORK_ENDPOINT":
            required = {"address", "port", "protocol"}
            if not required.issubset(self.locator):
                raise ValueError("network endpoint requires address/port/protocol locator")
            if not 1 <= int(self.locator["port"]) <= 65535:
                raise ValueError("invalid network endpoint port")
            if self.locator["protocol"] not in ("TCP", "UDP"):
                raise ValueError("invalid network endpoint protocol")
        if self.resource_type == "IDENTITY" and not ({"object_id", "account_name"} & set(self.locator)):
            raise ValueError("identity requires object_id or account_name")
        if self.resource_type == "KUBERNETES" and not {"cluster_uid", "kind", "name"}.issubset(self.locator):
            raise ValueError("kubernetes resource requires cluster_uid/kind/name")
        if self.resource_type == "CLOUD" and not {"provider", "resource_id"}.issubset(self.locator):
            raise ValueError("cloud resource requires provider/resource_id")
        return self


class NetworkConstraint(Contract):
    source_resource_ids: list[str] = Field(min_length=1)
    target_resource_ids: list[str] = Field(min_length=1)
    destination_ports: list[int] = Field(min_length=1)
    protocols: list[Literal["TCP", "UDP"]] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_ports(self):
        if any(not 1 <= p <= 65535 for p in self.destination_ports):
            raise ValueError("invalid network constraint port")
        return self


class ScopeDefinition(Contract):
    object_type: Literal["ScopeDefinition"] = "ScopeDefinition"
    scope_id: str
    environment_id: str
    version: str
    source_resource_ids: list[str] = Field(min_length=1)
    target_resource_ids: list[str] = Field(min_length=1)
    capability_source_ids: dict[str, list[str]]
    allowed_capabilities: list[str] = Field(min_length=1)
    network_constraints: list[NetworkConstraint] = Field(default_factory=list)
    valid_from: AwareDatetime
    valid_until: AwareDatetime
    max_requests_per_second: float = Field(gt=0)

    @model_validator(mode="after")
    def constraints(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("invalid scope time")
        for cap, sources in self.capability_source_ids.items():
            if cap not in self.allowed_capabilities or not sources or not set(sources).issubset(self.source_resource_ids):
                raise ValueError("capability-specific source constraint must narrow declared scope")
        for nc in self.network_constraints:
            if not set(nc.source_resource_ids).issubset(self.source_resource_ids) or not set(nc.target_resource_ids).issubset(self.target_resource_ids):
                raise ValueError("network constraint must narrow declared resources")
        return self


class Observable(Contract):
    observable_type: Literal["IP", "DOMAIN", "URL", "HASH", "PROCESS", "USER", "FILE", "REGISTRY", "CLOUD_RESOURCE", "OTHER"]
    value: str
    role: Literal["SOURCE", "TARGET", "RELATED", "INDICATOR"] = "RELATED"


class NormalizedEvent(Contract):
    object_type: Literal["NormalizedEvent"] = "NormalizedEvent"
    event_id: str
    specversion: Literal["1.0"] = "1.0"
    environment_id: str
    source_type: str
    collector_id: str
    origin_event_id: str
    provenance_group: str
    source_timestamp: AwareDatetime
    ingested_at: AwareDatetime
    clock_status: Literal["TRUSTED", "SKEWED", "UNKNOWN"]
    event_type: str
    activity_category: str
    activity_name: str
    outcome: Literal["SUCCESS", "FAILURE", "UNKNOWN", "PARTIAL", "DENIED"]
    actor_resource_id: str | None = None
    source_resource_ids: list[str] = Field(default_factory=list)
    target_resource_ids: list[str] = Field(default_factory=list)
    observables: list[Observable] = Field(default_factory=list)
    severity_signal: int = Field(ge=0, le=10)
    raw_ref: str
    parser_version: str
    mapping_version: str
    fingerprint: str
    validation_run_id: str | None = None
    data_origin: Literal["SYNTHETIC", "OBSERVED"]


class EventGroup(Contract):
    object_type: Literal["EventGroup"] = "EventGroup"
    group_id: str
    environment_id: str
    first_seen_at: AwareDatetime
    last_seen_at: AwareDatetime
    member_event_ids: list[str] = Field(min_length=1)
    grouping_keys: dict[str, str]
    correlation_reasons: list[str] = Field(min_length=1)
    outlier_event_ids: list[str] = Field(default_factory=list)
    correlation_confidence: float = Field(ge=0, le=1)
    rule_version: str
    algorithm_version: str

    @model_validator(mode="after")
    def interval(self):
        if self.last_seen_at < self.first_seen_at:
            raise ValueError("invalid event group interval")
        if set(self.outlier_event_ids) & set(self.member_event_ids):
            raise ValueError("outliers cannot also be members")
        return self


class CorrelationDecision(Contract):
    object_type: Literal["CorrelationDecision"] = "CorrelationDecision"
    decision_id: str
    environment_id: str
    input_event_ids: list[str] = Field(min_length=1)
    output_group_id: str
    rules_fired: list[str] = Field(min_length=1)
    merge_reason: str
    excluded_event_ids: list[str] = Field(default_factory=list)
    decision_version: str
    created_at: AwareDatetime


class Evidence(Contract):
    object_type: Literal["Evidence"] = "Evidence"
    evidence_id: str
    environment_id: str
    incident_id: str
    source_event_ids: list[str]
    provenance_group: str
    claim_kind: Literal["OBSERVATION", "SOURCE_ASSERTION", "INFERENCE", "HUMAN_REVIEW"]
    observed_at: AwareDatetime
    collected_at: AwareDatetime
    valid_until: AwareDatetime
    content_ref: str
    integrity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    hash_algorithm: Literal["SHA256"] = "SHA256"
    collector_id: str
    collection_method: str
    trust_status: Literal["VERIFIED_ORIGIN", "UNVERIFIED_ORIGIN", "CONFLICTED"]
    supports: list[str]
    contradicts: list[str]
    data_origin: Literal["SYNTHETIC", "OBSERVED"]


class SensorHealth(Contract):
    object_type: Literal["SensorHealth"] = "SensorHealth"
    sensor_id: str
    environment_id: str
    status: Literal["HEALTHY", "DEGRADED", "OFFLINE", "UNKNOWN"]
    last_heartbeat_at: AwareDatetime
    last_event_at: AwareDatetime | None
    lag_seconds: float = Field(ge=0)
    lost_event_count: int = Field(ge=0)
    coverage_scope_ids: list[str]
    coverage_validated: bool
    config_version: str


class StateEntity(Contract):
    object_type: Literal["StateEntity"] = "StateEntity"
    entity_id: str
    environment_id: str
    entity_type: str
    state_version: int = Field(ge=1)
    attributes: dict[str, Any]
    claim_kind: Literal["OBSERVATION", "INFERENCE", "HUMAN_REVIEW"]
    evidence_ids: list[str]
    observed_at: AwareDatetime
    valid_until: AwareDatetime


class StateRelation(Contract):
    object_type: Literal["StateRelation"] = "StateRelation"
    relation_id: str
    environment_id: str
    source_entity_id: str
    destination_entity_id: str
    relation_type: str
    state_version: int = Field(ge=1)
    evidence_ids: list[str]
    valid_from: AwareDatetime
    valid_until: AwareDatetime


class SecurityIncident(Contract):
    object_type: Literal["SecurityIncident"] = "SecurityIncident"
    incident_id: str
    environment_id: str
    title: str
    status: IncidentStatus
    priority: Literal["P0", "P1", "P2", "P3", "P4"]
    affected_asset_ids: list[str]
    related_event_ids: list[str]
    event_group_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str]
    state_version: int = Field(ge=1)
    first_observed_at: AwareDatetime
    created_at: AwareDatetime
    updated_at: AwareDatetime
    triaged_at: AwareDatetime | None = None
    investigation_started_at: AwareDatetime | None = None
    contained_at: AwareDatetime | None = None
    resolved_at: AwareDatetime | None = None
    closed_at: AwareDatetime | None = None
    open_action_ids: list[str]
    residual_risks: list[str]
    closure_type: Literal["CLOSED_REMEDIATED", "CLOSED_FALSE_POSITIVE", "CLOSED_DUPLICATE", "CLOSED_ACCEPTED_RISK"] | None = None
    closure_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def constraints(self):
        if self.created_at < self.first_observed_at or self.updated_at < self.created_at:
            raise ValueError("incident timestamps are not monotonic")
        if self.status == IncidentStatus.CLOSED and (not self.closure_type or not self.closure_evidence_ids or not self.closed_at):
            raise ValueError("closed incident requires disposition, evidence and closed_at")
        if self.status != IncidentStatus.CLOSED and self.closure_type:
            raise ValueError("closure disposition only applies to closed incident")
        return self


class ContextBundle(Contract):
    object_type: Literal["ContextBundle"] = "ContextBundle"
    context_id: str
    environment_id: str
    incident_id: str
    state_version: int = Field(ge=1)
    evidence_ids: list[str]
    excluded_evidence_reasons: dict[str, str]
    unresolved_conflicts: list[str]
    sensor_health_ids: list[str]
    capability_ids: list[str]
    policy_version: str
    token_budget: int = Field(gt=0)
    data_classification: Literal["PUBLIC", "INTERNAL", "SENSITIVE", "RESTRICTED"]
    egress_allowed: bool
    summary_version: str
    prompt_version: str
    created_at: AwareDatetime


class WorkerLease(Contract):
    object_type: Literal["WorkerLease"] = "WorkerLease"
    lease_id: str
    task_id: str
    worker_id: str
    generation: int = Field(ge=1)
    acquired_at: AwareDatetime
    expires_at: AwareDatetime
    renewed_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def lease_time(self):
        if self.expires_at <= self.acquired_at:
            raise ValueError("lease expiry must follow acquisition")
        if self.renewed_at and self.renewed_at < self.acquired_at:
            raise ValueError("renewed_at cannot predate acquisition")
        return self


class Task(Contract):
    object_type: Literal["Task"] = "Task"
    task_id: str
    incident_id: str
    environment_id: str
    dependencies: list[str]
    capability_id: str
    capability_version: str
    target_resource_ids: list[str] = Field(min_length=1)
    scope_id: str
    parameters: dict[str, Any]
    status: TaskStatus
    priority: Literal["P0", "P1", "P2", "P3", "P4"]
    timeout_seconds: int = Field(gt=0)
    max_attempts: int = Field(ge=1, le=10)
    attempt_count: int = Field(ge=0, le=10)
    expected_output: str
    evidence_ids: list[str]
    created_at: AwareDatetime
    queued_at: AwareDatetime
    claimed_at: AwareDatetime | None = None
    started_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None
    active_lease_id: str | None = None
    worker_id: str | None = None


class Hypothesis(Contract):
    hypothesis_id: str
    claim: str
    evidence_ids: list[str]
    counter_evidence_ids: list[str]
    missing_evidence: list[str]
    model_confidence: float | None = Field(default=None, ge=0, le=1)
    calibration_status: Literal["UNCALIBRATED", "CALIBRATED"] = "UNCALIBRATED"


class AIPlan(Contract):
    object_type: Literal["AIPlan"] = "AIPlan"
    plan_id: str
    incident_id: str
    environment_id: str
    context_id: str
    model_run_id: str | None = None
    hypotheses: list[Hypothesis] = Field(min_length=1)
    tasks: list[Task] = Field(min_length=1)
    stop_conditions: list[str] = Field(min_length=1)
    max_replans: int = Field(ge=0)
    total_model_calls: int = Field(ge=0)

    @model_validator(mode="after")
    def dag(self):
        nodes = {t.task_id: t for t in self.tasks}
        if len(nodes) != len(self.tasks): raise ValueError("duplicate task id")
        visited, active = set(), set()
        def visit(key):
            if key not in nodes: raise ValueError("unknown task dependency")
            if key in active: raise ValueError("cyclic task graph")
            if key in visited: return
            active.add(key)
            for dep in nodes[key].dependencies: visit(dep)
            active.remove(key); visited.add(key)
        for t in self.tasks:
            if t.environment_id != self.environment_id or t.incident_id != self.incident_id:
                raise ValueError("cross-environment/incident task")
            visit(t.task_id)
        return self


class ModelRun(Contract):
    object_type: Literal["ModelRun"] = "ModelRun"
    run_id: str
    environment_id: str
    incident_id: str
    task_id: str | None
    provider: str
    model: str
    model_revision: str | None = None
    prompt_version: str
    context_id: str
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    route_reason: str
    fallback_from_run_id: str | None = None
    started_at: AwareDatetime
    finished_at: AwareDatetime
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    schema_valid: bool
    safety_status: Literal["PASS", "REJECTED", "DEGRADED"]


class CapabilityManifest(Contract):
    object_type: Literal["CapabilityManifest"] = "CapabilityManifest"
    capability_id: str
    version: str
    adapter: str
    base_risk: Risk
    operation_kind: Literal["PASSIVE_READ", "ACTIVE_CHECK", "STATE_CHANGE"]
    controller_location: str
    execution_location: str
    target_domain: str
    network_path: str
    cleanup_owner: str
    supported_os: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    scope_required: bool
    timeout_seconds: int = Field(gt=0)
    idempotency: Literal["NATIVE", "ADAPTER_RECONCILE", "NONE"]
    reconciliation_method: str
    ttl_enforcement: Literal["DEVICE", "SITE_DURABLE_WATCHDOG", "CONTROLLER_ONLY", "NONE"]
    rollback_policy: str
    required_permissions: list[str]
    required_secret_refs: list[str]
    supports_cancel: bool
    supports_dry_run: bool
    resource_locks: list[str]
    max_concurrency: int = Field(ge=1)
    expected_evidence_types: list[str]
    verification_capability_id: str | None = None
    compensator_capability_id: str | None = None
    integration_status: Literal["DESIGN", "ADAPTED", "LAB_VERIFIED", "PRODUCTION_VERIFIED"]


class CapabilityHealth(Contract):
    object_type: Literal["CapabilityHealth"] = "CapabilityHealth"
    capability_id: str
    capability_version: str
    environment_id: str
    worker_pool: str
    status: Literal["UNVERIFIED", "HEALTHY", "DEGRADED", "OFFLINE"]
    checked_at: AwareDatetime
    latency_ms: int | None = Field(default=None, ge=0)
    queue_depth: int = Field(ge=0)
    running_count: int = Field(ge=0)
    detail: str | None = None


class ActionRequest(Contract):
    object_type: Literal["ActionRequest"] = "ActionRequest"
    action_id: str
    incident_id: str
    task_id: str
    environment_id: str
    capability_id: str
    capability_version: str
    source: ResourceRef | None
    target: ResourceRef
    parameters: dict[str, Any]
    scope_id: str
    scope_version: str
    environment_profile_version: str
    policy_version: str
    expected_state_version: int = Field(ge=1)
    preconditions: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    created_at: AwareDatetime
    expires_at: AwareDatetime
    ttl_seconds: int = Field(ge=0)
    idempotency_key: str
    ownership_tag: str
    rollback_policy_id: str

    @model_validator(mode="after")
    def constraints(self):
        if self.expires_at <= self.created_at: raise ValueError("action expiry must follow creation")
        if self.target.environment_id != self.environment_id or (self.source and self.source.environment_id != self.environment_id):
            raise ValueError("action resource must belong to environment")
        return self


def action_digest(action: ActionRequest) -> str:
    body = json.dumps(action.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


class ApprovalRecord(Contract):
    object_type: Literal["ApprovalRecord"] = "ApprovalRecord"
    approval_id: str
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    actor_id: str
    actor_role: Literal["APPROVER", "ADMIN"]
    decision: Literal["APPROVED", "REJECTED"]
    reason: str
    policy_version: str
    approved_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def constraints(self):
        if self.expires_at <= self.approved_at: raise ValueError("approval has no valid time window")
        return self


class AuthorizationContext(Contract):
    object_type: Literal["AuthorizationContext"] = "AuthorizationContext"
    authorization_context_id: str
    environment_id: str
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    principal_id: str
    principal_role: str
    environment_profile_version: str
    scope_id: str
    scope_version: str
    capability_id: str
    capability_version: str
    target_resource_id: str
    source_resource_id: str | None
    asset_criticality: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    business_impact: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    evidence_quality: Literal["LOW", "MEDIUM", "HIGH"]
    sensor_health_status: Literal["HEALTHY", "DEGRADED", "UNKNOWN"]
    autonomy_mode: Literal["OBSERVE_ONLY", "ASSISTED", "CONTROLLED_AUTONOMY", "VALIDATION"]
    load_mode: Literal["NORMAL", "HIGH_LOAD", "EMERGENCY"]
    requested_risk: Risk
    policy_version: str
    budget_id: str
    created_at: AwareDatetime


class AuthorizationDecision(Contract):
    object_type: Literal["AuthorizationDecision"] = "AuthorizationDecision"
    authorization_id: str
    authorization_context_id: str
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL", "DOWNGRADE"]
    assessed_risk: Risk
    business_impact: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    human_approval_required: bool
    approval_id: str | None
    policy_version: str
    valid_until: AwareDatetime
    reasons: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def constraints(self):
        high = self.assessed_risk == Risk.R5 or self.business_impact in ("HIGH", "CRITICAL")
        if high and not self.human_approval_required: raise ValueError("high impact cannot bypass human approval")
        if self.outcome == "ALLOW" and self.human_approval_required and not self.approval_id: raise ValueError("allow requires approval reference")
        return self


class ActionAttempt(Contract):
    object_type: Literal["ActionAttempt"] = "ActionAttempt"
    attempt_id: str
    action_id: str
    status: ActionStatus
    fencing_generation: int = Field(ge=1)
    worker_id: str
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    device_receipt_id: str | None
    reconciliation_state: Literal["NOT_NEEDED", "PENDING", "CONFIRMED_APPLIED", "CONFIRMED_NOT_APPLIED", "PARTIAL", "UNKNOWN"]
    evidence_ids: list[str]
    error_code: str | None = None
    error_class: str | None = None
    device_response_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class AssertionSpec(Contract):
    field: str
    operator: Literal["EQUALS", "NOT_EQUALS", "IN", "NOT_IN", "LT", "LTE", "GT", "GTE", "EXISTS", "NOT_EXISTS", "MATCHES"]
    expected: Any | None = None


class VerificationCheckSpec(Contract):
    check_id: str
    dimension: Literal["SECURITY", "BUSINESS", "OBSERVATION"]
    capability_id: str
    source_resource_id: str | None = None
    target_resource_id: str
    timeout_seconds: int = Field(gt=0)
    repetitions: int = Field(ge=1, le=20)
    assertions: list[AssertionSpec] = Field(min_length=1)
    required_sensor_ids: list[str] = Field(default_factory=list)
    executor_must_differ_from_action_executor: bool = True
    on_missing_observation: Literal["INCONCLUSIVE", "FAIL"] = "INCONCLUSIVE"


class VerificationSpec(Contract):
    object_type: Literal["VerificationSpec"] = "VerificationSpec"
    verification_spec_id: str
    scenario_id: str
    scenario_version: str
    objective_type: Literal["DETECTION", "CONTAINMENT", "REMEDIATION", "RECOVERY", "CLEANUP"]
    checks: list[VerificationCheckSpec] = Field(min_length=3)
    aggregation_rule: Literal["THREE_DIMENSION_STRICT"] = "THREE_DIMENSION_STRICT"

    @model_validator(mode="after")
    def three_dimensions(self):
        if {c.dimension for c in self.checks} != {"SECURITY", "BUSINESS", "OBSERVATION"}:
            raise ValueError("verification spec requires security, business and observation checks")
        return self


def expected_verdict(security: Verdict | str, business: Verdict | str, observation: Verdict | str) -> Verdict:
    if security == "FAIL" or business == "FAIL": return Verdict.FAIL
    if security == "PASS" and business == "PASS" and observation == "PASS": return Verdict.PASS
    return Verdict.INCONCLUSIVE


class VerificationResult(Contract):
    object_type: Literal["VerificationResult"] = "VerificationResult"
    verification_id: str
    verification_spec_id: str
    incident_id: str
    environment_id: str
    action_id: str | None
    validation_run_id: str
    objective_type: Literal["DETECTION", "CONTAINMENT", "REMEDIATION", "RECOVERY", "CLEANUP"]
    claim: str
    target_ids: list[str] = Field(min_length=1)
    scope_id: str
    scenario_version: str
    started_at: AwareDatetime
    finished_at: AwareDatetime
    valid_until: AwareDatetime
    security_status: Verdict
    business_status: Verdict
    observation_status: Verdict
    status: Verdict
    evidence_ids: list[str] = Field(min_length=1)
    expected_result: str
    observed_result: str
    residual_risks: list[str]
    recommended_next_step: str

    @model_validator(mode="after")
    def constraints(self):
        if self.finished_at < self.started_at or self.valid_until < self.finished_at: raise ValueError("invalid verification time interval")
        if self.status != expected_verdict(self.security_status, self.business_status, self.observation_status):
            raise ValueError("overall verdict violates three-check semantics")
        return self


class ValidationScenario(Contract):
    object_type: Literal["ValidationScenario"] = "ValidationScenario"
    scenario_id: str
    version: str
    implementation_status: Literal["DESIGN_ONLY", "LAB_VERIFIED"]
    objective: str
    environment_id: str
    scope_id: str
    preconditions: list[str]
    trigger_steps: list[str]
    expected_events: list[str]
    verification_spec_id: str
    cleanup_steps: list[str]
    stop_conditions: list[str]
    config_is_measured_performance: Literal[False] = False


class ValidationRun(Contract):
    object_type: Literal["ValidationRun"] = "ValidationRun"
    run_id: str
    scenario_id: str
    scenario_version: str
    environment_id: str
    scope_id: str
    registered_by: str
    trusted_registration: bool
    started_at: AwareDatetime
    expires_at: AwareDatetime
    expected_event_types: list[str]
    allowed_side_effects: list[str]
    cleanup_policy_id: str
    data_origin: Literal["SYNTHETIC", "OBSERVED"]


class PolicySnapshot(Contract):
    object_type: Literal["PolicySnapshot"] = "PolicySnapshot"
    policy_id: str
    version: str
    environment_id: str
    high_impact_requires_human: Literal[True] = True
    r5_auto_allowed: Literal[False] = False
    load_can_expand_permissions: Literal[False] = False
    allowed_capability_ids: list[str]
    valid_until: AwareDatetime
    max_replans: int = Field(ge=0)
    max_model_calls: int = Field(ge=1)
    max_active_calls: int = Field(ge=1)
    max_elapsed_seconds: int = Field(ge=1)


class AuditEntry(Contract):
    object_type: Literal["AuditEntry"] = "AuditEntry"
    audit_id: str
    trace_id: str
    environment_id: str
    actor_type: Literal["HUMAN", "SERVICE", "MODEL", "WORKER"]
    actor_id: str
    object_kind: str
    object_id: str
    operation: str
    reason: str
    timestamp: AwareDatetime
    previous_entry_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    integrity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class OutboxMessage(Contract):
    object_type: Literal["OutboxMessage"] = "OutboxMessage"
    message_id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload_ref: str
    created_at: AwareDatetime
    published_at: AwareDatetime | None = None
    attempt_count: int = Field(ge=0)


CONTRACTS = {c.__name__: c for c in (
    EnvironmentProfile, ResourceRef, ScopeDefinition, NormalizedEvent, EventGroup, CorrelationDecision,
    Evidence, SensorHealth, StateEntity, StateRelation, SecurityIncident, ContextBundle, WorkerLease,
    Task, AIPlan, ModelRun, CapabilityManifest, CapabilityHealth, ActionRequest, ApprovalRecord,
    AuthorizationContext, AuthorizationDecision, ActionAttempt, VerificationSpec, VerificationResult,
    ValidationScenario, ValidationRun, PolicySnapshot, AuditEntry, OutboxMessage,
)}
