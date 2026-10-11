"""M1.1 ai.5 initial PostgreSQL schema"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_m1_1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "capabilities",
        sa.Column("capability_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("adapter", sa.Text(), nullable=False),
        sa.Column("base_risk", sa.Text(), nullable=False),
        sa.Column("operation_kind", sa.Text(), nullable=False),
        sa.Column("controller_location", sa.Text(), nullable=False),
        sa.Column("execution_location", sa.Text(), nullable=False),
        sa.Column("target_domain", sa.Text(), nullable=False),
        sa.Column("network_path", sa.Text(), nullable=False),
        sa.Column("cleanup_owner", sa.Text(), nullable=False),
        sa.Column("supported_os", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column(
            "output_schema", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("scope_required", sa.Boolean(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("idempotency", sa.Text(), nullable=False),
        sa.Column("reconciliation_method", sa.Text(), nullable=False),
        sa.Column("ttl_enforcement", sa.Text(), nullable=False),
        sa.Column("rollback_policy", sa.Text(), nullable=False),
        sa.Column(
            "required_permissions", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "required_secret_refs", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("supports_cancel", sa.Boolean(), nullable=False),
        sa.Column("supports_dry_run", sa.Boolean(), nullable=False),
        sa.Column(
            "resource_locks", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column(
            "expected_evidence_types",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("verification_capability_id", sa.Text(), nullable=True),
        sa.Column("compensator_capability_id", sa.Text(), nullable=True),
        sa.Column("integration_status", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "base_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')",
            name=op.f("ck_capabilities_capabilities_base_risk_enum"),
        ),
        sa.CheckConstraint(
            "idempotency IN ('NATIVE', 'ADAPTER_RECONCILE', 'NONE')",
            name=op.f("ck_capabilities_capabilities_idempotency_enum"),
        ),
        sa.CheckConstraint(
            "integration_status IN ('DESIGN', 'ADAPTED', 'LAB_VERIFIED', 'PRODUCTION_VERIFIED')",
            name=op.f("ck_capabilities_capabilities_integration_status_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(expected_evidence_types) = 'array'",
            name=op.f("ck_capabilities_capabilities_expected_evidence_types_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(input_schema) = 'object'",
            name=op.f("ck_capabilities_capabilities_input_schema_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(output_schema) = 'object'",
            name=op.f("ck_capabilities_capabilities_output_schema_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(required_permissions) = 'array'",
            name=op.f("ck_capabilities_capabilities_required_permissions_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(required_secret_refs) = 'array'",
            name=op.f("ck_capabilities_capabilities_required_secret_refs_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(resource_locks) = 'array'",
            name=op.f("ck_capabilities_capabilities_resource_locks_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(supported_os) = 'array'",
            name=op.f("ck_capabilities_capabilities_supported_os_json"),
        ),
        sa.CheckConstraint(
            "operation_kind IN ('PASSIVE_READ', 'ACTIVE_CHECK', 'STATE_CHANGE')",
            name=op.f("ck_capabilities_capabilities_operation_kind_enum"),
        ),
        sa.CheckConstraint(
            "ttl_enforcement IN ('DEVICE', 'SITE_DURABLE_WATCHDOG', 'CONTROLLER_ONLY', 'NONE')",
            name=op.f("ck_capabilities_capabilities_ttl_enforcement_enum"),
        ),
        sa.CheckConstraint(
            "length(capability_id) > 0", name=op.f("ck_capabilities_capabilities_capability_id_nonempty")
        ),
        sa.CheckConstraint("length(version) > 0", name=op.f("ck_capabilities_capabilities_version_nonempty")),
        sa.CheckConstraint(
            "max_concurrency >= 1", name=op.f("ck_capabilities_capabilities_max_concurrency_minimum")
        ),
        sa.CheckConstraint(
            "timeout_seconds > 0", name=op.f("ck_capabilities_capabilities_timeout_seconds_exclusiveMinimum")
        ),
        sa.PrimaryKeyConstraint("capability_id", "version", name=op.f("pk_capabilities")),
    )
    op.create_table(
        "environments",
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("deployment_stage", sa.Text(), nullable=False),
        sa.Column("asset_domain", sa.Text(), nullable=False),
        sa.Column("connectivity", sa.Text(), nullable=False),
        sa.Column("operating_model", sa.Text(), nullable=False),
        sa.Column("autonomy_mode", sa.Text(), nullable=False),
        sa.Column("load_mode", sa.Text(), nullable=False),
        sa.Column("model_policy", sa.Text(), nullable=False),
        sa.Column("data_egress_policy", sa.Text(), nullable=False),
        sa.Column("max_auto_risk", sa.Text(), nullable=False),
        sa.Column("active_validation", sa.Text(), nullable=False),
        sa.Column("scope_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column(
            "capability_allowlist", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "required_sensor_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "active_validation IN ('DISABLED', 'ISOLATED_ONLY', 'SCOPED_PREAPPROVED')",
            name=op.f("ck_environments_environments_active_validation_enum"),
        ),
        sa.CheckConstraint(
            "asset_domain IN ('IT', 'OT', 'MIXED')",
            name=op.f("ck_environments_environments_asset_domain_enum"),
        ),
        sa.CheckConstraint(
            "autonomy_mode IN ('OBSERVE_ONLY', 'ASSISTED', 'CONTROLLED_AUTONOMY', 'VALIDATION')",
            name=op.f("ck_environments_environments_autonomy_mode_enum"),
        ),
        sa.CheckConstraint(
            "connectivity <> 'AIR_GAPPED' OR (model_policy = 'LOCAL_ONLY' AND data_egress_policy = 'DENY')",
            name=op.f("ck_environments_airgap_egress"),
        ),
        sa.CheckConstraint(
            "connectivity IN ('CONNECTED', 'RESTRICTED', 'AIR_GAPPED')",
            name=op.f("ck_environments_environments_connectivity_enum"),
        ),
        sa.CheckConstraint(
            "data_egress_policy IN ('DENY', 'REDACT_THEN_ALLOW', 'ALLOW')",
            name=op.f("ck_environments_environments_data_egress_policy_enum"),
        ),
        sa.CheckConstraint(
            "deployment_stage <> 'PRODUCTION' OR asset_domain = 'IT' OR (autonomy_mode IN ('OBSERVE_ONLY','ASSISTED') AND active_validation = 'DISABLED')",
            name=op.f("ck_environments_ot_production_passive"),
        ),
        sa.CheckConstraint(
            "deployment_stage IN ('LAB', 'PILOT', 'PRODUCTION')",
            name=op.f("ck_environments_environments_deployment_stage_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(capability_allowlist) = 'array'",
            name=op.f("ck_environments_environments_capability_allowlist_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(required_sensor_ids) = 'array'",
            name=op.f("ck_environments_environments_required_sensor_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(scope_ids) = 'array'", name=op.f("ck_environments_environments_scope_ids_json")
        ),
        sa.CheckConstraint(
            "load_mode IN ('NORMAL', 'HIGH_LOAD', 'EMERGENCY')",
            name=op.f("ck_environments_environments_load_mode_enum"),
        ),
        sa.CheckConstraint("max_auto_risk <> 'R5'", name=op.f("ck_environments_environment_not_auto_r5")),
        sa.CheckConstraint(
            "max_auto_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')",
            name=op.f("ck_environments_environments_max_auto_risk_enum"),
        ),
        sa.CheckConstraint(
            "model_policy IN ('LOCAL_ONLY', 'HYBRID', 'CLOUD_ALLOWED')",
            name=op.f("ck_environments_environments_model_policy_enum"),
        ),
        sa.CheckConstraint(
            "operating_model IN ('SINGLE_ORG', 'SOC_MSSP')",
            name=op.f("ck_environments_environments_operating_model_enum"),
        ),
        sa.CheckConstraint(
            "length(environment_id) > 0", name=op.f("ck_environments_environments_environment_id_nonempty")
        ),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_environments_environments_row_version")),
        sa.PrimaryKeyConstraint("environment_id", name=op.f("pk_environments")),
    )
    op.create_table(
        "verification_specs",
        sa.Column("verification_spec_id", sa.Text(), nullable=False),
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("scenario_version", sa.Text(), nullable=False),
        sa.Column("objective_type", sa.Text(), nullable=False),
        sa.Column("checks", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("aggregation_rule", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(checks) = 'array'",
            name=op.f("ck_verification_specs_verification_specs_checks_json"),
        ),
        sa.CheckConstraint(
            "objective_type IN ('DETECTION', 'CONTAINMENT', 'REMEDIATION', 'RECOVERY', 'CLEANUP')",
            name=op.f("ck_verification_specs_verification_specs_objective_type_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(checks) >= 3",
            name=op.f("ck_verification_specs_verification_specs_checks_minitems"),
        ),
        sa.CheckConstraint(
            "length(verification_spec_id) > 0",
            name=op.f("ck_verification_specs_verification_specs_verification_spec_id_nonempty"),
        ),
        sa.PrimaryKeyConstraint("verification_spec_id", name=op.f("pk_verification_specs")),
    )
    op.create_table(
        "audit_entries",
        sa.Column("audit_id", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("object_kind", sa.Text(), nullable=False),
        sa.Column("object_id", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_entry_hash", sa.Text(), nullable=True),
        sa.Column("integrity_hash", sa.Text(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "actor_type IN ('HUMAN', 'SERVICE', 'MODEL', 'WORKER')",
            name=op.f("ck_audit_entries_audit_entries_actor_type_enum"),
        ),
        sa.CheckConstraint(
            "integrity_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_audit_entries_audit_entries_integrity_hash_pattern"),
        ),
        sa.CheckConstraint(
            "previous_entry_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_audit_entries_audit_entries_previous_entry_hash_pattern"),
        ),
        sa.CheckConstraint(
            "length(audit_id) > 0", name=op.f("ck_audit_entries_audit_entries_audit_id_nonempty")
        ),
        sa.CheckConstraint("sequence >= 1", name=op.f("ck_audit_entries_audit_sequence_positive")),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_audit_entries_environment"
        ),
        sa.PrimaryKeyConstraint("audit_id", name=op.f("pk_audit_entries")),
        sa.UniqueConstraint("environment_id", "audit_id", name="uq_audit_entries_environment_id"),
        sa.UniqueConstraint("environment_id", "integrity_hash", name="uq_audit_hash"),
        sa.UniqueConstraint("environment_id", "sequence", name="uq_audit_sequence"),
    )
    op.create_index("ix_audit_trace_time", "audit_entries", ["trace_id", "timestamp"], unique=False)
    op.create_table(
        "audit_heads",
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("integrity_hash", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(sequence = 0) = (integrity_hash IS NULL)", name=op.f("ck_audit_heads_head_empty_pair")
        ),
        sa.CheckConstraint("sequence >= 0", name=op.f("ck_audit_heads_sequence_nonnegative")),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["environments.environment_id"],
            name=op.f("fk_audit_heads_environment_id_environments"),
        ),
        sa.PrimaryKeyConstraint("environment_id", name=op.f("pk_audit_heads")),
    )
    op.create_table(
        "capability_health",
        sa.Column("capability_id", sa.Text(), nullable=False),
        sa.Column("capability_version", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("worker_pool", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("queue_depth", sa.Integer(), nullable=False),
        sa.Column("running_count", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "status IN ('UNVERIFIED', 'HEALTHY', 'DEGRADED', 'OFFLINE')",
            name=op.f("ck_capability_health_capability_health_status_enum"),
        ),
        sa.CheckConstraint(
            "latency_ms >= 0", name=op.f("ck_capability_health_capability_health_latency_ms_minimum")
        ),
        sa.CheckConstraint(
            "length(capability_id) > 0",
            name=op.f("ck_capability_health_capability_health_capability_id_nonempty"),
        ),
        sa.CheckConstraint(
            "length(capability_version) > 0",
            name=op.f("ck_capability_health_capability_health_capability_version_nonempty"),
        ),
        sa.CheckConstraint(
            "length(environment_id) > 0",
            name=op.f("ck_capability_health_capability_health_environment_id_nonempty"),
        ),
        sa.CheckConstraint(
            "length(worker_pool) > 0",
            name=op.f("ck_capability_health_capability_health_worker_pool_nonempty"),
        ),
        sa.CheckConstraint(
            "queue_depth >= 0", name=op.f("ck_capability_health_capability_health_queue_depth_minimum")
        ),
        sa.CheckConstraint(
            "row_version >= 1", name=op.f("ck_capability_health_capability_health_row_version")
        ),
        sa.CheckConstraint(
            "running_count >= 0", name=op.f("ck_capability_health_capability_health_running_count_minimum")
        ),
        sa.ForeignKeyConstraint(
            ["capability_id", "capability_version"],
            ["capabilities.capability_id", "capabilities.version"],
            name="fk_capability_health_capability",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_capability_health_environment"
        ),
        sa.PrimaryKeyConstraint(
            "capability_id",
            "capability_version",
            "environment_id",
            "worker_pool",
            name=op.f("pk_capability_health"),
        ),
    )
    op.create_table(
        "event_groups",
        sa.Column("group_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "member_event_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "grouping_keys", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "correlation_reasons", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "outlier_event_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("correlation_confidence", sa.Float(), nullable=False),
        sa.Column("rule_version", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(correlation_reasons) = 'array'",
            name=op.f("ck_event_groups_event_groups_correlation_reasons_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(grouping_keys) = 'object'",
            name=op.f("ck_event_groups_event_groups_grouping_keys_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(member_event_ids) = 'array'",
            name=op.f("ck_event_groups_event_groups_member_event_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(outlier_event_ids) = 'array'",
            name=op.f("ck_event_groups_event_groups_outlier_event_ids_json"),
        ),
        sa.CheckConstraint(
            "correlation_confidence <= 1",
            name=op.f("ck_event_groups_event_groups_correlation_confidence_maximum"),
        ),
        sa.CheckConstraint(
            "correlation_confidence >= 0",
            name=op.f("ck_event_groups_event_groups_correlation_confidence_minimum"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(correlation_reasons) >= 1",
            name=op.f("ck_event_groups_event_groups_correlation_reasons_minitems"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(member_event_ids) >= 1",
            name=op.f("ck_event_groups_event_groups_member_event_ids_minitems"),
        ),
        sa.CheckConstraint("last_seen_at >= first_seen_at", name=op.f("ck_event_groups_group_interval")),
        sa.CheckConstraint(
            "length(group_id) > 0", name=op.f("ck_event_groups_event_groups_group_id_nonempty")
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_event_groups_environment"
        ),
        sa.PrimaryKeyConstraint("group_id", name=op.f("pk_event_groups")),
        sa.UniqueConstraint("environment_id", "group_id", name="uq_event_groups_environment_id"),
    )
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.Column(
            "affected_asset_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "related_event_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "event_group_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("evidence_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("triaged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("investigation_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "open_action_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "residual_risks", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("closure_type", sa.Text(), nullable=True),
        sa.Column(
            "closure_evidence_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "(status = 'CLOSED' AND closure_type IS NOT NULL AND jsonb_array_length(closure_evidence_ids) > 0 AND closed_at IS NOT NULL) OR (status <> 'CLOSED' AND closure_type IS NULL)",
            name=op.f("ck_incidents_incident_closure"),
        ),
        sa.CheckConstraint(
            "closure_type IN ('CLOSED_REMEDIATED', 'CLOSED_FALSE_POSITIVE', 'CLOSED_DUPLICATE', 'CLOSED_ACCEPTED_RISK')",
            name=op.f("ck_incidents_incidents_closure_type_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(affected_asset_ids) = 'array'",
            name=op.f("ck_incidents_incidents_affected_asset_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(closure_evidence_ids) = 'array'",
            name=op.f("ck_incidents_incidents_closure_evidence_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(event_group_ids) = 'array'",
            name=op.f("ck_incidents_incidents_event_group_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_ids) = 'array'", name=op.f("ck_incidents_incidents_evidence_ids_json")
        ),
        sa.CheckConstraint(
            "jsonb_typeof(open_action_ids) = 'array'",
            name=op.f("ck_incidents_incidents_open_action_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(related_event_ids) = 'array'",
            name=op.f("ck_incidents_incidents_related_event_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(residual_risks) = 'array'", name=op.f("ck_incidents_incidents_residual_risks_json")
        ),
        sa.CheckConstraint(
            "priority IN ('P0', 'P1', 'P2', 'P3', 'P4')", name=op.f("ck_incidents_incidents_priority_enum")
        ),
        sa.CheckConstraint(
            "status IN ('NEW', 'TRIAGED', 'INVESTIGATING', 'PLANNED', 'WAITING_APPROVAL', 'EXECUTING', 'VERIFYING', 'CONTAINED', 'RESOLVED', 'CLOSED', 'HUMAN_REVIEW', 'REOPENED')",
            name=op.f("ck_incidents_incidents_status_enum"),
        ),
        sa.CheckConstraint(
            "created_at >= first_observed_at AND updated_at >= created_at",
            name=op.f("ck_incidents_incident_interval"),
        ),
        sa.CheckConstraint(
            "length(incident_id) > 0", name=op.f("ck_incidents_incidents_incident_id_nonempty")
        ),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_incidents_incidents_row_version")),
        sa.CheckConstraint("state_version >= 1", name=op.f("ck_incidents_incidents_state_version_minimum")),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_incidents_environment"
        ),
        sa.PrimaryKeyConstraint("incident_id", name=op.f("pk_incidents")),
        sa.UniqueConstraint("environment_id", "incident_id", name="uq_incidents_environment_id"),
    )
    op.create_index(
        "ix_incident_env_status", "incidents", ["environment_id", "status", "priority"], unique=False
    )
    op.create_table(
        "outbox",
        sa.Column("message_id", sa.Text(), nullable=False),
        sa.Column("aggregate_type", sa.Text(), nullable=False),
        sa.Column("aggregate_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("lease_owner", sa.Text(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generation", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "(lease_owner IS NULL) = (lease_until IS NULL)", name=op.f("ck_outbox_outbox_lease_pair")
        ),
        sa.CheckConstraint("attempt_count >= 0", name=op.f("ck_outbox_outbox_attempt_count_minimum")),
        sa.CheckConstraint("generation >= 0", name=op.f("ck_outbox_outbox_generation")),
        sa.CheckConstraint("length(message_id) > 0", name=op.f("ck_outbox_outbox_message_id_nonempty")),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_outbox_outbox_row_version")),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_outbox_environment"
        ),
        sa.PrimaryKeyConstraint("message_id", name=op.f("pk_outbox")),
        sa.UniqueConstraint(
            "environment_id", "aggregate_type", "aggregate_id", "event_type", name="uq_outbox_aggregate_event"
        ),
    )
    op.create_index(
        "ix_outbox_pending",
        "outbox",
        ["available_at", "created_at"],
        unique=False,
        postgresql_where=sa.text("published_at IS NULL"),
    )
    op.create_table(
        "policy_snapshots",
        sa.Column("policy_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("high_impact_requires_human", sa.Boolean(), nullable=False),
        sa.Column("r5_auto_allowed", sa.Boolean(), nullable=False),
        sa.Column("load_can_expand_permissions", sa.Boolean(), nullable=False),
        sa.Column(
            "allowed_capability_ids",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_replans", sa.Integer(), nullable=False),
        sa.Column("max_model_calls", sa.Integer(), nullable=False),
        sa.Column("max_active_calls", sa.Integer(), nullable=False),
        sa.Column("max_elapsed_seconds", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(allowed_capability_ids) = 'array'",
            name=op.f("ck_policy_snapshots_policy_snapshots_allowed_capability_ids_json"),
        ),
        sa.CheckConstraint(
            "high_impact_requires_human IS TRUE",
            name=op.f("ck_policy_snapshots_policy_snapshots_high_impact_requires_human_const"),
        ),
        sa.CheckConstraint(
            "length(environment_id) > 0",
            name=op.f("ck_policy_snapshots_policy_snapshots_environment_id_nonempty"),
        ),
        sa.CheckConstraint(
            "length(policy_id) > 0", name=op.f("ck_policy_snapshots_policy_snapshots_policy_id_nonempty")
        ),
        sa.CheckConstraint(
            "length(version) > 0", name=op.f("ck_policy_snapshots_policy_snapshots_version_nonempty")
        ),
        sa.CheckConstraint(
            "load_can_expand_permissions IS FALSE",
            name=op.f("ck_policy_snapshots_policy_snapshots_load_can_expand_permissions_const"),
        ),
        sa.CheckConstraint(
            "max_active_calls >= 1",
            name=op.f("ck_policy_snapshots_policy_snapshots_max_active_calls_minimum"),
        ),
        sa.CheckConstraint(
            "max_elapsed_seconds >= 1",
            name=op.f("ck_policy_snapshots_policy_snapshots_max_elapsed_seconds_minimum"),
        ),
        sa.CheckConstraint(
            "max_model_calls >= 1", name=op.f("ck_policy_snapshots_policy_snapshots_max_model_calls_minimum")
        ),
        sa.CheckConstraint(
            "max_replans >= 0", name=op.f("ck_policy_snapshots_policy_snapshots_max_replans_minimum")
        ),
        sa.CheckConstraint(
            "r5_auto_allowed IS FALSE",
            name=op.f("ck_policy_snapshots_policy_snapshots_r5_auto_allowed_const"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_policy_snapshots_environment"
        ),
        sa.PrimaryKeyConstraint("policy_id", "version", "environment_id", name=op.f("pk_policy_snapshots")),
    )
    op.create_table(
        "resources",
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("binding_version", sa.Integer(), nullable=False),
        sa.Column("locator", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "(resource_type <> 'NETWORK_ENDPOINT' OR (locator ?& ARRAY['address','port','protocol'] AND (locator->>'port')::integer BETWEEN 1 AND 65535 AND locator->>'protocol' IN ('TCP','UDP'))) AND (resource_type <> 'IDENTITY' OR locator ?| ARRAY['object_id','account_name']) AND (resource_type <> 'KUBERNETES' OR locator ?& ARRAY['cluster_uid','kind','name']) AND (resource_type <> 'CLOUD' OR locator ?& ARRAY['provider','resource_id'])",
            name=op.f("ck_resources_resource_locator_required"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(locator) = 'object'", name=op.f("ck_resources_resources_locator_json")
        ),
        sa.CheckConstraint(
            "resource_type IN ('NETWORK_ENDPOINT', 'HOST', 'IDENTITY', 'KUBERNETES', 'CLOUD', 'SAAS', 'SECURITY_CONTROL')",
            name=op.f("ck_resources_resources_resource_type_enum"),
        ),
        sa.CheckConstraint(
            "binding_version >= 1", name=op.f("ck_resources_resources_binding_version_minimum")
        ),
        sa.CheckConstraint(
            "length(environment_id) > 0", name=op.f("ck_resources_resources_environment_id_nonempty")
        ),
        sa.CheckConstraint(
            "length(resource_id) > 0", name=op.f("ck_resources_resources_resource_id_nonempty")
        ),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_resources_resources_row_version")),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_resources_environment"
        ),
        sa.PrimaryKeyConstraint("resource_id", "environment_id", name=op.f("pk_resources")),
    )
    op.create_index("ix_resources_type", "resources", ["environment_id", "resource_type"], unique=False)
    op.create_table(
        "scopes",
        sa.Column("scope_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column(
            "source_resource_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "target_resource_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "capability_source_ids",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "allowed_capabilities", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "network_constraints", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_requests_per_second", sa.Float(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(allowed_capabilities) = 'array'",
            name=op.f("ck_scopes_scopes_allowed_capabilities_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(capability_source_ids) = 'object'",
            name=op.f("ck_scopes_scopes_capability_source_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(network_constraints) = 'array'",
            name=op.f("ck_scopes_scopes_network_constraints_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_resource_ids) = 'array'",
            name=op.f("ck_scopes_scopes_source_resource_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(target_resource_ids) = 'array'",
            name=op.f("ck_scopes_scopes_target_resource_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(allowed_capabilities) >= 1",
            name=op.f("ck_scopes_scopes_allowed_capabilities_minitems"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(source_resource_ids) >= 1",
            name=op.f("ck_scopes_scopes_source_resource_ids_minitems"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(target_resource_ids) >= 1",
            name=op.f("ck_scopes_scopes_target_resource_ids_minitems"),
        ),
        sa.CheckConstraint(
            "length(environment_id) > 0", name=op.f("ck_scopes_scopes_environment_id_nonempty")
        ),
        sa.CheckConstraint("length(scope_id) > 0", name=op.f("ck_scopes_scopes_scope_id_nonempty")),
        sa.CheckConstraint(
            "max_requests_per_second > 0",
            name=op.f("ck_scopes_scopes_max_requests_per_second_exclusiveMinimum"),
        ),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_scopes_scopes_row_version")),
        sa.CheckConstraint("valid_until > valid_from", name=op.f("ck_scopes_scope_interval")),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_scopes_environment"
        ),
        sa.PrimaryKeyConstraint("scope_id", "environment_id", name=op.f("pk_scopes")),
    )
    op.create_index("ix_scopes_expiry", "scopes", ["environment_id", "valid_until"], unique=False)
    op.create_table(
        "sensor_health",
        sa.Column("sensor_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lag_seconds", sa.Float(), nullable=False),
        sa.Column("lost_event_count", sa.Integer(), nullable=False),
        sa.Column(
            "coverage_scope_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("coverage_validated", sa.Boolean(), nullable=False),
        sa.Column("config_version", sa.Text(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(coverage_scope_ids) = 'array'",
            name=op.f("ck_sensor_health_sensor_health_coverage_scope_ids_json"),
        ),
        sa.CheckConstraint(
            "status IN ('HEALTHY', 'DEGRADED', 'OFFLINE', 'UNKNOWN')",
            name=op.f("ck_sensor_health_sensor_health_status_enum"),
        ),
        sa.CheckConstraint(
            "lag_seconds >= 0", name=op.f("ck_sensor_health_sensor_health_lag_seconds_minimum")
        ),
        sa.CheckConstraint(
            "length(environment_id) > 0", name=op.f("ck_sensor_health_sensor_health_environment_id_nonempty")
        ),
        sa.CheckConstraint(
            "length(sensor_id) > 0", name=op.f("ck_sensor_health_sensor_health_sensor_id_nonempty")
        ),
        sa.CheckConstraint(
            "lost_event_count >= 0", name=op.f("ck_sensor_health_sensor_health_lost_event_count_minimum")
        ),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_sensor_health_sensor_health_row_version")),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_sensor_health_environment"
        ),
        sa.PrimaryKeyConstraint("sensor_id", "environment_id", name=op.f("pk_sensor_health")),
    )
    op.create_table(
        "state_entities",
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("attributes", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("claim_kind", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "claim_kind IN ('OBSERVATION', 'INFERENCE', 'HUMAN_REVIEW')",
            name=op.f("ck_state_entities_state_entities_claim_kind_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(attributes) = 'object'",
            name=op.f("ck_state_entities_state_entities_attributes_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_ids) = 'array'",
            name=op.f("ck_state_entities_state_entities_evidence_ids_json"),
        ),
        sa.CheckConstraint(
            "length(entity_id) > 0", name=op.f("ck_state_entities_state_entities_entity_id_nonempty")
        ),
        sa.CheckConstraint(
            "length(environment_id) > 0",
            name=op.f("ck_state_entities_state_entities_environment_id_nonempty"),
        ),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_state_entities_state_entities_row_version")),
        sa.CheckConstraint(
            "state_version >= 1", name=op.f("ck_state_entities_state_entities_state_version_minimum")
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_state_entities_environment"
        ),
        sa.PrimaryKeyConstraint("entity_id", "environment_id", name=op.f("pk_state_entities")),
    )
    op.create_table(
        "context_bundles",
        sa.Column("context_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column(
            "excluded_evidence_reasons",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "unresolved_conflicts", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "sensor_health_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "capability_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("data_classification", sa.Text(), nullable=False),
        sa.Column("egress_allowed", sa.Boolean(), nullable=False),
        sa.Column("summary_version", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "data_classification IN ('PUBLIC', 'INTERNAL', 'SENSITIVE', 'RESTRICTED')",
            name=op.f("ck_context_bundles_context_bundles_data_classification_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(capability_ids) = 'array'",
            name=op.f("ck_context_bundles_context_bundles_capability_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_ids) = 'array'",
            name=op.f("ck_context_bundles_context_bundles_evidence_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(excluded_evidence_reasons) = 'object'",
            name=op.f("ck_context_bundles_context_bundles_excluded_evidence_reasons_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(sensor_health_ids) = 'array'",
            name=op.f("ck_context_bundles_context_bundles_sensor_health_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(unresolved_conflicts) = 'array'",
            name=op.f("ck_context_bundles_context_bundles_unresolved_conflicts_json"),
        ),
        sa.CheckConstraint(
            "length(context_id) > 0", name=op.f("ck_context_bundles_context_bundles_context_id_nonempty")
        ),
        sa.CheckConstraint(
            "state_version >= 1", name=op.f("ck_context_bundles_context_bundles_state_version_minimum")
        ),
        sa.CheckConstraint(
            "token_budget > 0", name=op.f("ck_context_bundles_context_bundles_token_budget_exclusiveMinimum")
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_context_bundles_incident",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_context_bundles_environment"
        ),
        sa.PrimaryKeyConstraint("context_id", name=op.f("pk_context_bundles")),
        sa.UniqueConstraint("environment_id", "context_id", name="uq_context_bundles_environment_id"),
        sa.UniqueConstraint("environment_id", "incident_id", "context_id", name="uq_context_incident"),
    )
    op.create_table(
        "correlation_decisions",
        sa.Column("decision_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column(
            "input_event_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("output_group_id", sa.Text(), nullable=False),
        sa.Column("rules_fired", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("merge_reason", sa.Text(), nullable=False),
        sa.Column(
            "excluded_event_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("decision_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(excluded_event_ids) = 'array'",
            name=op.f("ck_correlation_decisions_correlation_decisions_excluded_event_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(input_event_ids) = 'array'",
            name=op.f("ck_correlation_decisions_correlation_decisions_input_event_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(rules_fired) = 'array'",
            name=op.f("ck_correlation_decisions_correlation_decisions_rules_fired_json"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(input_event_ids) >= 1",
            name=op.f("ck_correlation_decisions_correlation_decisions_input_event_ids_minitems"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(rules_fired) >= 1",
            name=op.f("ck_correlation_decisions_correlation_decisions_rules_fired_minitems"),
        ),
        sa.CheckConstraint(
            "length(decision_id) > 0",
            name=op.f("ck_correlation_decisions_correlation_decisions_decision_id_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "output_group_id"],
            ["event_groups.environment_id", "event_groups.group_id"],
            name="fk_correlation_group",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_correlation_decisions_environment"
        ),
        sa.PrimaryKeyConstraint("decision_id", name=op.f("pk_correlation_decisions")),
        sa.UniqueConstraint("environment_id", "decision_id", name="uq_correlation_decisions_environment_id"),
    )
    op.create_table(
        "evidence",
        sa.Column("evidence_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column(
            "source_event_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("provenance_group", sa.Text(), nullable=False),
        sa.Column("claim_kind", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_ref", sa.Text(), nullable=False),
        sa.Column("integrity_hash", sa.Text(), nullable=False),
        sa.Column("hash_algorithm", sa.Text(), nullable=False),
        sa.Column("collector_id", sa.Text(), nullable=False),
        sa.Column("collection_method", sa.Text(), nullable=False),
        sa.Column("trust_status", sa.Text(), nullable=False),
        sa.Column("supports", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("contradicts", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("data_origin", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "claim_kind IN ('OBSERVATION', 'SOURCE_ASSERTION', 'INFERENCE', 'HUMAN_REVIEW')",
            name=op.f("ck_evidence_evidence_claim_kind_enum"),
        ),
        sa.CheckConstraint(
            "data_origin IN ('SYNTHETIC', 'OBSERVED')", name=op.f("ck_evidence_evidence_data_origin_enum")
        ),
        sa.CheckConstraint(
            "integrity_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_evidence_evidence_integrity_hash_pattern")
        ),
        sa.CheckConstraint(
            "jsonb_typeof(contradicts) = 'array'", name=op.f("ck_evidence_evidence_contradicts_json")
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_event_ids) = 'array'",
            name=op.f("ck_evidence_evidence_source_event_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(supports) = 'array'", name=op.f("ck_evidence_evidence_supports_json")
        ),
        sa.CheckConstraint(
            "trust_status IN ('VERIFIED_ORIGIN', 'UNVERIFIED_ORIGIN', 'CONFLICTED')",
            name=op.f("ck_evidence_evidence_trust_status_enum"),
        ),
        sa.CheckConstraint("length(evidence_id) > 0", name=op.f("ck_evidence_evidence_evidence_id_nonempty")),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_evidence_incident",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_evidence_environment"
        ),
        sa.PrimaryKeyConstraint("evidence_id", name=op.f("pk_evidence")),
        sa.UniqueConstraint("environment_id", "evidence_id", name="uq_evidence_environment_id"),
    )
    op.create_index("ix_evidence_incident_time", "evidence", ["incident_id", "observed_at"], unique=False)
    op.create_table(
        "scope_resources",
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "role IN ('SOURCE','TARGET')", name=op.f("ck_scope_resources_scope_resource_role")
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "resource_id"],
            ["resources.environment_id", "resources.resource_id"],
            name=op.f("fk_scope_resources_environment_id_resources"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name=op.f("fk_scope_resources_environment_id_scopes"),
        ),
        sa.PrimaryKeyConstraint(
            "environment_id", "scope_id", "resource_id", "role", name=op.f("pk_scope_resources")
        ),
    )
    op.create_table(
        "state_relations",
        sa.Column("relation_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("source_entity_id", sa.Text(), nullable=False),
        sa.Column("destination_entity_id", sa.Text(), nullable=False),
        sa.Column("relation_type", sa.Text(), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_ids) = 'array'",
            name=op.f("ck_state_relations_state_relations_evidence_ids_json"),
        ),
        sa.CheckConstraint(
            "length(environment_id) > 0",
            name=op.f("ck_state_relations_state_relations_environment_id_nonempty"),
        ),
        sa.CheckConstraint(
            "length(relation_id) > 0", name=op.f("ck_state_relations_state_relations_relation_id_nonempty")
        ),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_state_relations_state_relations_row_version")),
        sa.CheckConstraint(
            "state_version >= 1", name=op.f("ck_state_relations_state_relations_state_version_minimum")
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "destination_entity_id"],
            ["state_entities.environment_id", "state_entities.entity_id"],
            name="fk_relation_destination_entity_id",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "source_entity_id"],
            ["state_entities.environment_id", "state_entities.entity_id"],
            name="fk_relation_source_entity_id",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_state_relations_environment"
        ),
        sa.PrimaryKeyConstraint("relation_id", "environment_id", name=op.f("pk_state_relations")),
    )
    op.create_table(
        "tasks",
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("dependencies", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("capability_id", sa.Text(), nullable=False),
        sa.Column("capability_version", sa.Text(), nullable=False),
        sa.Column(
            "target_resource_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("scope_id", sa.Text(), nullable=False),
        sa.Column("parameters", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_lease_id", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(dependencies) = 'array'", name=op.f("ck_tasks_tasks_dependencies_json")
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_ids) = 'array'", name=op.f("ck_tasks_tasks_evidence_ids_json")
        ),
        sa.CheckConstraint(
            "jsonb_typeof(parameters) = 'object'", name=op.f("ck_tasks_tasks_parameters_json")
        ),
        sa.CheckConstraint(
            "jsonb_typeof(target_resource_ids) = 'array'",
            name=op.f("ck_tasks_tasks_target_resource_ids_json"),
        ),
        sa.CheckConstraint(
            "priority IN ('P0', 'P1', 'P2', 'P3', 'P4')", name=op.f("ck_tasks_tasks_priority_enum")
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'BLOCKED', 'WAITING_APPROVAL', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'TIMED_OUT')",
            name=op.f("ck_tasks_tasks_status_enum"),
        ),
        sa.CheckConstraint("attempt_count <= 10", name=op.f("ck_tasks_tasks_attempt_count_maximum")),
        sa.CheckConstraint("attempt_count <= max_attempts", name=op.f("ck_tasks_task_attempt_budget")),
        sa.CheckConstraint("attempt_count >= 0", name=op.f("ck_tasks_tasks_attempt_count_minimum")),
        sa.CheckConstraint(
            "jsonb_array_length(target_resource_ids) >= 1",
            name=op.f("ck_tasks_tasks_target_resource_ids_minitems"),
        ),
        sa.CheckConstraint("length(task_id) > 0", name=op.f("ck_tasks_tasks_task_id_nonempty")),
        sa.CheckConstraint("max_attempts <= 10", name=op.f("ck_tasks_tasks_max_attempts_maximum")),
        sa.CheckConstraint("max_attempts >= 1", name=op.f("ck_tasks_tasks_max_attempts_minimum")),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_tasks_tasks_row_version")),
        sa.CheckConstraint(
            "timeout_seconds > 0", name=op.f("ck_tasks_tasks_timeout_seconds_exclusiveMinimum")
        ),
        sa.ForeignKeyConstraint(
            ["capability_id", "capability_version"],
            ["capabilities.capability_id", "capabilities.version"],
            name="fk_tasks_capability",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_tasks_incident",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_tasks_scope",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_tasks_environment"
        ),
        sa.PrimaryKeyConstraint("task_id", name=op.f("pk_tasks")),
        sa.UniqueConstraint("environment_id", "incident_id", "task_id", name="uq_task_incident"),
        sa.UniqueConstraint("environment_id", "task_id", name="uq_tasks_environment_id"),
    )
    op.create_index("ix_tasks_dispatch", "tasks", ["status", "priority", "queued_at"], unique=False)
    op.create_table(
        "validation_scenarios",
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("implementation_status", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=False),
        sa.Column(
            "preconditions", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "trigger_steps", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "expected_events", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("verification_spec_id", sa.Text(), nullable=False),
        sa.Column(
            "cleanup_steps", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "stop_conditions", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("config_is_measured_performance", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "implementation_status IN ('DESIGN_ONLY', 'LAB_VERIFIED')",
            name=op.f("ck_validation_scenarios_validation_scenarios_implementation_status_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(cleanup_steps) = 'array'",
            name=op.f("ck_validation_scenarios_validation_scenarios_cleanup_steps_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(expected_events) = 'array'",
            name=op.f("ck_validation_scenarios_validation_scenarios_expected_events_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(preconditions) = 'array'",
            name=op.f("ck_validation_scenarios_validation_scenarios_preconditions_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(stop_conditions) = 'array'",
            name=op.f("ck_validation_scenarios_validation_scenarios_stop_conditions_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(trigger_steps) = 'array'",
            name=op.f("ck_validation_scenarios_validation_scenarios_trigger_steps_json"),
        ),
        sa.CheckConstraint(
            "config_is_measured_performance IS FALSE",
            name=op.f("ck_validation_scenarios_validation_scenarios_config_is_measured_perfo_const"),
        ),
        sa.CheckConstraint(
            "length(scenario_id) > 0",
            name=op.f("ck_validation_scenarios_validation_scenarios_scenario_id_nonempty"),
        ),
        sa.CheckConstraint(
            "length(version) > 0", name=op.f("ck_validation_scenarios_validation_scenarios_version_nonempty")
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_validation_scenarios_scope",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_validation_scenarios_environment"
        ),
        sa.PrimaryKeyConstraint("scenario_id", "version", name=op.f("pk_validation_scenarios")),
        sa.UniqueConstraint(
            "environment_id", "scenario_id", "version", name="uq_scenario_environment_version"
        ),
    )
    op.create_table(
        "action_requests",
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("capability_id", sa.Text(), nullable=False),
        sa.Column("capability_version", sa.Text(), nullable=False),
        sa.Column("source", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
        sa.Column("target", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("parameters", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=False),
        sa.Column("scope_version", sa.Text(), nullable=False),
        sa.Column("environment_profile_version", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("expected_state_version", sa.Integer(), nullable=False),
        sa.Column(
            "preconditions", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("evidence_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("ownership_tag", sa.Text(), nullable=False),
        sa.Column("rollback_policy_id", sa.Text(), nullable=False),
        sa.Column("action_digest", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "action_digest ~ '^[0-9a-f]{64}$'", name=op.f("ck_action_requests_action_digest_format")
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_ids) = 'array'",
            name=op.f("ck_action_requests_action_requests_evidence_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(parameters) = 'object'",
            name=op.f("ck_action_requests_action_requests_parameters_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(preconditions) = 'array'",
            name=op.f("ck_action_requests_action_requests_preconditions_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source) = 'object'", name=op.f("ck_action_requests_action_requests_source_json")
        ),
        sa.CheckConstraint(
            "jsonb_typeof(target) = 'object'", name=op.f("ck_action_requests_action_requests_target_json")
        ),
        sa.CheckConstraint(
            "target->>'environment_id' = environment_id AND (source IS NULL OR source->>'environment_id' = environment_id)",
            name=op.f("ck_action_requests_action_resource_environment"),
        ),
        sa.CheckConstraint(
            "expected_state_version >= 1",
            name=op.f("ck_action_requests_action_requests_expected_state_version_minimum"),
        ),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_action_requests_action_interval")),
        sa.CheckConstraint(
            "jsonb_array_length(evidence_ids) >= 1",
            name=op.f("ck_action_requests_action_requests_evidence_ids_minitems"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(preconditions) >= 1",
            name=op.f("ck_action_requests_action_requests_preconditions_minitems"),
        ),
        sa.CheckConstraint(
            "length(action_id) > 0", name=op.f("ck_action_requests_action_requests_action_id_nonempty")
        ),
        sa.CheckConstraint(
            "ttl_seconds >= 0", name=op.f("ck_action_requests_action_requests_ttl_seconds_minimum")
        ),
        sa.ForeignKeyConstraint(
            ["capability_id", "capability_version"],
            ["capabilities.capability_id", "capabilities.version"],
            name="fk_action_requests_capability",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id", "task_id"],
            ["tasks.environment_id", "tasks.incident_id", "tasks.task_id"],
            name="fk_action_task",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_action_requests_incident",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_action_requests_scope",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_action_requests_environment"
        ),
        sa.PrimaryKeyConstraint("action_id", name=op.f("pk_action_requests")),
        sa.UniqueConstraint("action_id", "action_digest", name="uq_action_digest"),
        sa.UniqueConstraint("environment_id", "action_id", name="uq_action_requests_environment_id"),
        sa.UniqueConstraint("environment_id", "idempotency_key", name="uq_action_idempotency"),
        sa.UniqueConstraint("environment_id", "incident_id", "action_id", name="uq_action_incident"),
    )
    op.create_table(
        "model_runs",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("model_revision", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("context_id", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("output_hash", sa.Text(), nullable=False),
        sa.Column("route_reason", sa.Text(), nullable=False),
        sa.Column("fallback_from_run_id", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cached_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("schema_valid", sa.Boolean(), nullable=False),
        sa.Column("safety_status", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_model_runs_model_runs_input_hash_pattern")
        ),
        sa.CheckConstraint(
            "output_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_model_runs_model_runs_output_hash_pattern")
        ),
        sa.CheckConstraint(
            "safety_status IN ('PASS', 'REJECTED', 'DEGRADED')",
            name=op.f("ck_model_runs_model_runs_safety_status_enum"),
        ),
        sa.CheckConstraint("cached_tokens >= 0", name=op.f("ck_model_runs_model_runs_cached_tokens_minimum")),
        sa.CheckConstraint("cost_usd >= 0", name=op.f("ck_model_runs_model_runs_cost_usd_minimum")),
        sa.CheckConstraint("input_tokens >= 0", name=op.f("ck_model_runs_model_runs_input_tokens_minimum")),
        sa.CheckConstraint("latency_ms >= 0", name=op.f("ck_model_runs_model_runs_latency_ms_minimum")),
        sa.CheckConstraint("length(run_id) > 0", name=op.f("ck_model_runs_model_runs_run_id_nonempty")),
        sa.CheckConstraint("output_tokens >= 0", name=op.f("ck_model_runs_model_runs_output_tokens_minimum")),
        sa.ForeignKeyConstraint(
            ["environment_id", "fallback_from_run_id"],
            ["model_runs.environment_id", "model_runs.run_id"],
            name="fk_model_fallback",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id", "context_id"],
            ["context_bundles.environment_id", "context_bundles.incident_id", "context_bundles.context_id"],
            name="fk_model_context",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id", "task_id"],
            ["tasks.environment_id", "tasks.incident_id", "tasks.task_id"],
            name="fk_model_task",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_model_runs_incident",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_model_runs_environment"
        ),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_model_runs")),
        sa.UniqueConstraint("environment_id", "run_id", name="uq_model_runs_environment_id"),
    )
    op.create_table(
        "validation_runs",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("scenario_version", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=False),
        sa.Column("registered_by", sa.Text(), nullable=False),
        sa.Column("trusted_registration", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "expected_event_types", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "allowed_side_effects", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("cleanup_policy_id", sa.Text(), nullable=False),
        sa.Column("data_origin", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "data_origin IN ('SYNTHETIC', 'OBSERVED')",
            name=op.f("ck_validation_runs_validation_runs_data_origin_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(allowed_side_effects) = 'array'",
            name=op.f("ck_validation_runs_validation_runs_allowed_side_effects_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(expected_event_types) = 'array'",
            name=op.f("ck_validation_runs_validation_runs_expected_event_types_json"),
        ),
        sa.CheckConstraint(
            "length(run_id) > 0", name=op.f("ck_validation_runs_validation_runs_run_id_nonempty")
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "scenario_id", "scenario_version"],
            [
                "validation_scenarios.environment_id",
                "validation_scenarios.scenario_id",
                "validation_scenarios.version",
            ],
            name="fk_run_scenario",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_validation_runs_scope",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_validation_runs_environment"
        ),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_validation_runs")),
        sa.UniqueConstraint("environment_id", "run_id", name="uq_validation_runs_environment_id"),
    )
    op.create_table(
        "worker_leases",
        sa.Column("lease_id", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("renewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "expires_at > acquired_at AND (renewed_at IS NULL OR renewed_at >= acquired_at)",
            name=op.f("ck_worker_leases_lease_interval"),
        ),
        sa.CheckConstraint("generation >= 1", name=op.f("ck_worker_leases_worker_leases_generation_minimum")),
        sa.CheckConstraint(
            "length(lease_id) > 0", name=op.f("ck_worker_leases_worker_leases_lease_id_nonempty")
        ),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_worker_leases_worker_leases_row_version")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.task_id"], name="fk_lease_task"),
        sa.PrimaryKeyConstraint("lease_id", name=op.f("pk_worker_leases")),
        sa.UniqueConstraint("task_id", "generation", name="uq_task_lease_generation"),
        sa.UniqueConstraint("task_id", "lease_id", name="uq_task_lease_id"),
    )
    op.create_index("ix_leases_expiry", "worker_leases", ["expires_at"], unique=False)
    op.create_table(
        "action_attempts",
        sa.Column("attempt_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("fencing_generation", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_receipt_id", sa.Text(), nullable=True),
        sa.Column("reconciliation_state", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_class", sa.Text(), nullable=True),
        sa.Column("device_response_hash", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "device_response_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_action_attempts_action_attempts_device_response_hash_pattern"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_ids) = 'array'",
            name=op.f("ck_action_attempts_action_attempts_evidence_ids_json"),
        ),
        sa.CheckConstraint(
            "reconciliation_state IN ('NOT_NEEDED', 'PENDING', 'CONFIRMED_APPLIED', 'CONFIRMED_NOT_APPLIED', 'PARTIAL', 'UNKNOWN')",
            name=op.f("ck_action_attempts_action_attempts_reconciliation_state_enum"),
        ),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'WAITING_APPROVAL', 'AUTHORIZED', 'DISPATCHED', 'EXECUTING', 'EXECUTED', 'EXECUTION_UNKNOWN', 'RECONCILING', 'COMPENSATING', 'COMPENSATED', 'COMPENSATION_FAILED', 'NEEDS_MANUAL', 'DENIED', 'EXPIRED', 'CANCELLED', 'FAILED')",
            name=op.f("ck_action_attempts_action_attempts_status_enum"),
        ),
        sa.CheckConstraint(
            "fencing_generation >= 1",
            name=op.f("ck_action_attempts_action_attempts_fencing_generation_minimum"),
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name=op.f("ck_action_attempts_attempt_interval"),
        ),
        sa.CheckConstraint(
            "length(attempt_id) > 0", name=op.f("ck_action_attempts_action_attempts_attempt_id_nonempty")
        ),
        sa.CheckConstraint("row_version >= 1", name=op.f("ck_action_attempts_action_attempts_row_version")),
        sa.ForeignKeyConstraint(["action_id"], ["action_requests.action_id"], name="fk_attempt_action"),
        sa.PrimaryKeyConstraint("attempt_id", name=op.f("pk_action_attempts")),
    )
    op.create_index("ix_attempts_action_time", "action_attempts", ["action_id", "started_at"], unique=False)
    op.create_table(
        "approvals",
        sa.Column("approval_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("action_digest", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("actor_role", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action_digest ~ '^[0-9a-f]{64}$'", name=op.f("ck_approvals_approvals_action_digest_pattern")
        ),
        sa.CheckConstraint(
            "actor_role IN ('APPROVER', 'ADMIN')", name=op.f("ck_approvals_approvals_actor_role_enum")
        ),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')", name=op.f("ck_approvals_approvals_decision_enum")
        ),
        sa.CheckConstraint("expires_at > approved_at", name=op.f("ck_approvals_approval_interval")),
        sa.CheckConstraint(
            "length(approval_id) > 0", name=op.f("ck_approvals_approvals_approval_id_nonempty")
        ),
        sa.ForeignKeyConstraint(
            ["action_id", "action_digest"],
            ["action_requests.action_id", "action_requests.action_digest"],
            name="fk_approval_action_digest",
        ),
        sa.PrimaryKeyConstraint("approval_id", name=op.f("pk_approvals")),
        sa.UniqueConstraint("approval_id", "action_id", "action_digest", name="uq_approval_binding"),
    )
    op.create_table(
        "authorization_contexts",
        sa.Column("authorization_context_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("action_digest", sa.Text(), nullable=False),
        sa.Column("principal_id", sa.Text(), nullable=False),
        sa.Column("principal_role", sa.Text(), nullable=False),
        sa.Column("environment_profile_version", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=False),
        sa.Column("scope_version", sa.Text(), nullable=False),
        sa.Column("capability_id", sa.Text(), nullable=False),
        sa.Column("capability_version", sa.Text(), nullable=False),
        sa.Column("target_resource_id", sa.Text(), nullable=False),
        sa.Column("source_resource_id", sa.Text(), nullable=True),
        sa.Column("asset_criticality", sa.Text(), nullable=False),
        sa.Column("business_impact", sa.Text(), nullable=False),
        sa.Column("evidence_quality", sa.Text(), nullable=False),
        sa.Column("sensor_health_status", sa.Text(), nullable=False),
        sa.Column("autonomy_mode", sa.Text(), nullable=False),
        sa.Column("load_mode", sa.Text(), nullable=False),
        sa.Column("requested_risk", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("budget_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action_digest ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_authorization_contexts_authorization_contexts_action_digest_pattern"),
        ),
        sa.CheckConstraint(
            "asset_criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_authorization_contexts_authorization_contexts_asset_criticality_enum"),
        ),
        sa.CheckConstraint(
            "autonomy_mode IN ('OBSERVE_ONLY', 'ASSISTED', 'CONTROLLED_AUTONOMY', 'VALIDATION')",
            name=op.f("ck_authorization_contexts_authorization_contexts_autonomy_mode_enum"),
        ),
        sa.CheckConstraint(
            "business_impact IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_authorization_contexts_authorization_contexts_business_impact_enum"),
        ),
        sa.CheckConstraint(
            "evidence_quality IN ('LOW', 'MEDIUM', 'HIGH')",
            name=op.f("ck_authorization_contexts_authorization_contexts_evidence_quality_enum"),
        ),
        sa.CheckConstraint(
            "load_mode IN ('NORMAL', 'HIGH_LOAD', 'EMERGENCY')",
            name=op.f("ck_authorization_contexts_authorization_contexts_load_mode_enum"),
        ),
        sa.CheckConstraint(
            "requested_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')",
            name=op.f("ck_authorization_contexts_authorization_contexts_requested_risk_enum"),
        ),
        sa.CheckConstraint(
            "sensor_health_status IN ('HEALTHY', 'DEGRADED', 'UNKNOWN')",
            name=op.f("ck_authorization_contexts_authorization_contexts_sensor_health_status_enum"),
        ),
        sa.CheckConstraint(
            "length(authorization_context_id) > 0",
            name=op.f("ck_authorization_contexts_authorization_contexts_authorization_context__nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["action_id", "action_digest"],
            ["action_requests.action_id", "action_requests.action_digest"],
            name="fk_authctx_action_digest",
        ),
        sa.ForeignKeyConstraint(
            ["capability_id", "capability_version"],
            ["capabilities.capability_id", "capabilities.version"],
            name="fk_authorization_contexts_capability",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "action_id"],
            ["action_requests.environment_id", "action_requests.action_id"],
            name="fk_authctx_action_env",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_authorization_contexts_scope",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "source_resource_id"],
            ["resources.environment_id", "resources.resource_id"],
            name="fk_authctx_source_resource_id",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "target_resource_id"],
            ["resources.environment_id", "resources.resource_id"],
            name="fk_authctx_target_resource_id",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_authorization_contexts_environment"
        ),
        sa.PrimaryKeyConstraint("authorization_context_id", name=op.f("pk_authorization_contexts")),
        sa.UniqueConstraint(
            "authorization_context_id", "action_id", "action_digest", name="uq_authctx_binding"
        ),
        sa.UniqueConstraint(
            "environment_id", "authorization_context_id", name="uq_authorization_contexts_environment_id"
        ),
    )
    op.create_table(
        "normalized_events",
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("specversion", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("collector_id", sa.Text(), nullable=False),
        sa.Column("origin_event_id", sa.Text(), nullable=False),
        sa.Column("provenance_group", sa.Text(), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clock_status", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("activity_category", sa.Text(), nullable=False),
        sa.Column("activity_name", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("actor_resource_id", sa.Text(), nullable=True),
        sa.Column(
            "source_resource_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "target_resource_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("observables", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("severity_signal", sa.Integer(), nullable=False),
        sa.Column("raw_ref", sa.Text(), nullable=False),
        sa.Column("parser_version", sa.Text(), nullable=False),
        sa.Column("mapping_version", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("validation_run_id", sa.Text(), nullable=True),
        sa.Column("data_origin", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "clock_status IN ('TRUSTED', 'SKEWED', 'UNKNOWN')",
            name=op.f("ck_normalized_events_normalized_events_clock_status_enum"),
        ),
        sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_normalized_events_event_hash")),
        sa.CheckConstraint(
            "data_origin IN ('SYNTHETIC', 'OBSERVED')",
            name=op.f("ck_normalized_events_normalized_events_data_origin_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(observables) = 'array'",
            name=op.f("ck_normalized_events_normalized_events_observables_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_resource_ids) = 'array'",
            name=op.f("ck_normalized_events_normalized_events_source_resource_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(target_resource_ids) = 'array'",
            name=op.f("ck_normalized_events_normalized_events_target_resource_ids_json"),
        ),
        sa.CheckConstraint(
            "outcome IN ('SUCCESS', 'FAILURE', 'UNKNOWN', 'PARTIAL', 'DENIED')",
            name=op.f("ck_normalized_events_normalized_events_outcome_enum"),
        ),
        sa.CheckConstraint(
            "length(event_id) > 0", name=op.f("ck_normalized_events_normalized_events_event_id_nonempty")
        ),
        sa.CheckConstraint(
            "severity_signal <= 10",
            name=op.f("ck_normalized_events_normalized_events_severity_signal_maximum"),
        ),
        sa.CheckConstraint(
            "severity_signal >= 0",
            name=op.f("ck_normalized_events_normalized_events_severity_signal_minimum"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "actor_resource_id"],
            ["resources.environment_id", "resources.resource_id"],
            name="fk_event_actor",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "validation_run_id"],
            ["validation_runs.environment_id", "validation_runs.run_id"],
            name="fk_event_run",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_normalized_events_environment"
        ),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_normalized_events")),
        sa.UniqueConstraint(
            "environment_id",
            "collector_id",
            "source_type",
            "origin_event_id",
            "event_type",
            name="uq_event_origin",
        ),
        sa.UniqueConstraint("environment_id", "event_id", name="uq_normalized_events_environment_id"),
    )
    op.create_index(
        "ix_events_env_time", "normalized_events", ["environment_id", "source_timestamp"], unique=False
    )
    op.create_index(
        "ix_events_fingerprint", "normalized_events", ["environment_id", "fingerprint"], unique=False
    )
    op.create_index(
        "ix_events_provenance", "normalized_events", ["environment_id", "provenance_group"], unique=False
    )
    op.create_table(
        "plans",
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("context_id", sa.Text(), nullable=False),
        sa.Column("model_run_id", sa.Text(), nullable=True),
        sa.Column("hypotheses", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("tasks", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column(
            "stop_conditions", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("max_replans", sa.Integer(), nullable=False),
        sa.Column("total_model_calls", sa.Integer(), nullable=False),
        sa.CheckConstraint("jsonb_typeof(hypotheses) = 'array'", name=op.f("ck_plans_plans_hypotheses_json")),
        sa.CheckConstraint(
            "jsonb_typeof(stop_conditions) = 'array'", name=op.f("ck_plans_plans_stop_conditions_json")
        ),
        sa.CheckConstraint("jsonb_typeof(tasks) = 'array'", name=op.f("ck_plans_plans_tasks_json")),
        sa.CheckConstraint(
            "jsonb_array_length(hypotheses) >= 1", name=op.f("ck_plans_plans_hypotheses_minitems")
        ),
        sa.CheckConstraint(
            "jsonb_array_length(stop_conditions) >= 1", name=op.f("ck_plans_plans_stop_conditions_minitems")
        ),
        sa.CheckConstraint("jsonb_array_length(tasks) >= 1", name=op.f("ck_plans_plans_tasks_minitems")),
        sa.CheckConstraint("length(plan_id) > 0", name=op.f("ck_plans_plans_plan_id_nonempty")),
        sa.CheckConstraint("max_replans >= 0", name=op.f("ck_plans_plans_max_replans_minimum")),
        sa.CheckConstraint("total_model_calls >= 0", name=op.f("ck_plans_plans_total_model_calls_minimum")),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id", "context_id"],
            ["context_bundles.environment_id", "context_bundles.incident_id", "context_bundles.context_id"],
            name="fk_plan_context",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_plans_incident",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "model_run_id"],
            ["model_runs.environment_id", "model_runs.run_id"],
            name="fk_plan_model",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_plans_environment"
        ),
        sa.PrimaryKeyConstraint("plan_id", name=op.f("pk_plans")),
        sa.UniqueConstraint("environment_id", "plan_id", name="uq_plans_environment_id"),
    )
    op.create_table(
        "verification_results",
        sa.Column("verification_id", sa.Text(), nullable=False),
        sa.Column("verification_spec_id", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=True),
        sa.Column("validation_run_id", sa.Text(), nullable=False),
        sa.Column("objective_type", sa.Text(), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("target_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=False),
        sa.Column("scenario_version", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("security_status", sa.Text(), nullable=False),
        sa.Column("business_status", sa.Text(), nullable=False),
        sa.Column("observation_status", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.Column("expected_result", sa.Text(), nullable=False),
        sa.Column("observed_result", sa.Text(), nullable=False),
        sa.Column(
            "residual_risks", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False
        ),
        sa.Column("recommended_next_step", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "business_status IN ('PASS', 'FAIL', 'INCONCLUSIVE')",
            name=op.f("ck_verification_results_verification_results_business_status_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_ids) = 'array'",
            name=op.f("ck_verification_results_verification_results_evidence_ids_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(residual_risks) = 'array'",
            name=op.f("ck_verification_results_verification_results_residual_risks_json"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(target_ids) = 'array'",
            name=op.f("ck_verification_results_verification_results_target_ids_json"),
        ),
        sa.CheckConstraint(
            "objective_type IN ('DETECTION', 'CONTAINMENT', 'REMEDIATION', 'RECOVERY', 'CLEANUP')",
            name=op.f("ck_verification_results_verification_results_objective_type_enum"),
        ),
        sa.CheckConstraint(
            "observation_status IN ('PASS', 'FAIL', 'INCONCLUSIVE')",
            name=op.f("ck_verification_results_verification_results_observation_status_enum"),
        ),
        sa.CheckConstraint(
            "security_status IN ('PASS', 'FAIL', 'INCONCLUSIVE')",
            name=op.f("ck_verification_results_verification_results_security_status_enum"),
        ),
        sa.CheckConstraint(
            "status = CASE WHEN security_status = 'FAIL' OR business_status = 'FAIL' THEN 'FAIL' WHEN security_status = 'PASS' AND business_status = 'PASS' AND observation_status = 'PASS' THEN 'PASS' ELSE 'INCONCLUSIVE' END",
            name=op.f("ck_verification_results_verification_three_check"),
        ),
        sa.CheckConstraint(
            "status IN ('PASS', 'FAIL', 'INCONCLUSIVE')",
            name=op.f("ck_verification_results_verification_results_status_enum"),
        ),
        sa.CheckConstraint(
            "finished_at >= started_at AND valid_until >= finished_at",
            name=op.f("ck_verification_results_verification_interval"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(evidence_ids) >= 1",
            name=op.f("ck_verification_results_verification_results_evidence_ids_minitems"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(target_ids) >= 1",
            name=op.f("ck_verification_results_verification_results_target_ids_minitems"),
        ),
        sa.CheckConstraint(
            "length(verification_id) > 0",
            name=op.f("ck_verification_results_verification_results_verification_id_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id", "action_id"],
            ["action_requests.environment_id", "action_requests.incident_id", "action_requests.action_id"],
            name="fk_verification_action",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name="fk_verification_results_incident",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name="fk_verification_results_scope",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "validation_run_id"],
            ["validation_runs.environment_id", "validation_runs.run_id"],
            name="fk_verification_run",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.environment_id"], name="fk_verification_results_environment"
        ),
        sa.ForeignKeyConstraint(
            ["verification_spec_id"], ["verification_specs.verification_spec_id"], name="fk_verification_spec"
        ),
        sa.PrimaryKeyConstraint("verification_id", name=op.f("pk_verification_results")),
        sa.UniqueConstraint(
            "environment_id", "verification_id", name="uq_verification_results_environment_id"
        ),
    )
    op.create_table(
        "authorization_decisions",
        sa.Column("authorization_id", sa.Text(), nullable=False),
        sa.Column("authorization_context_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("action_digest", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("assessed_risk", sa.Text(), nullable=False),
        sa.Column("business_impact", sa.Text(), nullable=False),
        sa.Column("human_approval_required", sa.Boolean(), nullable=False),
        sa.Column("approval_id", sa.Text(), nullable=True),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reasons", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "(assessed_risk <> 'R5' AND business_impact NOT IN ('HIGH','CRITICAL')) OR human_approval_required",
            name=op.f("ck_authorization_decisions_high_impact_human"),
        ),
        sa.CheckConstraint(
            "action_digest ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_authorization_decisions_authorization_decisions_action_digest_pattern"),
        ),
        sa.CheckConstraint(
            "assessed_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')",
            name=op.f("ck_authorization_decisions_authorization_decisions_assessed_risk_enum"),
        ),
        sa.CheckConstraint(
            "business_impact IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_authorization_decisions_authorization_decisions_business_impact_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(reasons) = 'array'",
            name=op.f("ck_authorization_decisions_authorization_decisions_reasons_json"),
        ),
        sa.CheckConstraint(
            "outcome <> 'ALLOW' OR NOT human_approval_required OR approval_id IS NOT NULL",
            name=op.f("ck_authorization_decisions_allow_requires_approval"),
        ),
        sa.CheckConstraint(
            "outcome IN ('ALLOW', 'DENY', 'REQUIRE_APPROVAL', 'DOWNGRADE')",
            name=op.f("ck_authorization_decisions_authorization_decisions_outcome_enum"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(reasons) >= 1",
            name=op.f("ck_authorization_decisions_authorization_decisions_reasons_minitems"),
        ),
        sa.CheckConstraint(
            "length(authorization_id) > 0",
            name=op.f("ck_authorization_decisions_authorization_decisions_authorization_id_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["approval_id", "action_id", "action_digest"],
            ["approvals.approval_id", "approvals.action_id", "approvals.action_digest"],
            name="fk_decision_approval",
        ),
        sa.ForeignKeyConstraint(
            ["authorization_context_id", "action_id", "action_digest"],
            [
                "authorization_contexts.authorization_context_id",
                "authorization_contexts.action_id",
                "authorization_contexts.action_digest",
            ],
            name="fk_decision_context_binding",
        ),
        sa.PrimaryKeyConstraint("authorization_id", name=op.f("pk_authorization_decisions")),
    )
    op.create_table(
        "event_receipts",
        sa.Column("receipt_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("submitted_event_id", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("raw_ref", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submission_hash", sa.Text(), nullable=False),
        sa.Column("disposition", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "disposition IN ('ACCEPTED','DUPLICATE')", name=op.f("ck_event_receipts_receipt_disposition")
        ),
        sa.CheckConstraint("submission_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_event_receipts_receipt_hash")),
        sa.ForeignKeyConstraint(
            ["environment_id", "event_id"],
            ["normalized_events.environment_id", "normalized_events.event_id"],
            name=op.f("fk_event_receipts_environment_id_normalized_events"),
        ),
        sa.PrimaryKeyConstraint("receipt_id", name=op.f("pk_event_receipts")),
    )
    op.create_index("ix_receipts_event", "event_receipts", ["environment_id", "event_id"], unique=False)
    op.create_index("ix_receipts_trace", "event_receipts", ["trace_id"], unique=False)
    op.create_table(
        "event_resources",
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "role IN ('SOURCE','TARGET')", name=op.f("ck_event_resources_event_resource_role")
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "event_id"],
            ["normalized_events.environment_id", "normalized_events.event_id"],
            name=op.f("fk_event_resources_environment_id_normalized_events"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "resource_id"],
            ["resources.environment_id", "resources.resource_id"],
            name=op.f("fk_event_resources_environment_id_resources"),
        ),
        sa.PrimaryKeyConstraint(
            "environment_id", "event_id", "resource_id", "role", name=op.f("pk_event_resources")
        ),
    )
    op.create_foreign_key(
        "fk_task_active_lease",
        "tasks",
        "worker_leases",
        ["task_id", "active_lease_id"],
        ["task_id", "lease_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_foreign_key(
        "fk_spec_scenario",
        "verification_specs",
        "validation_scenarios",
        ["scenario_id", "scenario_version"],
        ["scenario_id", "version"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_foreign_key(
        "fk_scenario_spec",
        "validation_scenarios",
        "verification_specs",
        ["verification_spec_id"],
        ["verification_spec_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.execute("""CREATE FUNCTION zhiyu_reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'immutable record: %', TG_TABLE_NAME USING ERRCODE = '23514'; END;
        $$""")
    op.execute(
        "CREATE TRIGGER immutable_audit_entries BEFORE UPDATE OR DELETE ON audit_entries FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute(
        "CREATE TRIGGER immutable_event_receipts BEFORE UPDATE OR DELETE ON event_receipts FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute(
        "CREATE TRIGGER immutable_normalized_events BEFORE UPDATE OR DELETE ON normalized_events FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute(
        "CREATE TRIGGER immutable_action_requests BEFORE UPDATE OR DELETE ON action_requests FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute(
        "CREATE TRIGGER immutable_approvals BEFORE UPDATE OR DELETE ON approvals FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute(
        "CREATE TRIGGER immutable_authorization_contexts BEFORE UPDATE OR DELETE ON authorization_contexts FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute(
        "CREATE TRIGGER immutable_authorization_decisions BEFORE UPDATE OR DELETE ON authorization_decisions FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )

    op.create_check_constraint(
        op.f("ck_normalized_events_event_specversion"), "normalized_events", "specversion = '1.0'"
    )
    op.create_check_constraint(
        op.f("ck_evidence_evidence_hash_algorithm"), "evidence", "hash_algorithm = 'SHA256'"
    )
    op.create_check_constraint(
        op.f("ck_verification_specs_verification_aggregation"),
        "verification_specs",
        "aggregation_rule = 'THREE_DIMENSION_STRICT'",
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER immutable_audit_entries ON audit_entries")
    op.execute("DROP TRIGGER immutable_event_receipts ON event_receipts")
    op.execute("DROP TRIGGER immutable_normalized_events ON normalized_events")
    op.execute("DROP TRIGGER immutable_action_requests ON action_requests")
    op.execute("DROP TRIGGER immutable_approvals ON approvals")
    op.execute("DROP TRIGGER immutable_authorization_contexts ON authorization_contexts")
    op.execute("DROP TRIGGER immutable_authorization_decisions ON authorization_decisions")
    op.execute("DROP FUNCTION zhiyu_reject_mutation()")
    op.drop_constraint("fk_task_active_lease", "tasks", type_="foreignkey")
    op.drop_constraint("fk_spec_scenario", "verification_specs", type_="foreignkey")
    op.drop_constraint("fk_scenario_spec", "validation_scenarios", type_="foreignkey")
    op.drop_table("event_resources")
    op.drop_index("ix_receipts_trace", table_name="event_receipts")
    op.drop_index("ix_receipts_event", table_name="event_receipts")
    op.drop_table("event_receipts")
    op.drop_table("authorization_decisions")
    op.drop_table("verification_results")
    op.drop_table("plans")
    op.drop_index("ix_events_provenance", table_name="normalized_events")
    op.drop_index("ix_events_fingerprint", table_name="normalized_events")
    op.drop_index("ix_events_env_time", table_name="normalized_events")
    op.drop_table("normalized_events")
    op.drop_table("authorization_contexts")
    op.drop_table("approvals")
    op.drop_index("ix_attempts_action_time", table_name="action_attempts")
    op.drop_table("action_attempts")
    op.drop_index("ix_leases_expiry", table_name="worker_leases")
    op.drop_table("worker_leases")
    op.drop_table("validation_runs")
    op.drop_table("model_runs")
    op.drop_table("action_requests")
    op.drop_table("validation_scenarios")
    op.drop_index("ix_tasks_dispatch", table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("state_relations")
    op.drop_table("scope_resources")
    op.drop_index("ix_evidence_incident_time", table_name="evidence")
    op.drop_table("evidence")
    op.drop_table("correlation_decisions")
    op.drop_table("context_bundles")
    op.drop_table("state_entities")
    op.drop_table("sensor_health")
    op.drop_index("ix_scopes_expiry", table_name="scopes")
    op.drop_table("scopes")
    op.drop_index("ix_resources_type", table_name="resources")
    op.drop_table("resources")
    op.drop_table("policy_snapshots")
    op.drop_index("ix_outbox_pending", table_name="outbox", postgresql_where=sa.text("published_at IS NULL"))
    op.drop_table("outbox")
    op.drop_index("ix_incident_env_status", table_name="incidents")
    op.drop_table("incidents")
    op.drop_table("event_groups")
    op.drop_table("capability_health")
    op.drop_table("audit_heads")
    op.drop_index("ix_audit_trace_time", table_name="audit_entries")
    op.drop_table("audit_entries")
    op.drop_table("verification_specs")
    op.drop_table("environments")
    op.drop_table("capabilities")
