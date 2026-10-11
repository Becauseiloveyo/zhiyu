"""SQL column allowlist. Sensitive payload columns are never fetched by projections."""

import re
from datetime import datetime
from typing import Any, Literal

from zhiyu.db import (
    ai_analysis,
    ai_context,
    ai_decisions,
    ai_gateway,
    ai_planning,
    infrastructure,
    intelligence,
    models,
    response_authority,
    response_execution,
    response_planning,
    verification_replan,
    verification_runtime,
)
from zhiyu.product.contracts import Fact

# kind -> (ORM model, identifier field, explicitly public fields).
SPECS: dict[str, tuple[Any, str, str]] = {
    "incident": (
        models.IncidentRow,
        "incident_id",
        "title status priority affected_asset_ids state_version first_observed_at created_at updated_at triaged_at investigation_started_at contained_at resolved_at closed_at closure_type",
    ),
    "resource": (models.ResourceRow, "resource_id", "resource_type binding_version display_name"),
    "event": (
        models.EventRow,
        "event_id",
        "source_type collector_id provenance_group source_timestamp ingested_at clock_status event_type activity_category activity_name outcome actor_resource_id source_resource_ids target_resource_ids severity_signal parser_version mapping_version data_origin content_hash",
    ),
    "event_resource": (infrastructure.EventResourceRow, "event_id", "resource_id role"),
    "raw": (infrastructure.RawRecordRow, "raw_id", "collector_id source_type integrity_hash received_at"),
    "normalization": (
        infrastructure.RawDeliveryRow,
        "delivery_id",
        "raw_id event_id disposition error_code created_at",
    ),
    "group": (
        models.EventGroupRow,
        "group_id",
        "first_seen_at last_seen_at member_event_ids outlier_event_ids rule_version algorithm_version",
    ),
    "correlation": (
        models.CorrelationDecisionRow,
        "decision_id",
        "input_event_ids output_group_id excluded_event_ids decision_version created_at",
    ),
    "evidence": (
        models.EvidenceRow,
        "evidence_id",
        "incident_id source_event_ids provenance_group claim_kind observed_at collected_at valid_until integrity_hash hash_algorithm collector_id collection_method trust_status data_origin",
    ),
    "context": (
        models.ContextRow,
        "context_id",
        "incident_id state_version evidence_ids policy_version data_classification egress_allowed summary_version prompt_version created_at",
    ),
    "ai_context": (
        ai_context.DecisionContextRow,
        "context_id",
        "incident_id snapshot_id scope_id context_hash created_at valid_until",
    ),
    "model_request": (
        ai_gateway.ModelRequestRow,
        "request_id",
        "incident_id context_id task_type routing_version status started_at lease_until",
    ),
    "model_receipt": (
        ai_gateway.ModelReceiptRow,
        "request_id",
        "model_run_id status error_code usage_known completed_at provider_ms",
    ),
    "model_run": (
        models.ModelRunRow,
        "run_id",
        "incident_id context_id provider model model_revision prompt_version input_hash output_hash started_at finished_at input_tokens output_tokens latency_ms schema_valid safety_status",
    ),
    "analysis": (
        ai_analysis.SituationAnalysisRow,
        "analysis_id",
        "incident_id context_id request_id model_run_id state_entity_id status grounding created_at",
    ),
    "proposal": (
        ai_planning.AIProposalRow,
        "proposal_id",
        "incident_id incident_version context_id analysis_id request_id model_run_id parent_verification_id plan_id mode status validation created_at",
    ),
    "decision": (ai_decisions.AIDecisionRow, "context_id", "incident_id status plan_id created_at"),
    "plan": (
        response_planning.ResponsePlanRow,
        "plan_id",
        "incident_id incident_version planner_version policy_version scope_id snapshot_hash created_at",
    ),
    "task": (
        models.TaskRow,
        "task_id",
        "incident_id capability_id capability_version target_resource_ids scope_id status priority attempt_count created_at queued_at claimed_at started_at finished_at",
    ),
    "action": (
        models.ActionRow,
        "action_id",
        "incident_id task_id capability_id capability_version scope_id scope_version policy_version expected_state_version evidence_ids created_at expires_at action_digest",
    ),
    "authorization_context": (
        models.AuthorizationContextRow,
        "authorization_context_id",
        "action_id action_digest scope_id scope_version asset_criticality business_impact evidence_quality sensor_health_status autonomy_mode load_mode requested_risk policy_version created_at",
    ),
    "authorization": (
        models.AuthorizationDecisionRow,
        "authorization_id",
        "authorization_context_id action_id action_digest outcome assessed_risk business_impact human_approval_required approval_id policy_version valid_until reasons",
    ),
    "risk": (
        response_authority.AuthorizationSnapshotRow,
        "context_id",
        "action_id rule_id denied_dimensions created_at",
    ),
    "approval": (
        models.ApprovalRow,
        "approval_id",
        "action_id action_digest actor_role decision reason policy_version approved_at expires_at",
    ),
    "attempt": (
        models.ActionAttemptRow,
        "attempt_id",
        "action_id status started_at finished_at reconciliation_state evidence_ids error_code error_class device_response_hash",
    ),
    "result": (
        response_execution.ActionResultRow,
        "attempt_id",
        "execution_outcome executor executor_version started_at completed_at output_hash error_code retryable side_effect",
    ),
    "verification_spec": (
        verification_runtime.VerificationRuntimeRow,
        "spec_id",
        "incident_id plan_id task_id action_id action_result_id scope_id spec_hash created_at valid_until",
    ),
    "check": (verification_runtime.VerificationCheckRow, "check_id", "spec_id status generation started_at"),
    "observation": (
        verification_runtime.VerificationObservationRow,
        "evidence_id",
        "spec_id check_id execution_status assertion_status assertions reason executor_version started_at checked_at",
    ),
    "verification": (
        models.VerificationResultRow,
        "verification_id",
        "incident_id verification_spec_id action_id objective_type claim target_ids scope_id started_at finished_at valid_until security_status business_status observation_status status evidence_ids recommended_next_step",
    ),
    "state_update": (
        verification_replan.VerificationStateUpdateRow,
        "verification_id",
        "entity_ids updated_at",
    ),
    "state": (
        models.StateEntityRow,
        "entity_id",
        "entity_type state_version claim_kind evidence_ids observed_at valid_until",
    ),
    "state_relation": (
        models.StateRelationRow,
        "relation_id",
        "source_entity_id destination_entity_id relation_type state_version evidence_ids valid_from valid_until",
    ),
    "replan": (
        verification_replan.ReplanDecisionRow,
        "verification_id",
        "root_plan_id parent_plan_id new_plan_id status reason replan_count policy_version created_at",
    ),
    "audit": (
        models.AuditEntryRow,
        "audit_id",
        "object_kind object_id operation timestamp integrity_hash sequence",
    ),
    "group_member": (intelligence.GroupMemberRow, "event_id", "group_id added_at"),
}

