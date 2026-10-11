"""Explicit PostgreSQL persistence for ai.5. Nested values use JSONB; no duplicate body column.

Runtime business/state-machine guards belong to services, not these mappings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db.base import Base, Versioned


class EnvironmentRow(Versioned, Base):
    __tablename__ = "environments"
    environment_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    deployment_stage: Mapped[str] = mapped_column(Text, nullable=False)
    asset_domain: Mapped[str] = mapped_column(Text, nullable=False)
    connectivity: Mapped[str] = mapped_column(Text, nullable=False)
    operating_model: Mapped[str] = mapped_column(Text, nullable=False)
    autonomy_mode: Mapped[str] = mapped_column(Text, nullable=False)
    load_mode: Mapped[str] = mapped_column(Text, nullable=False)
    model_policy: Mapped[str] = mapped_column(Text, nullable=False)
    data_egress_policy: Mapped[str] = mapped_column(Text, nullable=False)
    max_auto_risk: Mapped[str] = mapped_column(Text, nullable=False)
    active_validation: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    capability_allowlist: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    required_sensor_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    __table_args__ = (
        CheckConstraint("max_auto_risk <> 'R5'", name="environment_not_auto_r5"),
        CheckConstraint(
            "connectivity <> 'AIR_GAPPED' OR (model_policy = 'LOCAL_ONLY' AND data_egress_policy = 'DENY')",
            name="airgap_egress",
        ),
        CheckConstraint(
            "deployment_stage <> 'PRODUCTION' OR asset_domain = 'IT' OR (autonomy_mode IN ('OBSERVE_ONLY','ASSISTED') AND active_validation = 'DISABLED')",
            name="ot_production_passive",
        ),
        CheckConstraint("length(environment_id) > 0", name="environments_environment_id_nonempty"),
        CheckConstraint(
            "deployment_stage IN ('LAB', 'PILOT', 'PRODUCTION')", name="environments_deployment_stage_enum"
        ),
        CheckConstraint("asset_domain IN ('IT', 'OT', 'MIXED')", name="environments_asset_domain_enum"),
        CheckConstraint(
            "connectivity IN ('CONNECTED', 'RESTRICTED', 'AIR_GAPPED')", name="environments_connectivity_enum"
        ),
        CheckConstraint(
            "operating_model IN ('SINGLE_ORG', 'SOC_MSSP')", name="environments_operating_model_enum"
        ),
        CheckConstraint(
            "autonomy_mode IN ('OBSERVE_ONLY', 'ASSISTED', 'CONTROLLED_AUTONOMY', 'VALIDATION')",
            name="environments_autonomy_mode_enum",
        ),
        CheckConstraint(
            "load_mode IN ('NORMAL', 'HIGH_LOAD', 'EMERGENCY')", name="environments_load_mode_enum"
        ),
        CheckConstraint(
            "model_policy IN ('LOCAL_ONLY', 'HYBRID', 'CLOUD_ALLOWED')", name="environments_model_policy_enum"
        ),
        CheckConstraint(
            "data_egress_policy IN ('DENY', 'REDACT_THEN_ALLOW', 'ALLOW')",
            name="environments_data_egress_policy_enum",
        ),
        CheckConstraint(
            "max_auto_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')", name="environments_max_auto_risk_enum"
        ),
        CheckConstraint(
            "active_validation IN ('DISABLED', 'ISOLATED_ONLY', 'SCOPED_PREAPPROVED')",
            name="environments_active_validation_enum",
        ),
        CheckConstraint("jsonb_typeof(scope_ids) = 'array'", name="environments_scope_ids_json"),
        CheckConstraint(
            "jsonb_typeof(capability_allowlist) = 'array'", name="environments_capability_allowlist_json"
        ),
        CheckConstraint(
            "jsonb_typeof(required_sensor_ids) = 'array'", name="environments_required_sensor_ids_json"
        ),
        CheckConstraint("row_version >= 1", name="environments_row_version"),
    )


class ResourceRow(Versioned, Base):
    __tablename__ = "resources"
    resource_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    binding_version: Mapped[int] = mapped_column(Integer, nullable=False)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_resources_environment"
        ),
        CheckConstraint(
            "(resource_type <> 'NETWORK_ENDPOINT' OR (locator ?& ARRAY['address','port','protocol'] AND (locator->>'port')::integer BETWEEN 1 AND 65535 AND locator->>'protocol' IN ('TCP','UDP'))) AND (resource_type <> 'IDENTITY' OR locator ?| ARRAY['object_id','account_name']) AND (resource_type <> 'KUBERNETES' OR locator ?& ARRAY['cluster_uid','kind','name']) AND (resource_type <> 'CLOUD' OR locator ?& ARRAY['provider','resource_id'])",
            name="resource_locator_required",
        ),
        Index("ix_resources_type", "environment_id", "resource_type"),
        CheckConstraint("length(resource_id) > 0", name="resources_resource_id_nonempty"),
        CheckConstraint("length(environment_id) > 0", name="resources_environment_id_nonempty"),
        CheckConstraint(
            "resource_type IN ('NETWORK_ENDPOINT', 'HOST', 'IDENTITY', 'KUBERNETES', 'CLOUD', 'SAAS', 'SECURITY_CONTROL')",
            name="resources_resource_type_enum",
        ),
        CheckConstraint("binding_version >= 1", name="resources_binding_version_minimum"),
        CheckConstraint("jsonb_typeof(locator) = 'object'", name="resources_locator_json"),
        CheckConstraint("row_version >= 1", name="resources_row_version"),
    )


class ScopeRow(Versioned, Base):
    __tablename__ = "scopes"
    scope_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    source_resource_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    target_resource_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    capability_source_ids: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    allowed_capabilities: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    network_constraints: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_requests_per_second: Mapped[float] = mapped_column(Float, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_scopes_environment"
        ),
        CheckConstraint("valid_until > valid_from", name="scope_interval"),
        Index("ix_scopes_expiry", "environment_id", "valid_until"),
        CheckConstraint("length(scope_id) > 0", name="scopes_scope_id_nonempty"),
        CheckConstraint("length(environment_id) > 0", name="scopes_environment_id_nonempty"),
        CheckConstraint(
            "jsonb_typeof(source_resource_ids) = 'array'", name="scopes_source_resource_ids_json"
        ),
        CheckConstraint(
            "jsonb_array_length(source_resource_ids) >= 1", name="scopes_source_resource_ids_minitems"
        ),
        CheckConstraint(
            "jsonb_typeof(target_resource_ids) = 'array'", name="scopes_target_resource_ids_json"
        ),
        CheckConstraint(
            "jsonb_array_length(target_resource_ids) >= 1", name="scopes_target_resource_ids_minitems"
        ),
        CheckConstraint(
            "jsonb_typeof(capability_source_ids) = 'object'", name="scopes_capability_source_ids_json"
        ),
        CheckConstraint(
            "jsonb_typeof(allowed_capabilities) = 'array'", name="scopes_allowed_capabilities_json"
        ),
        CheckConstraint(
            "jsonb_array_length(allowed_capabilities) >= 1", name="scopes_allowed_capabilities_minitems"
        ),
        CheckConstraint(
            "jsonb_typeof(network_constraints) = 'array'", name="scopes_network_constraints_json"
        ),
        CheckConstraint(
            "max_requests_per_second > 0", name="scopes_max_requests_per_second_exclusiveMinimum"
        ),
        CheckConstraint("row_version >= 1", name="scopes_row_version"),
    )


class EventRow(Base):
    __tablename__ = "normalized_events"
    event_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    specversion: Mapped[str] = mapped_column(Text, nullable=False)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    collector_id: Mapped[str] = mapped_column(Text, nullable=False)
    origin_event_id: Mapped[str] = mapped_column(Text, nullable=False)
    provenance_group: Mapped[str] = mapped_column(Text, nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clock_status: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    activity_category: Mapped[str] = mapped_column(Text, nullable=False)
    activity_name: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    actor_resource_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_resource_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    target_resource_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    observables: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    severity_signal: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_ref: Mapped[str] = mapped_column(Text, nullable=False)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False)
    mapping_version: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    validation_run_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_origin: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint("specversion = '1.0'", name="event_specversion"),
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_normalized_events_environment"
        ),
        UniqueConstraint("environment_id", "event_id", name="uq_normalized_events_environment_id"),
        UniqueConstraint(
            "environment_id",
            "collector_id",
            "source_type",
            "origin_event_id",
            "event_type",
            name="uq_event_origin",
        ),
        ForeignKeyConstraint(
            ["environment_id", "actor_resource_id"],
            ["resources.environment_id", "resources.resource_id"],
            name="fk_event_actor",
        ),
        ForeignKeyConstraint(
            ["environment_id", "validation_run_id"],
            ["validation_runs.environment_id", "validation_runs.run_id"],
            name="fk_event_run",
        ),
        Index("ix_events_env_time", "environment_id", "source_timestamp"),
        Index("ix_events_provenance", "environment_id", "provenance_group"),
        Index("ix_events_fingerprint", "environment_id", "fingerprint"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="event_hash"),
        CheckConstraint("length(event_id) > 0", name="normalized_events_event_id_nonempty"),
        CheckConstraint(
            "clock_status IN ('TRUSTED', 'SKEWED', 'UNKNOWN')", name="normalized_events_clock_status_enum"
        ),
        CheckConstraint(
            "outcome IN ('SUCCESS', 'FAILURE', 'UNKNOWN', 'PARTIAL', 'DENIED')",
            name="normalized_events_outcome_enum",
        ),
        CheckConstraint(
            "jsonb_typeof(source_resource_ids) = 'array'", name="normalized_events_source_resource_ids_json"
        ),
        CheckConstraint(
            "jsonb_typeof(target_resource_ids) = 'array'", name="normalized_events_target_resource_ids_json"
        ),
        CheckConstraint("jsonb_typeof(observables) = 'array'", name="normalized_events_observables_json"),
        CheckConstraint("severity_signal >= 0", name="normalized_events_severity_signal_minimum"),
        CheckConstraint("severity_signal <= 10", name="normalized_events_severity_signal_maximum"),
        CheckConstraint(
            "data_origin IN ('SYNTHETIC', 'OBSERVED')", name="normalized_events_data_origin_enum"
        ),
    )


class EventGroupRow(Base):
    __tablename__ = "event_groups"
    group_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    member_event_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    grouping_keys: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    correlation_reasons: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    outlier_event_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    correlation_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rule_version: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_event_groups_environment"
        ),
        UniqueConstraint("environment_id", "group_id", name="uq_event_groups_environment_id"),
        CheckConstraint("last_seen_at >= first_seen_at", name="group_interval"),
        CheckConstraint("length(group_id) > 0", name="event_groups_group_id_nonempty"),
        CheckConstraint(
            "jsonb_typeof(member_event_ids) = 'array'", name="event_groups_member_event_ids_json"
        ),
        CheckConstraint(
            "jsonb_array_length(member_event_ids) >= 1", name="event_groups_member_event_ids_minitems"
        ),
        CheckConstraint("jsonb_typeof(grouping_keys) = 'object'", name="event_groups_grouping_keys_json"),
        CheckConstraint(
            "jsonb_typeof(correlation_reasons) = 'array'", name="event_groups_correlation_reasons_json"
        ),
        CheckConstraint(
            "jsonb_array_length(correlation_reasons) >= 1", name="event_groups_correlation_reasons_minitems"
        ),
        CheckConstraint(
            "jsonb_typeof(outlier_event_ids) = 'array'", name="event_groups_outlier_event_ids_json"
        ),
        CheckConstraint("correlation_confidence >= 0", name="event_groups_correlation_confidence_minimum"),
        CheckConstraint("correlation_confidence <= 1", name="event_groups_correlation_confidence_maximum"),
    )


class CorrelationDecisionRow(Base):
    __tablename__ = "correlation_decisions"
    decision_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    input_event_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    output_group_id: Mapped[str] = mapped_column(Text, nullable=False)
    rules_fired: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    merge_reason: Mapped[str] = mapped_column(Text, nullable=False)
    excluded_event_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    decision_version: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_correlation_decisions_environment"
        ),
        UniqueConstraint("environment_id", "decision_id", name="uq_correlation_decisions_environment_id"),
        ForeignKeyConstraint(
            ["environment_id", "output_group_id"],
            ["event_groups.environment_id", "event_groups.group_id"],
            name="fk_correlation_group",
        ),
        CheckConstraint("length(decision_id) > 0", name="correlation_decisions_decision_id_nonempty"),
        CheckConstraint(
            "jsonb_typeof(input_event_ids) = 'array'", name="correlation_decisions_input_event_ids_json"
        ),
        CheckConstraint(
            "jsonb_array_length(input_event_ids) >= 1", name="correlation_decisions_input_event_ids_minitems"
        ),
        CheckConstraint("jsonb_typeof(rules_fired) = 'array'", name="correlation_decisions_rules_fired_json"),
        CheckConstraint(
            "jsonb_array_length(rules_fired) >= 1", name="correlation_decisions_rules_fired_minitems"
        ),
        CheckConstraint(
            "jsonb_typeof(excluded_event_ids) = 'array'", name="correlation_decisions_excluded_event_ids_json"
        ),
    )


class EvidenceRow(Base):
    __tablename__ = "evidence"
    evidence_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    incident_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_event_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    provenance_group: Mapped[str] = mapped_column(Text, nullable=False)
    claim_kind: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_ref: Mapped[str] = mapped_column(Text, nullable=False)
    integrity_hash: Mapped[str] = mapped_column(Text, nullable=False)
    hash_algorithm: Mapped[str] = mapped_column(Text, nullable=False)
    collector_id: Mapped[str] = mapped_column(Text, nullable=False)
    collection_method: Mapped[str] = mapped_column(Text, nullable=False)
    trust_status: Mapped[str] = mapped_column(Text, nullable=False)
    supports: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    contradicts: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    data_origin: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint("hash_algorithm = 'SHA256'", name="evidence_hash_algorithm"),
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_evidence_environment"
        ),
        UniqueConstraint("environment_id", "evidence_id", name="uq_evidence_environment_id"),
        UniqueConstraint("environment_id", "incident_id", "evidence_id", name="uq_evidence_incident_owner"),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_evidence_incident",
        ),
        Index("ix_evidence_incident_time", "incident_id", "observed_at"),
        CheckConstraint("length(evidence_id) > 0", name="evidence_evidence_id_nonempty"),
        CheckConstraint("jsonb_typeof(source_event_ids) = 'array'", name="evidence_source_event_ids_json"),
        CheckConstraint(
            "claim_kind IN ('OBSERVATION', 'SOURCE_ASSERTION', 'INFERENCE', 'HUMAN_REVIEW')",
            name="evidence_claim_kind_enum",
        ),
        CheckConstraint("integrity_hash ~ '^[0-9a-f]{64}$'", name="evidence_integrity_hash_pattern"),
        CheckConstraint(
            "trust_status IN ('VERIFIED_ORIGIN', 'UNVERIFIED_ORIGIN', 'CONFLICTED')",
            name="evidence_trust_status_enum",
        ),
        CheckConstraint("jsonb_typeof(supports) = 'array'", name="evidence_supports_json"),
        CheckConstraint("jsonb_typeof(contradicts) = 'array'", name="evidence_contradicts_json"),
        CheckConstraint("data_origin IN ('SYNTHETIC', 'OBSERVED')", name="evidence_data_origin_enum"),
    )


class SensorHealthRow(Versioned, Base):
    __tablename__ = "sensor_health"
    sensor_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lag_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    lost_event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_scope_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    coverage_validated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    config_version: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_sensor_health_environment"
        ),
        CheckConstraint("length(sensor_id) > 0", name="sensor_health_sensor_id_nonempty"),
        CheckConstraint("length(environment_id) > 0", name="sensor_health_environment_id_nonempty"),
        CheckConstraint(
            "status IN ('HEALTHY', 'DEGRADED', 'OFFLINE', 'UNKNOWN')", name="sensor_health_status_enum"
        ),
        CheckConstraint("lag_seconds >= 0", name="sensor_health_lag_seconds_minimum"),
        CheckConstraint("lost_event_count >= 0", name="sensor_health_lost_event_count_minimum"),
        CheckConstraint(
            "jsonb_typeof(coverage_scope_ids) = 'array'", name="sensor_health_coverage_scope_ids_json"
        ),
        CheckConstraint("row_version >= 1", name="sensor_health_row_version"),
    )


class StateEntityRow(Versioned, Base):
    __tablename__ = "state_entities"
    entity_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    claim_kind: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_state_entities_environment"
        ),
        CheckConstraint("length(entity_id) > 0", name="state_entities_entity_id_nonempty"),
        CheckConstraint("length(environment_id) > 0", name="state_entities_environment_id_nonempty"),
        CheckConstraint("state_version >= 1", name="state_entities_state_version_minimum"),
        CheckConstraint("jsonb_typeof(attributes) = 'object'", name="state_entities_attributes_json"),
        CheckConstraint(
            "claim_kind IN ('OBSERVATION', 'INFERENCE', 'HUMAN_REVIEW')",
            name="state_entities_claim_kind_enum",
        ),
        CheckConstraint("jsonb_typeof(evidence_ids) = 'array'", name="state_entities_evidence_ids_json"),
        CheckConstraint("row_version >= 1", name="state_entities_row_version"),
    )


class StateRelationRow(Versioned, Base):
    __tablename__ = "state_relations"
    relation_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    source_entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    destination_entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    relation_type: Mapped[str] = mapped_column(Text, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_state_relations_environment"
        ),
        ForeignKeyConstraint(
            ["environment_id", "source_entity_id"],
            ["state_entities.environment_id", "state_entities.entity_id"],
            name="fk_relation_source_entity_id",
        ),
        ForeignKeyConstraint(
            ["environment_id", "destination_entity_id"],
            ["state_entities.environment_id", "state_entities.entity_id"],
            name="fk_relation_destination_entity_id",
        ),
        CheckConstraint("length(relation_id) > 0", name="state_relations_relation_id_nonempty"),
        CheckConstraint("length(environment_id) > 0", name="state_relations_environment_id_nonempty"),
        CheckConstraint("state_version >= 1", name="state_relations_state_version_minimum"),
        CheckConstraint("jsonb_typeof(evidence_ids) = 'array'", name="state_relations_evidence_ids_json"),
        CheckConstraint("row_version >= 1", name="state_relations_row_version"),
    )


class IncidentRow(Versioned, Base):
    __tablename__ = "incidents"
    incident_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(Text, nullable=False)
    affected_asset_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    related_event_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    event_group_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    triaged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    investigation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    open_action_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    residual_risks: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    closure_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_evidence_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_incidents_environment"
        ),
        UniqueConstraint("environment_id", "incident_id", name="uq_incidents_environment_id"),
        CheckConstraint(
            "created_at >= first_observed_at AND updated_at >= created_at", name="incident_interval"
        ),
        CheckConstraint(
            "(status = 'CLOSED' AND closure_type IS NOT NULL AND jsonb_array_length(closure_evidence_ids) > 0 AND closed_at IS NOT NULL) OR (status <> 'CLOSED' AND closure_type IS NULL)",
            name="incident_closure",
        ),
        Index("ix_incident_env_status", "environment_id", "status", "priority"),
        CheckConstraint("length(incident_id) > 0", name="incidents_incident_id_nonempty"),
        CheckConstraint(
            "status IN ('NEW', 'TRIAGED', 'INVESTIGATING', 'PLANNED', 'WAITING_APPROVAL', 'EXECUTING', 'VERIFYING', 'CONTAINED', 'RESOLVED', 'CLOSED', 'HUMAN_REVIEW', 'REOPENED')",
            name="incidents_status_enum",
        ),
        CheckConstraint("priority IN ('P0', 'P1', 'P2', 'P3', 'P4')", name="incidents_priority_enum"),
        CheckConstraint(
            "jsonb_typeof(affected_asset_ids) = 'array'", name="incidents_affected_asset_ids_json"
        ),
        CheckConstraint("jsonb_typeof(related_event_ids) = 'array'", name="incidents_related_event_ids_json"),
        CheckConstraint("jsonb_typeof(event_group_ids) = 'array'", name="incidents_event_group_ids_json"),
        CheckConstraint("jsonb_typeof(evidence_ids) = 'array'", name="incidents_evidence_ids_json"),
        CheckConstraint("state_version >= 1", name="incidents_state_version_minimum"),
        CheckConstraint("jsonb_typeof(open_action_ids) = 'array'", name="incidents_open_action_ids_json"),
        CheckConstraint("jsonb_typeof(residual_risks) = 'array'", name="incidents_residual_risks_json"),
        CheckConstraint(
            "closure_type IN ('CLOSED_REMEDIATED', 'CLOSED_FALSE_POSITIVE', 'CLOSED_DUPLICATE', 'CLOSED_ACCEPTED_RISK')",
            name="incidents_closure_type_enum",
        ),
        CheckConstraint(
            "jsonb_typeof(closure_evidence_ids) = 'array'", name="incidents_closure_evidence_ids_json"
        ),
        CheckConstraint("row_version >= 1", name="incidents_row_version"),
    )


class ContextRow(Base):
    __tablename__ = "context_bundles"
    context_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    incident_id: Mapped[str] = mapped_column(Text, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    excluded_evidence_reasons: Mapped[dict[str, Any]] = mapped_column(
        JSONB(none_as_null=True), nullable=False
    )
    unresolved_conflicts: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    sensor_health_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    capability_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    token_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    data_classification: Mapped[str] = mapped_column(Text, nullable=False)
    egress_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    summary_version: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_context_bundles_environment"
        ),
        UniqueConstraint("environment_id", "context_id", name="uq_context_bundles_environment_id"),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_context_bundles_incident",
        ),
        UniqueConstraint("environment_id", "incident_id", "context_id", name="uq_context_incident"),
        CheckConstraint("length(context_id) > 0", name="context_bundles_context_id_nonempty"),
        CheckConstraint("state_version >= 1", name="context_bundles_state_version_minimum"),
        CheckConstraint("jsonb_typeof(evidence_ids) = 'array'", name="context_bundles_evidence_ids_json"),
        CheckConstraint(
            "jsonb_typeof(excluded_evidence_reasons) = 'object'",
            name="context_bundles_excluded_evidence_reasons_json",
        ),
        CheckConstraint(
            "jsonb_typeof(unresolved_conflicts) = 'array'", name="context_bundles_unresolved_conflicts_json"
        ),
        CheckConstraint(
            "jsonb_typeof(sensor_health_ids) = 'array'", name="context_bundles_sensor_health_ids_json"
        ),
        CheckConstraint("jsonb_typeof(capability_ids) = 'array'", name="context_bundles_capability_ids_json"),
        CheckConstraint("token_budget > 0", name="context_bundles_token_budget_exclusiveMinimum"),
        CheckConstraint(
            "data_classification IN ('PUBLIC', 'INTERNAL', 'SENSITIVE', 'RESTRICTED')",
            name="context_bundles_data_classification_enum",
        ),
    )


class WorkerLeaseRow(Versioned, Base):
    __tablename__ = "worker_leases"
    lease_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, nullable=False)
    worker_id: Mapped[str] = mapped_column(Text, nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    renewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(["task_id"], ["tasks.task_id"], name="fk_lease_task"),
        UniqueConstraint("task_id", "generation", name="uq_task_lease_generation"),
        UniqueConstraint("task_id", "lease_id", name="uq_task_lease_id"),
        CheckConstraint(
            "expires_at > acquired_at AND (renewed_at IS NULL OR renewed_at >= acquired_at)",
            name="lease_interval",
        ),
        Index("ix_leases_expiry", "expires_at"),
        CheckConstraint("length(lease_id) > 0", name="worker_leases_lease_id_nonempty"),
        CheckConstraint("generation >= 1", name="worker_leases_generation_minimum"),
        CheckConstraint("row_version >= 1", name="worker_leases_row_version"),
    )


class TaskRow(Versioned, Base):
    __tablename__ = "tasks"
    task_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    incident_id: Mapped[str] = mapped_column(Text, nullable=False)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    capability_id: Mapped[str] = mapped_column(Text, nullable=False)
    capability_version: Mapped[str] = mapped_column(Text, nullable=False)
    target_resource_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    scope_id: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(Text, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active_lease_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_tasks_environment"
        ),
        UniqueConstraint("environment_id", "task_id", name="uq_tasks_environment_id"),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_tasks_incident",
        ),
        ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_tasks_scope",
        ),
        ForeignKeyConstraint(
            ["capability_id", "capability_version"],
            ["capabilities.capability_id", "capabilities.version"],
            name="fk_tasks_capability",
        ),
        UniqueConstraint("environment_id", "incident_id", "task_id", name="uq_task_incident"),
        ForeignKeyConstraint(
            ["task_id", "active_lease_id"],
            ["worker_leases.task_id", "worker_leases.lease_id"],
            name="fk_task_active_lease",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
        CheckConstraint("attempt_count <= max_attempts", name="task_attempt_budget"),
        Index("ix_tasks_dispatch", "status", "priority", "queued_at"),
        CheckConstraint("length(task_id) > 0", name="tasks_task_id_nonempty"),
        CheckConstraint("jsonb_typeof(dependencies) = 'array'", name="tasks_dependencies_json"),
        CheckConstraint("jsonb_typeof(target_resource_ids) = 'array'", name="tasks_target_resource_ids_json"),
        CheckConstraint(
            "jsonb_array_length(target_resource_ids) >= 1", name="tasks_target_resource_ids_minitems"
        ),
        CheckConstraint("jsonb_typeof(parameters) = 'object'", name="tasks_parameters_json"),
        CheckConstraint(
            "status IN ('QUEUED', 'BLOCKED', 'WAITING_APPROVAL', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'TIMED_OUT')",
            name="tasks_status_enum",
        ),
        CheckConstraint("priority IN ('P0', 'P1', 'P2', 'P3', 'P4')", name="tasks_priority_enum"),
        CheckConstraint("timeout_seconds > 0", name="tasks_timeout_seconds_exclusiveMinimum"),
        CheckConstraint("max_attempts >= 1", name="tasks_max_attempts_minimum"),
        CheckConstraint("max_attempts <= 10", name="tasks_max_attempts_maximum"),
        CheckConstraint("attempt_count >= 0", name="tasks_attempt_count_minimum"),
        CheckConstraint("attempt_count <= 10", name="tasks_attempt_count_maximum"),
        CheckConstraint("jsonb_typeof(evidence_ids) = 'array'", name="tasks_evidence_ids_json"),
        CheckConstraint("row_version >= 1", name="tasks_row_version"),
    )


class PlanRow(Base):
    __tablename__ = "plans"
    plan_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    incident_id: Mapped[str] = mapped_column(Text, nullable=False)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    context_id: Mapped[str] = mapped_column(Text, nullable=False)
    model_run_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    hypotheses: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    tasks: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    stop_conditions: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    max_replans: Mapped[int] = mapped_column(Integer, nullable=False)
    total_model_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_plans_environment"
        ),
        UniqueConstraint("environment_id", "plan_id", name="uq_plans_environment_id"),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_plans_incident",
        ),
        ForeignKeyConstraint(
            ["environment_id", "incident_id", "context_id"],
            ["context_bundles.environment_id", "context_bundles.incident_id", "context_bundles.context_id"],
            name="fk_plan_context",
        ),
        ForeignKeyConstraint(
            ["environment_id", "model_run_id"],
            ["model_runs.environment_id", "model_runs.run_id"],
            name="fk_plan_model",
        ),
        CheckConstraint("length(plan_id) > 0", name="plans_plan_id_nonempty"),
        CheckConstraint("jsonb_typeof(hypotheses) = 'array'", name="plans_hypotheses_json"),
        CheckConstraint("jsonb_array_length(hypotheses) >= 1", name="plans_hypotheses_minitems"),
        CheckConstraint("jsonb_typeof(tasks) = 'array'", name="plans_tasks_json"),
        CheckConstraint("jsonb_array_length(tasks) >= 1", name="plans_tasks_minitems"),
        CheckConstraint("jsonb_typeof(stop_conditions) = 'array'", name="plans_stop_conditions_json"),
        CheckConstraint("jsonb_array_length(stop_conditions) >= 1", name="plans_stop_conditions_minitems"),
        CheckConstraint("max_replans >= 0", name="plans_max_replans_minimum"),
        CheckConstraint("total_model_calls >= 0", name="plans_total_model_calls_minimum"),
    )


class ModelRunRow(Base):
    __tablename__ = "model_runs"
    run_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    incident_id: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    model_revision: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    context_id: Mapped[str] = mapped_column(Text, nullable=False)
    input_hash: Mapped[str] = mapped_column(Text, nullable=False)
    output_hash: Mapped[str] = mapped_column(Text, nullable=False)
    route_reason: Mapped[str] = mapped_column(Text, nullable=False)
    fallback_from_run_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cached_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    schema_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    safety_status: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_model_runs_environment"
        ),
        UniqueConstraint("environment_id", "run_id", name="uq_model_runs_environment_id"),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_model_runs_incident",
        ),
        ForeignKeyConstraint(
            ["environment_id", "incident_id", "context_id"],
            ["context_bundles.environment_id", "context_bundles.incident_id", "context_bundles.context_id"],
            name="fk_model_context",
        ),
        ForeignKeyConstraint(
            ["environment_id", "incident_id", "task_id"],
            ["tasks.environment_id", "tasks.incident_id", "tasks.task_id"],
            name="fk_model_task",
        ),
        ForeignKeyConstraint(
            ["environment_id", "fallback_from_run_id"],
            ["model_runs.environment_id", "model_runs.run_id"],
            name="fk_model_fallback",
        ),
        CheckConstraint("length(run_id) > 0", name="model_runs_run_id_nonempty"),
        CheckConstraint("input_hash ~ '^[0-9a-f]{64}$'", name="model_runs_input_hash_pattern"),
        CheckConstraint("output_hash ~ '^[0-9a-f]{64}$'", name="model_runs_output_hash_pattern"),
        CheckConstraint("input_tokens >= 0", name="model_runs_input_tokens_minimum"),
        CheckConstraint("output_tokens >= 0", name="model_runs_output_tokens_minimum"),
        CheckConstraint("cached_tokens >= 0", name="model_runs_cached_tokens_minimum"),
        CheckConstraint("latency_ms >= 0", name="model_runs_latency_ms_minimum"),
        CheckConstraint("cost_usd >= 0", name="model_runs_cost_usd_minimum"),
        CheckConstraint(
            "safety_status IN ('PASS', 'REJECTED', 'DEGRADED')", name="model_runs_safety_status_enum"
        ),
    )


class CapabilityRow(Base):
    __tablename__ = "capabilities"
    capability_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    adapter: Mapped[str] = mapped_column(Text, nullable=False)
    base_risk: Mapped[str] = mapped_column(Text, nullable=False)
    operation_kind: Mapped[str] = mapped_column(Text, nullable=False)
    controller_location: Mapped[str] = mapped_column(Text, nullable=False)
    execution_location: Mapped[str] = mapped_column(Text, nullable=False)
    target_domain: Mapped[str] = mapped_column(Text, nullable=False)
    network_path: Mapped[str] = mapped_column(Text, nullable=False)
    cleanup_owner: Mapped[str] = mapped_column(Text, nullable=False)
    supported_os: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    scope_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency: Mapped[str] = mapped_column(Text, nullable=False)
    reconciliation_method: Mapped[str] = mapped_column(Text, nullable=False)
    ttl_enforcement: Mapped[str] = mapped_column(Text, nullable=False)
    rollback_policy: Mapped[str] = mapped_column(Text, nullable=False)
    required_permissions: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    required_secret_refs: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    supports_cancel: Mapped[bool] = mapped_column(Boolean, nullable=False)
    supports_dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False)
    resource_locks: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_evidence_types: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    verification_capability_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    compensator_capability_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    integration_status: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint("length(capability_id) > 0", name="capabilities_capability_id_nonempty"),
        CheckConstraint("length(version) > 0", name="capabilities_version_nonempty"),
        CheckConstraint(
            "base_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')", name="capabilities_base_risk_enum"
        ),
        CheckConstraint(
            "operation_kind IN ('PASSIVE_READ', 'ACTIVE_CHECK', 'STATE_CHANGE')",
            name="capabilities_operation_kind_enum",
        ),
        CheckConstraint("jsonb_typeof(supported_os) = 'array'", name="capabilities_supported_os_json"),
        CheckConstraint("jsonb_typeof(input_schema) = 'object'", name="capabilities_input_schema_json"),
        CheckConstraint("jsonb_typeof(output_schema) = 'object'", name="capabilities_output_schema_json"),
        CheckConstraint("timeout_seconds > 0", name="capabilities_timeout_seconds_exclusiveMinimum"),
        CheckConstraint(
            "idempotency IN ('NATIVE', 'ADAPTER_RECONCILE', 'NONE')", name="capabilities_idempotency_enum"
        ),
        CheckConstraint(
            "ttl_enforcement IN ('DEVICE', 'SITE_DURABLE_WATCHDOG', 'CONTROLLER_ONLY', 'NONE')",
            name="capabilities_ttl_enforcement_enum",
        ),
        CheckConstraint(
            "jsonb_typeof(required_permissions) = 'array'", name="capabilities_required_permissions_json"
        ),
        CheckConstraint(
            "jsonb_typeof(required_secret_refs) = 'array'", name="capabilities_required_secret_refs_json"
        ),
        CheckConstraint("jsonb_typeof(resource_locks) = 'array'", name="capabilities_resource_locks_json"),
        CheckConstraint("max_concurrency >= 1", name="capabilities_max_concurrency_minimum"),
        CheckConstraint(
            "jsonb_typeof(expected_evidence_types) = 'array'",
            name="capabilities_expected_evidence_types_json",
        ),
        CheckConstraint(
            "integration_status IN ('DESIGN', 'ADAPTED', 'LAB_VERIFIED', 'PRODUCTION_VERIFIED')",
            name="capabilities_integration_status_enum",
        ),
    )


class CapabilityHealthRow(Versioned, Base):
    __tablename__ = "capability_health"
    capability_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    capability_version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    worker_pool: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queue_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    running_count: Mapped[int] = mapped_column(Integer, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_capability_health_environment"
        ),
        ForeignKeyConstraint(
            ["capability_id", "capability_version"],
            ["capabilities.capability_id", "capabilities.version"],
            name="fk_capability_health_capability",
        ),
        CheckConstraint("length(capability_id) > 0", name="capability_health_capability_id_nonempty"),
        CheckConstraint(
            "length(capability_version) > 0", name="capability_health_capability_version_nonempty"
        ),
        CheckConstraint("length(environment_id) > 0", name="capability_health_environment_id_nonempty"),
        CheckConstraint("length(worker_pool) > 0", name="capability_health_worker_pool_nonempty"),
        CheckConstraint(
            "status IN ('UNVERIFIED', 'HEALTHY', 'DEGRADED', 'OFFLINE')", name="capability_health_status_enum"
        ),
        CheckConstraint("latency_ms >= 0", name="capability_health_latency_ms_minimum"),
        CheckConstraint("queue_depth >= 0", name="capability_health_queue_depth_minimum"),
        CheckConstraint("running_count >= 0", name="capability_health_running_count_minimum"),
        CheckConstraint("row_version >= 1", name="capability_health_row_version"),
    )


class ActionRow(Base):
    __tablename__ = "action_requests"
    action_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    incident_id: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[str] = mapped_column(Text, nullable=False)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    capability_id: Mapped[str] = mapped_column(Text, nullable=False)
    capability_version: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    target: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    scope_id: Mapped[str] = mapped_column(Text, nullable=False)
    scope_version: Mapped[str] = mapped_column(Text, nullable=False)
    environment_profile_version: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    expected_state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    preconditions: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    ownership_tag: Mapped[str] = mapped_column(Text, nullable=False)
    rollback_policy_id: Mapped[str] = mapped_column(Text, nullable=False)
    action_digest: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_action_requests_environment"
        ),
        UniqueConstraint("environment_id", "action_id", name="uq_action_requests_environment_id"),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_action_requests_incident",
        ),
        ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_action_requests_scope",
        ),
        ForeignKeyConstraint(
            ["capability_id", "capability_version"],
            ["capabilities.capability_id", "capabilities.version"],
            name="fk_action_requests_capability",
        ),
        UniqueConstraint("environment_id", "idempotency_key", name="uq_action_idempotency"),
        UniqueConstraint("environment_id", "incident_id", "action_id", name="uq_action_incident"),
        UniqueConstraint("action_id", "action_digest", name="uq_action_digest"),
        ForeignKeyConstraint(
            ["environment_id", "incident_id", "task_id"],
            ["tasks.environment_id", "tasks.incident_id", "tasks.task_id"],
            name="fk_action_task",
        ),
        CheckConstraint("expires_at > created_at", name="action_interval"),
        CheckConstraint("action_digest ~ '^[0-9a-f]{64}$'", name="action_digest_format"),
        CheckConstraint(
            "target->>'environment_id' = environment_id AND (source IS NULL OR source->>'environment_id' = environment_id)",
            name="action_resource_environment",
        ),
        CheckConstraint("length(action_id) > 0", name="action_requests_action_id_nonempty"),
        CheckConstraint("jsonb_typeof(source) = 'object'", name="action_requests_source_json"),
        CheckConstraint("jsonb_typeof(target) = 'object'", name="action_requests_target_json"),
        CheckConstraint("jsonb_typeof(parameters) = 'object'", name="action_requests_parameters_json"),
        CheckConstraint("expected_state_version >= 1", name="action_requests_expected_state_version_minimum"),
        CheckConstraint("jsonb_typeof(preconditions) = 'array'", name="action_requests_preconditions_json"),
        CheckConstraint(
            "jsonb_array_length(preconditions) >= 1", name="action_requests_preconditions_minitems"
        ),
        CheckConstraint("jsonb_typeof(evidence_ids) = 'array'", name="action_requests_evidence_ids_json"),
        CheckConstraint(
            "jsonb_array_length(evidence_ids) >= 1", name="action_requests_evidence_ids_minitems"
        ),
        CheckConstraint("ttl_seconds >= 0", name="action_requests_ttl_seconds_minimum"),
    )


class ApprovalRow(Base):
    __tablename__ = "approvals"
    approval_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    action_id: Mapped[str] = mapped_column(Text, nullable=False)
    action_digest: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    actor_role: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["action_id", "action_digest"],
            ["action_requests.action_id", "action_requests.action_digest"],
            name="fk_approval_action_digest",
        ),
        UniqueConstraint("approval_id", "action_id", "action_digest", name="uq_approval_binding"),
        CheckConstraint("expires_at > approved_at", name="approval_interval"),
        CheckConstraint("length(approval_id) > 0", name="approvals_approval_id_nonempty"),
        CheckConstraint("action_digest ~ '^[0-9a-f]{64}$'", name="approvals_action_digest_pattern"),
        CheckConstraint("actor_role IN ('APPROVER', 'ADMIN')", name="approvals_actor_role_enum"),
        CheckConstraint("decision IN ('APPROVED', 'REJECTED')", name="approvals_decision_enum"),
    )


class AuthorizationContextRow(Base):
    __tablename__ = "authorization_contexts"
    authorization_context_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    action_id: Mapped[str] = mapped_column(Text, nullable=False)
    action_digest: Mapped[str] = mapped_column(Text, nullable=False)
    principal_id: Mapped[str] = mapped_column(Text, nullable=False)
    principal_role: Mapped[str] = mapped_column(Text, nullable=False)
    environment_profile_version: Mapped[str] = mapped_column(Text, nullable=False)
    scope_id: Mapped[str] = mapped_column(Text, nullable=False)
    scope_version: Mapped[str] = mapped_column(Text, nullable=False)
    capability_id: Mapped[str] = mapped_column(Text, nullable=False)
    capability_version: Mapped[str] = mapped_column(Text, nullable=False)
    target_resource_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_resource_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_criticality: Mapped[str] = mapped_column(Text, nullable=False)
    business_impact: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_quality: Mapped[str] = mapped_column(Text, nullable=False)
    sensor_health_status: Mapped[str] = mapped_column(Text, nullable=False)
    autonomy_mode: Mapped[str] = mapped_column(Text, nullable=False)
    load_mode: Mapped[str] = mapped_column(Text, nullable=False)
    requested_risk: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    budget_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_authorization_contexts_environment"
        ),
        UniqueConstraint(
            "environment_id", "authorization_context_id", name="uq_authorization_contexts_environment_id"
        ),
        ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_authorization_contexts_scope",
        ),
        ForeignKeyConstraint(
            ["capability_id", "capability_version"],
            ["capabilities.capability_id", "capabilities.version"],
            name="fk_authorization_contexts_capability",
        ),
        ForeignKeyConstraint(
            ["environment_id", "action_id"],
            ["action_requests.environment_id", "action_requests.action_id"],
            name="fk_authctx_action_env",
        ),
        ForeignKeyConstraint(
            ["action_id", "action_digest"],
            ["action_requests.action_id", "action_requests.action_digest"],
            name="fk_authctx_action_digest",
        ),
        UniqueConstraint("authorization_context_id", "action_id", "action_digest", name="uq_authctx_binding"),
        ForeignKeyConstraint(
            ["environment_id", "target_resource_id"],
            ["resources.environment_id", "resources.resource_id"],
            name="fk_authctx_target_resource_id",
        ),
        ForeignKeyConstraint(
            ["environment_id", "source_resource_id"],
            ["resources.environment_id", "resources.resource_id"],
            name="fk_authctx_source_resource_id",
        ),
        CheckConstraint(
            "length(authorization_context_id) > 0",
            name="authorization_contexts_authorization_context__nonempty",
        ),
        CheckConstraint(
            "action_digest ~ '^[0-9a-f]{64}$'", name="authorization_contexts_action_digest_pattern"
        ),
        CheckConstraint(
            "asset_criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="authorization_contexts_asset_criticality_enum",
        ),
        CheckConstraint(
            "business_impact IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="authorization_contexts_business_impact_enum",
        ),
        CheckConstraint(
            "evidence_quality IN ('LOW', 'MEDIUM', 'HIGH')",
            name="authorization_contexts_evidence_quality_enum",
        ),
        CheckConstraint(
            "sensor_health_status IN ('HEALTHY', 'DEGRADED', 'UNKNOWN')",
            name="authorization_contexts_sensor_health_status_enum",
        ),
        CheckConstraint(
            "autonomy_mode IN ('OBSERVE_ONLY', 'ASSISTED', 'CONTROLLED_AUTONOMY', 'VALIDATION')",
            name="authorization_contexts_autonomy_mode_enum",
        ),
        CheckConstraint(
            "load_mode IN ('NORMAL', 'HIGH_LOAD', 'EMERGENCY')", name="authorization_contexts_load_mode_enum"
        ),
        CheckConstraint(
            "requested_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')",
            name="authorization_contexts_requested_risk_enum",
        ),
    )


class AuthorizationDecisionRow(Base):
    __tablename__ = "authorization_decisions"
    authorization_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    authorization_context_id: Mapped[str] = mapped_column(Text, nullable=False)
    action_id: Mapped[str] = mapped_column(Text, nullable=False)
    action_digest: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    assessed_risk: Mapped[str] = mapped_column(Text, nullable=False)
    business_impact: Mapped[str] = mapped_column(Text, nullable=False)
    human_approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    approval_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reasons: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["authorization_context_id", "action_id", "action_digest"],
            [
                "authorization_contexts.authorization_context_id",
                "authorization_contexts.action_id",
                "authorization_contexts.action_digest",
            ],
            name="fk_decision_context_binding",
        ),
        ForeignKeyConstraint(
            ["approval_id", "action_id", "action_digest"],
            ["approvals.approval_id", "approvals.action_id", "approvals.action_digest"],
            name="fk_decision_approval",
        ),
        CheckConstraint(
            "(assessed_risk <> 'R5' AND business_impact NOT IN ('HIGH','CRITICAL')) OR human_approval_required",
            name="high_impact_human",
        ),
        CheckConstraint(
            "outcome <> 'ALLOW' OR NOT human_approval_required OR approval_id IS NOT NULL",
            name="allow_requires_approval",
        ),
        CheckConstraint(
            "length(authorization_id) > 0", name="authorization_decisions_authorization_id_nonempty"
        ),
        CheckConstraint(
            "action_digest ~ '^[0-9a-f]{64}$'", name="authorization_decisions_action_digest_pattern"
        ),
        CheckConstraint(
            "outcome IN ('ALLOW', 'DENY', 'REQUIRE_APPROVAL', 'DOWNGRADE')",
            name="authorization_decisions_outcome_enum",
        ),
        CheckConstraint(
            "assessed_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')",
            name="authorization_decisions_assessed_risk_enum",
        ),
        CheckConstraint(
            "business_impact IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="authorization_decisions_business_impact_enum",
        ),
        CheckConstraint("jsonb_typeof(reasons) = 'array'", name="authorization_decisions_reasons_json"),
        CheckConstraint("jsonb_array_length(reasons) >= 1", name="authorization_decisions_reasons_minitems"),
    )


class ActionAttemptRow(Versioned, Base):
    __tablename__ = "action_attempts"
    attempt_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    action_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    fencing_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_id: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_receipt_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    reconciliation_state: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_class: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_response_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(["action_id"], ["action_requests.action_id"], name="fk_attempt_action"),
        CheckConstraint("finished_at IS NULL OR finished_at >= started_at", name="attempt_interval"),
        Index("ix_attempts_action_time", "action_id", "started_at"),
        CheckConstraint("length(attempt_id) > 0", name="action_attempts_attempt_id_nonempty"),
        CheckConstraint(
            "status IN ('PROPOSED', 'WAITING_APPROVAL', 'AUTHORIZED', 'DISPATCHED', 'EXECUTING', 'EXECUTED', 'EXECUTION_UNKNOWN', 'RECONCILING', 'COMPENSATING', 'COMPENSATED', 'COMPENSATION_FAILED', 'NEEDS_MANUAL', 'DENIED', 'EXPIRED', 'CANCELLED', 'FAILED')",
            name="action_attempts_status_enum",
        ),
        CheckConstraint("fencing_generation >= 1", name="action_attempts_fencing_generation_minimum"),
        CheckConstraint(
            "reconciliation_state IN ('NOT_NEEDED', 'PENDING', 'CONFIRMED_APPLIED', 'CONFIRMED_NOT_APPLIED', 'PARTIAL', 'UNKNOWN')",
            name="action_attempts_reconciliation_state_enum",
        ),
        CheckConstraint("jsonb_typeof(evidence_ids) = 'array'", name="action_attempts_evidence_ids_json"),
        CheckConstraint(
            "device_response_hash ~ '^[0-9a-f]{64}$'", name="action_attempts_device_response_hash_pattern"
        ),
        CheckConstraint("row_version >= 1", name="action_attempts_row_version"),
    )


class VerificationSpecRow(Base):
    __tablename__ = "verification_specs"
    verification_spec_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_version: Mapped[str] = mapped_column(Text, nullable=False)
    objective_type: Mapped[str] = mapped_column(Text, nullable=False)
    checks: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    aggregation_rule: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint("aggregation_rule = 'THREE_DIMENSION_STRICT'", name="verification_aggregation"),
        ForeignKeyConstraint(
            ["scenario_id", "scenario_version"],
            ["validation_scenarios.scenario_id", "validation_scenarios.version"],
            name="fk_spec_scenario",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
        CheckConstraint(
            "length(verification_spec_id) > 0", name="verification_specs_verification_spec_id_nonempty"
        ),
        CheckConstraint(
            "objective_type IN ('DETECTION', 'CONTAINMENT', 'REMEDIATION', 'RECOVERY', 'CLEANUP')",
            name="verification_specs_objective_type_enum",
        ),
        CheckConstraint("jsonb_typeof(checks) = 'array'", name="verification_specs_checks_json"),
        CheckConstraint("jsonb_array_length(checks) >= 3", name="verification_specs_checks_minitems"),
    )


class VerificationResultRow(Base):
    __tablename__ = "verification_results"
    verification_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    verification_spec_id: Mapped[str] = mapped_column(Text, nullable=False)
    incident_id: Mapped[str] = mapped_column(Text, nullable=False)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    action_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    objective_type: Mapped[str] = mapped_column(Text, nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    target_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    scope_id: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_version: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    security_status: Mapped[str] = mapped_column(Text, nullable=False)
    business_status: Mapped[str] = mapped_column(Text, nullable=False)
    observation_status: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    expected_result: Mapped[str] = mapped_column(Text, nullable=False)
    observed_result: Mapped[str] = mapped_column(Text, nullable=False)
    residual_risks: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    recommended_next_step: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_verification_results_environment"
        ),
        UniqueConstraint("environment_id", "verification_id", name="uq_verification_results_environment_id"),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_verification_results_incident",
        ),
        ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_verification_results_scope",
        ),
        ForeignKeyConstraint(
            ["environment_id", "incident_id", "action_id"],
            ["action_requests.environment_id", "action_requests.incident_id", "action_requests.action_id"],
            name="fk_verification_action",
        ),
        ForeignKeyConstraint(
            ["verification_spec_id"], ["verification_specs.verification_spec_id"], name="fk_verification_spec"
        ),
        ForeignKeyConstraint(
            ["environment_id", "validation_run_id"],
            ["validation_runs.environment_id", "validation_runs.run_id"],
            name="fk_verification_run",
        ),
        CheckConstraint(
            "finished_at >= started_at AND valid_until >= finished_at", name="verification_interval"
        ),
        CheckConstraint(
            "status = CASE WHEN security_status = 'FAIL' OR business_status = 'FAIL' THEN 'FAIL' WHEN security_status = 'PASS' AND business_status = 'PASS' AND observation_status = 'PASS' THEN 'PASS' ELSE 'INCONCLUSIVE' END",
            name="verification_three_check",
        ),
        CheckConstraint("length(verification_id) > 0", name="verification_results_verification_id_nonempty"),
        CheckConstraint(
            "objective_type IN ('DETECTION', 'CONTAINMENT', 'REMEDIATION', 'RECOVERY', 'CLEANUP')",
            name="verification_results_objective_type_enum",
        ),
        CheckConstraint("jsonb_typeof(target_ids) = 'array'", name="verification_results_target_ids_json"),
        CheckConstraint(
            "jsonb_array_length(target_ids) >= 1", name="verification_results_target_ids_minitems"
        ),
        CheckConstraint(
            "security_status IN ('PASS', 'FAIL', 'INCONCLUSIVE')",
            name="verification_results_security_status_enum",
        ),
        CheckConstraint(
            "business_status IN ('PASS', 'FAIL', 'INCONCLUSIVE')",
            name="verification_results_business_status_enum",
        ),
        CheckConstraint(
            "observation_status IN ('PASS', 'FAIL', 'INCONCLUSIVE')",
            name="verification_results_observation_status_enum",
        ),
        CheckConstraint(
            "status IN ('PASS', 'FAIL', 'INCONCLUSIVE')", name="verification_results_status_enum"
        ),
        CheckConstraint(
            "jsonb_typeof(evidence_ids) = 'array'", name="verification_results_evidence_ids_json"
        ),
        CheckConstraint(
            "jsonb_array_length(evidence_ids) >= 1", name="verification_results_evidence_ids_minitems"
        ),
        CheckConstraint(
            "jsonb_typeof(residual_risks) = 'array'", name="verification_results_residual_risks_json"
        ),
    )


class ValidationScenarioRow(Base):
    __tablename__ = "validation_scenarios"
    scenario_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    implementation_status: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    scope_id: Mapped[str] = mapped_column(Text, nullable=False)
    preconditions: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    trigger_steps: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    expected_events: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    verification_spec_id: Mapped[str] = mapped_column(Text, nullable=False)
    cleanup_steps: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    stop_conditions: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    config_is_measured_performance: Mapped[bool] = mapped_column(Boolean, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_validation_scenarios_environment"
        ),
        ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_validation_scenarios_scope",
        ),
        ForeignKeyConstraint(
            ["verification_spec_id"],
            ["verification_specs.verification_spec_id"],
            name="fk_scenario_spec",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
        UniqueConstraint("environment_id", "scenario_id", "version", name="uq_scenario_environment_version"),
        CheckConstraint("length(scenario_id) > 0", name="validation_scenarios_scenario_id_nonempty"),
        CheckConstraint("length(version) > 0", name="validation_scenarios_version_nonempty"),
        CheckConstraint(
            "implementation_status IN ('DESIGN_ONLY', 'LAB_VERIFIED')",
            name="validation_scenarios_implementation_status_enum",
        ),
        CheckConstraint(
            "jsonb_typeof(preconditions) = 'array'", name="validation_scenarios_preconditions_json"
        ),
        CheckConstraint(
            "jsonb_typeof(trigger_steps) = 'array'", name="validation_scenarios_trigger_steps_json"
        ),
        CheckConstraint(
            "jsonb_typeof(expected_events) = 'array'", name="validation_scenarios_expected_events_json"
        ),
        CheckConstraint(
            "jsonb_typeof(cleanup_steps) = 'array'", name="validation_scenarios_cleanup_steps_json"
        ),
        CheckConstraint(
            "jsonb_typeof(stop_conditions) = 'array'", name="validation_scenarios_stop_conditions_json"
        ),
        CheckConstraint(
            "config_is_measured_performance IS FALSE",
            name="validation_scenarios_config_is_measured_perfo_const",
        ),
    )


class ValidationRunRow(Base):
    __tablename__ = "validation_runs"
    run_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_version: Mapped[str] = mapped_column(Text, nullable=False)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    scope_id: Mapped[str] = mapped_column(Text, nullable=False)
    registered_by: Mapped[str] = mapped_column(Text, nullable=False)
    trusted_registration: Mapped[bool] = mapped_column(Boolean, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_event_types: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    allowed_side_effects: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    cleanup_policy_id: Mapped[str] = mapped_column(Text, nullable=False)
    data_origin: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_validation_runs_environment"
        ),
        UniqueConstraint("environment_id", "run_id", name="uq_validation_runs_environment_id"),
        ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_validation_runs_scope",
        ),
        ForeignKeyConstraint(
            ["environment_id", "scenario_id", "scenario_version"],
            [
                "validation_scenarios.environment_id",
                "validation_scenarios.scenario_id",
                "validation_scenarios.version",
            ],
            name="fk_run_scenario",
        ),
        CheckConstraint("length(run_id) > 0", name="validation_runs_run_id_nonempty"),
        CheckConstraint(
            "jsonb_typeof(expected_event_types) = 'array'", name="validation_runs_expected_event_types_json"
        ),
        CheckConstraint(
            "jsonb_typeof(allowed_side_effects) = 'array'", name="validation_runs_allowed_side_effects_json"
        ),
        CheckConstraint("data_origin IN ('SYNTHETIC', 'OBSERVED')", name="validation_runs_data_origin_enum"),
    )


class PolicySnapshotRow(Base):
    __tablename__ = "policy_snapshots"
    policy_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    version: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    high_impact_requires_human: Mapped[bool] = mapped_column(Boolean, nullable=False)
    r5_auto_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    load_can_expand_permissions: Mapped[bool] = mapped_column(Boolean, nullable=False)
    allowed_capability_ids: Mapped[list[Any]] = mapped_column(JSONB(none_as_null=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_replans: Mapped[int] = mapped_column(Integer, nullable=False)
    max_model_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    max_active_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    max_elapsed_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_policy_snapshots_environment"
        ),
        CheckConstraint("length(policy_id) > 0", name="policy_snapshots_policy_id_nonempty"),
        CheckConstraint("length(version) > 0", name="policy_snapshots_version_nonempty"),
        CheckConstraint("length(environment_id) > 0", name="policy_snapshots_environment_id_nonempty"),
        CheckConstraint(
            "high_impact_requires_human IS TRUE", name="policy_snapshots_high_impact_requires_human_const"
        ),
        CheckConstraint("r5_auto_allowed IS FALSE", name="policy_snapshots_r5_auto_allowed_const"),
        CheckConstraint(
            "load_can_expand_permissions IS FALSE", name="policy_snapshots_load_can_expand_permissions_const"
        ),
        CheckConstraint(
            "jsonb_typeof(allowed_capability_ids) = 'array'",
            name="policy_snapshots_allowed_capability_ids_json",
        ),
        CheckConstraint("max_replans >= 0", name="policy_snapshots_max_replans_minimum"),
        CheckConstraint("max_model_calls >= 1", name="policy_snapshots_max_model_calls_minimum"),
        CheckConstraint("max_active_calls >= 1", name="policy_snapshots_max_active_calls_minimum"),
        CheckConstraint("max_elapsed_seconds >= 1", name="policy_snapshots_max_elapsed_seconds_minimum"),
    )


class AuditEntryRow(Base):
    __tablename__ = "audit_entries"
    audit_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    trace_id: Mapped[str] = mapped_column(Text, nullable=False)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    object_kind: Mapped[str] = mapped_column(Text, nullable=False)
    object_id: Mapped[str] = mapped_column(Text, nullable=False)
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_entry_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    integrity_hash: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_audit_entries_environment"
        ),
        UniqueConstraint("environment_id", "audit_id", name="uq_audit_entries_environment_id"),
        UniqueConstraint("environment_id", "sequence", name="uq_audit_sequence"),
        UniqueConstraint("environment_id", "integrity_hash", name="uq_audit_hash"),
        CheckConstraint("sequence >= 1", name="audit_sequence_positive"),
        Index("ix_audit_trace_time", "trace_id", "timestamp"),
        CheckConstraint("length(audit_id) > 0", name="audit_entries_audit_id_nonempty"),
        CheckConstraint(
            "actor_type IN ('HUMAN', 'SERVICE', 'MODEL', 'WORKER')", name="audit_entries_actor_type_enum"
        ),
        CheckConstraint(
            "previous_entry_hash ~ '^[0-9a-f]{64}$'", name="audit_entries_previous_entry_hash_pattern"
        ),
        CheckConstraint("integrity_hash ~ '^[0-9a-f]{64}$'", name="audit_entries_integrity_hash_pattern"),
    )


class OutboxRow(Versioned, Base):
    __tablename__ = "outbox"
    message_id: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(Text, nullable=False)
    aggregate_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_outbox_environment"
        ),
        CheckConstraint("generation >= 0", name="outbox_generation"),
        CheckConstraint("(lease_owner IS NULL) = (lease_until IS NULL)", name="outbox_lease_pair"),
        Index(
            "ix_outbox_pending", "available_at", "created_at", postgresql_where=text("published_at IS NULL")
        ),
        UniqueConstraint(
            "environment_id", "aggregate_type", "aggregate_id", "event_type", name="uq_outbox_aggregate_event"
        ),
        CheckConstraint("length(message_id) > 0", name="outbox_message_id_nonempty"),
        CheckConstraint("attempt_count >= 0", name="outbox_attempt_count_minimum"),
        CheckConstraint("row_version >= 1", name="outbox_row_version"),
    )