_SECRET = re.compile(
    r"(?i)(?:bearer\s+\S+|(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[^\s,;]+|(?:postgres(?:ql)?|https?)://[^\s/@]+:[^\s/@]+@[^\s]+|\bsk-[a-z0-9_-]{12,})"
)
_NESTED_KEYS = frozenset(
    {
        "accepted",
        "valid",
        "reasons",
        "status",
        "reason",
        "code",
        "rule_id",
        "claim_kind",
        "confidence_semantics",
        "assertion_id",
        "check_id",
        "dimension",
        "operator",
        "expected",
        "actual",
        "passed",
        "field",
        "required",
        "observed",
        "hallucination_count",
        "reference_grounded",
        "semantic_correctness_validated",
        "claim",
        "missing_evidence",
        "model_confidence",
    }
)


def public_value(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "[OMITTED]"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return _SECRET.sub("[REDACTED]", value[:1024])
    if isinstance(value, dict):
        return {k: public_value(v, depth + 1) for k, v in value.items() if k in _NESTED_KEYS}
    if isinstance(value, (list, tuple)):
        return [public_value(v, depth + 1) for v in value[:40]]
    return value


def columns(kind: str) -> list[Any]:
    model, identifier, fields = SPECS[kind]
    result = [getattr(model, name) for name in [identifier, *fields.split()]]
    if kind == "analysis":
        result += [
            model.output["incident_summary"].as_string().label("incident_summary"),
            model.output["uncertainty"].as_string().label("uncertainty"),
            model.output["hypotheses"].label("hypotheses"),
        ]
    if kind == "proposal":
        result += [
            model.output["objective"].as_string().label("objective"),
            model.output["reasoning_summary"].as_string().label("reasoning_summary"),
        ]
    return result


def fact(kind: str, row: Any, environment: str, as_of: datetime) -> Fact:
    values = dict(row)
    if kind in {"analysis", "proposal"} and values.get("status") in {"REJECTED", "FALLBACK"}:
        for field in ("incident_summary", "uncertainty", "hypotheses", "objective", "reasoning_summary"):
            values.pop(field, None)
    identifier = str(values.pop(SPECS[kind][1]))
    if kind == "check":
        identifier = str(values["spec_id"]) + ":" + identifier
    if kind == "event_resource":
        identifier += ":" + str(values["role"]) + ":" + str(values["resource_id"])
    until = values.get("valid_until", values.get("expires_at"))
    freshness: Literal["UNKNOWN", "EXPIRED", "CURRENT"] = (
        "UNKNOWN" if not until else "EXPIRED" if until <= as_of else "CURRENT"
    )
    observed = values.get("observed_at", values.get("valid_from", values.get("started_at")))
    if observed and observed > as_of:
        freshness = "UNKNOWN"
    basis: Literal["OBSERVED", "DERIVED", "MODEL_INFERENCE", "UNKNOWN"] = (
        "MODEL_INFERENCE" if kind in {"analysis", "proposal"} else "DERIVED"
    )
    if kind in {"raw", "event", "evidence", "observation", "state"}:
        basis = "DERIVED" if values.get("claim_kind") == "INFERENCE" else "OBSERVED"
    if values.get("claim_kind") == "SOURCE_ASSERTION":
        basis = "UNKNOWN"
    if values.get("entity_type") == "AI_SITUATION_ANALYSIS":
        basis = "MODEL_INFERENCE"
    fields = {key: public_value(value) for key, value in values.items()}
    clipped = [
        k
        for k, v in values.items()
        if (isinstance(v, str) and len(v) > 1024) or (isinstance(v, list) and len(v) > 40)
    ]
    if clipped:
        fields["display_truncated_fields"] = clipped
    if kind in {"analysis", "proposal"}:
        fields["semantic_correctness"] = "NOT_VALIDATED"
        fields["confidence_semantics"] = "MODEL_SELF_REPORTED_UNCALIBRATED"
    return Fact(
        ref=f"{kind}:{environment}:{identifier}",
        kind=kind,
        id=identifier,
        fields=fields,
        basis=basis,
        freshness=freshness,
    )
