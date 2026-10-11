-- Generated through 0016_lab_remediation; historical SQL retained separately.

BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_m1_1

CREATE TABLE capabilities (
    capability_id TEXT NOT NULL, 
    version TEXT NOT NULL, 
    adapter TEXT NOT NULL, 
    base_risk TEXT NOT NULL, 
    operation_kind TEXT NOT NULL, 
    controller_location TEXT NOT NULL, 
    execution_location TEXT NOT NULL, 
    target_domain TEXT NOT NULL, 
    network_path TEXT NOT NULL, 
    cleanup_owner TEXT NOT NULL, 
    supported_os JSONB NOT NULL, 
    input_schema JSONB NOT NULL, 
    output_schema JSONB NOT NULL, 
    scope_required BOOLEAN NOT NULL, 
    timeout_seconds INTEGER NOT NULL, 
    idempotency TEXT NOT NULL, 
    reconciliation_method TEXT NOT NULL, 
    ttl_enforcement TEXT NOT NULL, 
    rollback_policy TEXT NOT NULL, 
    required_permissions JSONB NOT NULL, 
    required_secret_refs JSONB NOT NULL, 
    supports_cancel BOOLEAN NOT NULL, 
    supports_dry_run BOOLEAN NOT NULL, 
    resource_locks JSONB NOT NULL, 
    max_concurrency INTEGER NOT NULL, 
    expected_evidence_types JSONB NOT NULL, 
    verification_capability_id TEXT, 
    compensator_capability_id TEXT, 
    integration_status TEXT NOT NULL, 
    CONSTRAINT pk_capabilities PRIMARY KEY (capability_id, version), 
    CONSTRAINT ck_capabilities_capabilities_base_risk_enum CHECK (base_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')), 
    CONSTRAINT ck_capabilities_capabilities_idempotency_enum CHECK (idempotency IN ('NATIVE', 'ADAPTER_RECONCILE', 'NONE')), 
    CONSTRAINT ck_capabilities_capabilities_integration_status_enum CHECK (integration_status IN ('DESIGN', 'ADAPTED', 'LAB_VERIFIED', 'PRODUCTION_VERIFIED')), 
    CONSTRAINT ck_capabilities_capabilities_expected_evidence_types_json CHECK (jsonb_typeof(expected_evidence_types) = 'array'), 
    CONSTRAINT ck_capabilities_capabilities_input_schema_json CHECK (jsonb_typeof(input_schema) = 'object'), 
    CONSTRAINT ck_capabilities_capabilities_output_schema_json CHECK (jsonb_typeof(output_schema) = 'object'), 
    CONSTRAINT ck_capabilities_capabilities_required_permissions_json CHECK (jsonb_typeof(required_permissions) = 'array'), 
    CONSTRAINT ck_capabilities_capabilities_required_secret_refs_json CHECK (jsonb_typeof(required_secret_refs) = 'array'), 
    CONSTRAINT ck_capabilities_capabilities_resource_locks_json CHECK (jsonb_typeof(resource_locks) = 'array'), 
    CONSTRAINT ck_capabilities_capabilities_supported_os_json CHECK (jsonb_typeof(supported_os) = 'array'), 
    CONSTRAINT ck_capabilities_capabilities_operation_kind_enum CHECK (operation_kind IN ('PASSIVE_READ', 'ACTIVE_CHECK', 'STATE_CHANGE')), 
    CONSTRAINT ck_capabilities_capabilities_ttl_enforcement_enum CHECK (ttl_enforcement IN ('DEVICE', 'SITE_DURABLE_WATCHDOG', 'CONTROLLER_ONLY', 'NONE')), 
    CONSTRAINT ck_capabilities_capabilities_capability_id_nonempty CHECK (length(capability_id) > 0), 
    CONSTRAINT ck_capabilities_capabilities_version_nonempty CHECK (length(version) > 0), 
    CONSTRAINT ck_capabilities_capabilities_max_concurrency_minimum CHECK (max_concurrency >= 1), 
    CONSTRAINT "ck_capabilities_capabilities_timeout_seconds_exclusiveMinimum" CHECK (timeout_seconds > 0)
);

CREATE TABLE environments (
    environment_id TEXT NOT NULL, 
    version TEXT NOT NULL, 
    deployment_stage TEXT NOT NULL, 
    asset_domain TEXT NOT NULL, 
    connectivity TEXT NOT NULL, 
    operating_model TEXT NOT NULL, 
    autonomy_mode TEXT NOT NULL, 
    load_mode TEXT NOT NULL, 
    model_policy TEXT NOT NULL, 
    data_egress_policy TEXT NOT NULL, 
    max_auto_risk TEXT NOT NULL, 
    active_validation TEXT NOT NULL, 
    scope_ids JSONB NOT NULL, 
    capability_allowlist JSONB NOT NULL, 
    required_sensor_ids JSONB NOT NULL, 
    policy_version TEXT NOT NULL, 
    owner_id TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_environments PRIMARY KEY (environment_id), 
    CONSTRAINT ck_environments_environments_active_validation_enum CHECK (active_validation IN ('DISABLED', 'ISOLATED_ONLY', 'SCOPED_PREAPPROVED')), 
    CONSTRAINT ck_environments_environments_asset_domain_enum CHECK (asset_domain IN ('IT', 'OT', 'MIXED')), 
    CONSTRAINT ck_environments_environments_autonomy_mode_enum CHECK (autonomy_mode IN ('OBSERVE_ONLY', 'ASSISTED', 'CONTROLLED_AUTONOMY', 'VALIDATION')), 
    CONSTRAINT ck_environments_airgap_egress CHECK (connectivity <> 'AIR_GAPPED' OR (model_policy = 'LOCAL_ONLY' AND data_egress_policy = 'DENY')), 
    CONSTRAINT ck_environments_environments_connectivity_enum CHECK (connectivity IN ('CONNECTED', 'RESTRICTED', 'AIR_GAPPED')), 
    CONSTRAINT ck_environments_environments_data_egress_policy_enum CHECK (data_egress_policy IN ('DENY', 'REDACT_THEN_ALLOW', 'ALLOW')), 
    CONSTRAINT ck_environments_ot_production_passive CHECK (deployment_stage <> 'PRODUCTION' OR asset_domain = 'IT' OR (autonomy_mode IN ('OBSERVE_ONLY','ASSISTED') AND active_validation = 'DISABLED')), 
    CONSTRAINT ck_environments_environments_deployment_stage_enum CHECK (deployment_stage IN ('LAB', 'PILOT', 'PRODUCTION')), 
    CONSTRAINT ck_environments_environments_capability_allowlist_json CHECK (jsonb_typeof(capability_allowlist) = 'array'), 
    CONSTRAINT ck_environments_environments_required_sensor_ids_json CHECK (jsonb_typeof(required_sensor_ids) = 'array'), 
    CONSTRAINT ck_environments_environments_scope_ids_json CHECK (jsonb_typeof(scope_ids) = 'array'), 
    CONSTRAINT ck_environments_environments_load_mode_enum CHECK (load_mode IN ('NORMAL', 'HIGH_LOAD', 'EMERGENCY')), 
    CONSTRAINT ck_environments_environment_not_auto_r5 CHECK (max_auto_risk <> 'R5'), 
    CONSTRAINT ck_environments_environments_max_auto_risk_enum CHECK (max_auto_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')), 
    CONSTRAINT ck_environments_environments_model_policy_enum CHECK (model_policy IN ('LOCAL_ONLY', 'HYBRID', 'CLOUD_ALLOWED')), 
    CONSTRAINT ck_environments_environments_operating_model_enum CHECK (operating_model IN ('SINGLE_ORG', 'SOC_MSSP')), 
    CONSTRAINT ck_environments_environments_environment_id_nonempty CHECK (length(environment_id) > 0), 
    CONSTRAINT ck_environments_environments_row_version CHECK (row_version >= 1)
);

CREATE TABLE verification_specs (
    verification_spec_id TEXT NOT NULL, 
    scenario_id TEXT NOT NULL, 
    scenario_version TEXT NOT NULL, 
    objective_type TEXT NOT NULL, 
    checks JSONB NOT NULL, 
    aggregation_rule TEXT NOT NULL, 
    CONSTRAINT pk_verification_specs PRIMARY KEY (verification_spec_id), 
    CONSTRAINT ck_verification_specs_verification_specs_checks_json CHECK (jsonb_typeof(checks) = 'array'), 
    CONSTRAINT ck_verification_specs_verification_specs_objective_type_enum CHECK (objective_type IN ('DETECTION', 'CONTAINMENT', 'REMEDIATION', 'RECOVERY', 'CLEANUP')), 
    CONSTRAINT ck_verification_specs_verification_specs_checks_minitems CHECK (jsonb_array_length(checks) >= 3), 
    CONSTRAINT ck_verification_specs_verification_specs_verification_s_36e0 CHECK (length(verification_spec_id) > 0)
);

CREATE TABLE audit_entries (
    audit_id TEXT NOT NULL, 
    trace_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    actor_type TEXT NOT NULL, 
    actor_id TEXT NOT NULL, 
    object_kind TEXT NOT NULL, 
    object_id TEXT NOT NULL, 
    operation TEXT NOT NULL, 
    reason TEXT NOT NULL, 
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
    previous_entry_hash TEXT, 
    integrity_hash TEXT NOT NULL, 
    sequence BIGINT NOT NULL, 
    CONSTRAINT pk_audit_entries PRIMARY KEY (audit_id), 
    CONSTRAINT ck_audit_entries_audit_entries_actor_type_enum CHECK (actor_type IN ('HUMAN', 'SERVICE', 'MODEL', 'WORKER')), 
    CONSTRAINT ck_audit_entries_audit_entries_integrity_hash_pattern CHECK (integrity_hash ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_audit_entries_audit_entries_previous_entry_hash_pattern CHECK (previous_entry_hash ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_audit_entries_audit_entries_audit_id_nonempty CHECK (length(audit_id) > 0), 
    CONSTRAINT ck_audit_entries_audit_sequence_positive CHECK (sequence >= 1), 
    CONSTRAINT fk_audit_entries_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_audit_entries_environment_id UNIQUE (environment_id, audit_id), 
    CONSTRAINT uq_audit_hash UNIQUE (environment_id, integrity_hash), 
    CONSTRAINT uq_audit_sequence UNIQUE (environment_id, sequence)
);

CREATE INDEX ix_audit_trace_time ON audit_entries (trace_id, timestamp);

CREATE TABLE audit_heads (
    environment_id TEXT NOT NULL, 
    sequence BIGINT DEFAULT '0' NOT NULL, 
    integrity_hash TEXT, 
    CONSTRAINT pk_audit_heads PRIMARY KEY (environment_id), 
    CONSTRAINT ck_audit_heads_head_empty_pair CHECK ((sequence = 0) = (integrity_hash IS NULL)), 
    CONSTRAINT ck_audit_heads_sequence_nonnegative CHECK (sequence >= 0), 
    CONSTRAINT fk_audit_heads_environment_id_environments FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE TABLE capability_health (
    capability_id TEXT NOT NULL, 
    capability_version TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    worker_pool TEXT NOT NULL, 
    status TEXT NOT NULL, 
    checked_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    latency_ms INTEGER, 
    queue_depth INTEGER NOT NULL, 
    running_count INTEGER NOT NULL, 
    detail TEXT, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_capability_health PRIMARY KEY (capability_id, capability_version, environment_id, worker_pool), 
    CONSTRAINT ck_capability_health_capability_health_status_enum CHECK (status IN ('UNVERIFIED', 'HEALTHY', 'DEGRADED', 'OFFLINE')), 
    CONSTRAINT ck_capability_health_capability_health_latency_ms_minimum CHECK (latency_ms >= 0), 
    CONSTRAINT ck_capability_health_capability_health_capability_id_nonempty CHECK (length(capability_id) > 0), 
    CONSTRAINT ck_capability_health_capability_health_capability_versi_e224 CHECK (length(capability_version) > 0), 
    CONSTRAINT ck_capability_health_capability_health_environment_id_nonempty CHECK (length(environment_id) > 0), 
    CONSTRAINT ck_capability_health_capability_health_worker_pool_nonempty CHECK (length(worker_pool) > 0), 
    CONSTRAINT ck_capability_health_capability_health_queue_depth_minimum CHECK (queue_depth >= 0), 
    CONSTRAINT ck_capability_health_capability_health_row_version CHECK (row_version >= 1), 
    CONSTRAINT ck_capability_health_capability_health_running_count_minimum CHECK (running_count >= 0), 
    CONSTRAINT fk_capability_health_capability FOREIGN KEY(capability_id, capability_version) REFERENCES capabilities (capability_id, version), 
    CONSTRAINT fk_capability_health_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE TABLE event_groups (
    group_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    member_event_ids JSONB NOT NULL, 
    grouping_keys JSONB NOT NULL, 
    correlation_reasons JSONB NOT NULL, 
    outlier_event_ids JSONB NOT NULL, 
    correlation_confidence FLOAT NOT NULL, 
    rule_version TEXT NOT NULL, 
    algorithm_version TEXT NOT NULL, 
    CONSTRAINT pk_event_groups PRIMARY KEY (group_id), 
    CONSTRAINT ck_event_groups_event_groups_correlation_reasons_json CHECK (jsonb_typeof(correlation_reasons) = 'array'), 
    CONSTRAINT ck_event_groups_event_groups_grouping_keys_json CHECK (jsonb_typeof(grouping_keys) = 'object'), 
    CONSTRAINT ck_event_groups_event_groups_member_event_ids_json CHECK (jsonb_typeof(member_event_ids) = 'array'), 
    CONSTRAINT ck_event_groups_event_groups_outlier_event_ids_json CHECK (jsonb_typeof(outlier_event_ids) = 'array'), 
    CONSTRAINT ck_event_groups_event_groups_correlation_confidence_maximum CHECK (correlation_confidence <= 1), 
    CONSTRAINT ck_event_groups_event_groups_correlation_confidence_minimum CHECK (correlation_confidence >= 0), 
    CONSTRAINT ck_event_groups_event_groups_correlation_reasons_minitems CHECK (jsonb_array_length(correlation_reasons) >= 1), 
    CONSTRAINT ck_event_groups_event_groups_member_event_ids_minitems CHECK (jsonb_array_length(member_event_ids) >= 1), 
    CONSTRAINT ck_event_groups_group_interval CHECK (last_seen_at >= first_seen_at), 
    CONSTRAINT ck_event_groups_event_groups_group_id_nonempty CHECK (length(group_id) > 0), 
    CONSTRAINT fk_event_groups_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_event_groups_environment_id UNIQUE (environment_id, group_id)
);

CREATE TABLE incidents (
    incident_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    title TEXT NOT NULL, 
    status TEXT NOT NULL, 
    priority TEXT NOT NULL, 
    affected_asset_ids JSONB NOT NULL, 
    related_event_ids JSONB NOT NULL, 
    event_group_ids JSONB NOT NULL, 
    evidence_ids JSONB NOT NULL, 
    state_version INTEGER NOT NULL, 
    first_observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    triaged_at TIMESTAMP WITH TIME ZONE, 
    investigation_started_at TIMESTAMP WITH TIME ZONE, 
    contained_at TIMESTAMP WITH TIME ZONE, 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    closed_at TIMESTAMP WITH TIME ZONE, 
    open_action_ids JSONB NOT NULL, 
    residual_risks JSONB NOT NULL, 
    closure_type TEXT, 
    closure_evidence_ids JSONB NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_incidents PRIMARY KEY (incident_id), 
    CONSTRAINT ck_incidents_incident_closure CHECK ((status = 'CLOSED' AND closure_type IS NOT NULL AND jsonb_array_length(closure_evidence_ids) > 0 AND closed_at IS NOT NULL) OR (status <> 'CLOSED' AND closure_type IS NULL)), 
    CONSTRAINT ck_incidents_incidents_closure_type_enum CHECK (closure_type IN ('CLOSED_REMEDIATED', 'CLOSED_FALSE_POSITIVE', 'CLOSED_DUPLICATE', 'CLOSED_ACCEPTED_RISK')), 
    CONSTRAINT ck_incidents_incidents_affected_asset_ids_json CHECK (jsonb_typeof(affected_asset_ids) = 'array'), 
    CONSTRAINT ck_incidents_incidents_closure_evidence_ids_json CHECK (jsonb_typeof(closure_evidence_ids) = 'array'), 
    CONSTRAINT ck_incidents_incidents_event_group_ids_json CHECK (jsonb_typeof(event_group_ids) = 'array'), 
    CONSTRAINT ck_incidents_incidents_evidence_ids_json CHECK (jsonb_typeof(evidence_ids) = 'array'), 
    CONSTRAINT ck_incidents_incidents_open_action_ids_json CHECK (jsonb_typeof(open_action_ids) = 'array'), 
    CONSTRAINT ck_incidents_incidents_related_event_ids_json CHECK (jsonb_typeof(related_event_ids) = 'array'), 
    CONSTRAINT ck_incidents_incidents_residual_risks_json CHECK (jsonb_typeof(residual_risks) = 'array'), 
    CONSTRAINT ck_incidents_incidents_priority_enum CHECK (priority IN ('P0', 'P1', 'P2', 'P3', 'P4')), 
    CONSTRAINT ck_incidents_incidents_status_enum CHECK (status IN ('NEW', 'TRIAGED', 'INVESTIGATING', 'PLANNED', 'WAITING_APPROVAL', 'EXECUTING', 'VERIFYING', 'CONTAINED', 'RESOLVED', 'CLOSED', 'HUMAN_REVIEW', 'REOPENED')), 
    CONSTRAINT ck_incidents_incident_interval CHECK (created_at >= first_observed_at AND updated_at >= created_at), 
    CONSTRAINT ck_incidents_incidents_incident_id_nonempty CHECK (length(incident_id) > 0), 
    CONSTRAINT ck_incidents_incidents_row_version CHECK (row_version >= 1), 
    CONSTRAINT ck_incidents_incidents_state_version_minimum CHECK (state_version >= 1), 
    CONSTRAINT fk_incidents_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_incidents_environment_id UNIQUE (environment_id, incident_id)
);

CREATE INDEX ix_incident_env_status ON incidents (environment_id, status, priority);

CREATE TABLE outbox (
    message_id TEXT NOT NULL, 
    aggregate_type TEXT NOT NULL, 
    aggregate_id TEXT NOT NULL, 
    event_type TEXT NOT NULL, 
    payload_ref TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    published_at TIMESTAMP WITH TIME ZONE, 
    attempt_count INTEGER NOT NULL, 
    environment_id TEXT NOT NULL, 
    lease_owner TEXT, 
    lease_until TIMESTAMP WITH TIME ZONE, 
    generation INTEGER DEFAULT '0' NOT NULL, 
    available_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    last_error_code TEXT, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_outbox PRIMARY KEY (message_id), 
    CONSTRAINT ck_outbox_outbox_lease_pair CHECK ((lease_owner IS NULL) = (lease_until IS NULL)), 
    CONSTRAINT ck_outbox_outbox_attempt_count_minimum CHECK (attempt_count >= 0), 
    CONSTRAINT ck_outbox_outbox_generation CHECK (generation >= 0), 
    CONSTRAINT ck_outbox_outbox_message_id_nonempty CHECK (length(message_id) > 0), 
    CONSTRAINT ck_outbox_outbox_row_version CHECK (row_version >= 1), 
    CONSTRAINT fk_outbox_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_outbox_aggregate_event UNIQUE (environment_id, aggregate_type, aggregate_id, event_type)
);

CREATE INDEX ix_outbox_pending ON outbox (available_at, created_at) WHERE published_at IS NULL;

CREATE TABLE policy_snapshots (
    policy_id TEXT NOT NULL, 
    version TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    high_impact_requires_human BOOLEAN NOT NULL, 
    r5_auto_allowed BOOLEAN NOT NULL, 
    load_can_expand_permissions BOOLEAN NOT NULL, 
    allowed_capability_ids JSONB NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    max_replans INTEGER NOT NULL, 
    max_model_calls INTEGER NOT NULL, 
    max_active_calls INTEGER NOT NULL, 
    max_elapsed_seconds INTEGER NOT NULL, 
    CONSTRAINT pk_policy_snapshots PRIMARY KEY (policy_id, version, environment_id), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_allowed_capability_e7e0 CHECK (jsonb_typeof(allowed_capability_ids) = 'array'), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_high_impact_requir_0005 CHECK (high_impact_requires_human IS TRUE), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_environment_id_nonempty CHECK (length(environment_id) > 0), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_policy_id_nonempty CHECK (length(policy_id) > 0), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_version_nonempty CHECK (length(version) > 0), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_load_can_expand_pe_6424 CHECK (load_can_expand_permissions IS FALSE), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_max_active_calls_minimum CHECK (max_active_calls >= 1), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_max_elapsed_second_3c6d CHECK (max_elapsed_seconds >= 1), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_max_model_calls_minimum CHECK (max_model_calls >= 1), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_max_replans_minimum CHECK (max_replans >= 0), 
    CONSTRAINT ck_policy_snapshots_policy_snapshots_r5_auto_allowed_const CHECK (r5_auto_allowed IS FALSE), 
    CONSTRAINT fk_policy_snapshots_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE TABLE resources (
    resource_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    resource_type TEXT NOT NULL, 
    binding_version INTEGER NOT NULL, 
    locator JSONB NOT NULL, 
    display_name TEXT, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_resources PRIMARY KEY (resource_id, environment_id), 
    CONSTRAINT ck_resources_resource_locator_required CHECK ((resource_type <> 'NETWORK_ENDPOINT' OR (locator ?& ARRAY['address','port','protocol'] AND (locator->>'port')::integer BETWEEN 1 AND 65535 AND locator->>'protocol' IN ('TCP','UDP'))) AND (resource_type <> 'IDENTITY' OR locator ?| ARRAY['object_id','account_name']) AND (resource_type <> 'KUBERNETES' OR locator ?& ARRAY['cluster_uid','kind','name']) AND (resource_type <> 'CLOUD' OR locator ?& ARRAY['provider','resource_id'])), 
    CONSTRAINT ck_resources_resources_locator_json CHECK (jsonb_typeof(locator) = 'object'), 
    CONSTRAINT ck_resources_resources_resource_type_enum CHECK (resource_type IN ('NETWORK_ENDPOINT', 'HOST', 'IDENTITY', 'KUBERNETES', 'CLOUD', 'SAAS', 'SECURITY_CONTROL')), 
    CONSTRAINT ck_resources_resources_binding_version_minimum CHECK (binding_version >= 1), 
    CONSTRAINT ck_resources_resources_environment_id_nonempty CHECK (length(environment_id) > 0), 
    CONSTRAINT ck_resources_resources_resource_id_nonempty CHECK (length(resource_id) > 0), 
    CONSTRAINT ck_resources_resources_row_version CHECK (row_version >= 1), 
    CONSTRAINT fk_resources_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE INDEX ix_resources_type ON resources (environment_id, resource_type);

CREATE TABLE scopes (
    scope_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    version TEXT NOT NULL, 
    source_resource_ids JSONB NOT NULL, 
    target_resource_ids JSONB NOT NULL, 
    capability_source_ids JSONB NOT NULL, 
    allowed_capabilities JSONB NOT NULL, 
    network_constraints JSONB NOT NULL, 
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    max_requests_per_second FLOAT NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_scopes PRIMARY KEY (scope_id, environment_id), 
    CONSTRAINT ck_scopes_scopes_allowed_capabilities_json CHECK (jsonb_typeof(allowed_capabilities) = 'array'), 
    CONSTRAINT ck_scopes_scopes_capability_source_ids_json CHECK (jsonb_typeof(capability_source_ids) = 'object'), 
    CONSTRAINT ck_scopes_scopes_network_constraints_json CHECK (jsonb_typeof(network_constraints) = 'array'), 
    CONSTRAINT ck_scopes_scopes_source_resource_ids_json CHECK (jsonb_typeof(source_resource_ids) = 'array'), 
    CONSTRAINT ck_scopes_scopes_target_resource_ids_json CHECK (jsonb_typeof(target_resource_ids) = 'array'), 
    CONSTRAINT ck_scopes_scopes_allowed_capabilities_minitems CHECK (jsonb_array_length(allowed_capabilities) >= 1), 
    CONSTRAINT ck_scopes_scopes_source_resource_ids_minitems CHECK (jsonb_array_length(source_resource_ids) >= 1), 
    CONSTRAINT ck_scopes_scopes_target_resource_ids_minitems CHECK (jsonb_array_length(target_resource_ids) >= 1), 
    CONSTRAINT ck_scopes_scopes_environment_id_nonempty CHECK (length(environment_id) > 0), 
    CONSTRAINT ck_scopes_scopes_scope_id_nonempty CHECK (length(scope_id) > 0), 
    CONSTRAINT "ck_scopes_scopes_max_requests_per_second_exclusiveMinimum" CHECK (max_requests_per_second > 0), 
    CONSTRAINT ck_scopes_scopes_row_version CHECK (row_version >= 1), 
    CONSTRAINT ck_scopes_scope_interval CHECK (valid_until > valid_from), 
    CONSTRAINT fk_scopes_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE INDEX ix_scopes_expiry ON scopes (environment_id, valid_until);

CREATE TABLE sensor_health (
    sensor_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    status TEXT NOT NULL, 
    last_heartbeat_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    last_event_at TIMESTAMP WITH TIME ZONE, 
    lag_seconds FLOAT NOT NULL, 
    lost_event_count INTEGER NOT NULL, 
    coverage_scope_ids JSONB NOT NULL, 
    coverage_validated BOOLEAN NOT NULL, 
    config_version TEXT NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_sensor_health PRIMARY KEY (sensor_id, environment_id), 
    CONSTRAINT ck_sensor_health_sensor_health_coverage_scope_ids_json CHECK (jsonb_typeof(coverage_scope_ids) = 'array'), 
    CONSTRAINT ck_sensor_health_sensor_health_status_enum CHECK (status IN ('HEALTHY', 'DEGRADED', 'OFFLINE', 'UNKNOWN')), 
    CONSTRAINT ck_sensor_health_sensor_health_lag_seconds_minimum CHECK (lag_seconds >= 0), 
    CONSTRAINT ck_sensor_health_sensor_health_environment_id_nonempty CHECK (length(environment_id) > 0), 
    CONSTRAINT ck_sensor_health_sensor_health_sensor_id_nonempty CHECK (length(sensor_id) > 0), 
    CONSTRAINT ck_sensor_health_sensor_health_lost_event_count_minimum CHECK (lost_event_count >= 0), 
    CONSTRAINT ck_sensor_health_sensor_health_row_version CHECK (row_version >= 1), 
    CONSTRAINT fk_sensor_health_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE TABLE state_entities (
    entity_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    entity_type TEXT NOT NULL, 
    state_version INTEGER NOT NULL, 
    attributes JSONB NOT NULL, 
    claim_kind TEXT NOT NULL, 
    evidence_ids JSONB NOT NULL, 
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_state_entities PRIMARY KEY (entity_id, environment_id), 
    CONSTRAINT ck_state_entities_state_entities_claim_kind_enum CHECK (claim_kind IN ('OBSERVATION', 'INFERENCE', 'HUMAN_REVIEW')), 
    CONSTRAINT ck_state_entities_state_entities_attributes_json CHECK (jsonb_typeof(attributes) = 'object'), 
    CONSTRAINT ck_state_entities_state_entities_evidence_ids_json CHECK (jsonb_typeof(evidence_ids) = 'array'), 
    CONSTRAINT ck_state_entities_state_entities_entity_id_nonempty CHECK (length(entity_id) > 0), 
    CONSTRAINT ck_state_entities_state_entities_environment_id_nonempty CHECK (length(environment_id) > 0), 
    CONSTRAINT ck_state_entities_state_entities_row_version CHECK (row_version >= 1), 
    CONSTRAINT ck_state_entities_state_entities_state_version_minimum CHECK (state_version >= 1), 
    CONSTRAINT fk_state_entities_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE TABLE context_bundles (
    context_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    state_version INTEGER NOT NULL, 
    evidence_ids JSONB NOT NULL, 
    excluded_evidence_reasons JSONB NOT NULL, 
    unresolved_conflicts JSONB NOT NULL, 
    sensor_health_ids JSONB NOT NULL, 
    capability_ids JSONB NOT NULL, 
    policy_version TEXT NOT NULL, 
    token_budget INTEGER NOT NULL, 
    data_classification TEXT NOT NULL, 
    egress_allowed BOOLEAN NOT NULL, 
    summary_version TEXT NOT NULL, 
    prompt_version TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_context_bundles PRIMARY KEY (context_id), 
    CONSTRAINT ck_context_bundles_context_bundles_data_classification_enum CHECK (data_classification IN ('PUBLIC', 'INTERNAL', 'SENSITIVE', 'RESTRICTED')), 
    CONSTRAINT ck_context_bundles_context_bundles_capability_ids_json CHECK (jsonb_typeof(capability_ids) = 'array'), 
    CONSTRAINT ck_context_bundles_context_bundles_evidence_ids_json CHECK (jsonb_typeof(evidence_ids) = 'array'), 
    CONSTRAINT ck_context_bundles_context_bundles_excluded_evidence_re_e86d CHECK (jsonb_typeof(excluded_evidence_reasons) = 'object'), 
    CONSTRAINT ck_context_bundles_context_bundles_sensor_health_ids_json CHECK (jsonb_typeof(sensor_health_ids) = 'array'), 
    CONSTRAINT ck_context_bundles_context_bundles_unresolved_conflicts_json CHECK (jsonb_typeof(unresolved_conflicts) = 'array'), 
    CONSTRAINT ck_context_bundles_context_bundles_context_id_nonempty CHECK (length(context_id) > 0), 
    CONSTRAINT ck_context_bundles_context_bundles_state_version_minimum CHECK (state_version >= 1), 
    CONSTRAINT ck_context_bundles_context_bundles_token_budget_exclusi_e183 CHECK (token_budget > 0), 
    CONSTRAINT fk_context_bundles_incident FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_context_bundles_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_context_bundles_environment_id UNIQUE (environment_id, context_id), 
    CONSTRAINT uq_context_incident UNIQUE (environment_id, incident_id, context_id)
);

CREATE TABLE correlation_decisions (
    decision_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    input_event_ids JSONB NOT NULL, 
    output_group_id TEXT NOT NULL, 
    rules_fired JSONB NOT NULL, 
    merge_reason TEXT NOT NULL, 
    excluded_event_ids JSONB NOT NULL, 
    decision_version TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_correlation_decisions PRIMARY KEY (decision_id), 
    CONSTRAINT ck_correlation_decisions_correlation_decisions_excluded_f776 CHECK (jsonb_typeof(excluded_event_ids) = 'array'), 
    CONSTRAINT ck_correlation_decisions_correlation_decisions_input_ev_994f CHECK (jsonb_typeof(input_event_ids) = 'array'), 
    CONSTRAINT ck_correlation_decisions_correlation_decisions_rules_fired_json CHECK (jsonb_typeof(rules_fired) = 'array'), 
    CONSTRAINT ck_correlation_decisions_correlation_decisions_input_ev_e359 CHECK (jsonb_array_length(input_event_ids) >= 1), 
    CONSTRAINT ck_correlation_decisions_correlation_decisions_rules_fi_a46b CHECK (jsonb_array_length(rules_fired) >= 1), 
    CONSTRAINT ck_correlation_decisions_correlation_decisions_decision_d0f2 CHECK (length(decision_id) > 0), 
    CONSTRAINT fk_correlation_group FOREIGN KEY(environment_id, output_group_id) REFERENCES event_groups (environment_id, group_id), 
    CONSTRAINT fk_correlation_decisions_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_correlation_decisions_environment_id UNIQUE (environment_id, decision_id)
);

CREATE TABLE evidence (
    evidence_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    source_event_ids JSONB NOT NULL, 
    provenance_group TEXT NOT NULL, 
    claim_kind TEXT NOT NULL, 
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    content_ref TEXT NOT NULL, 
    integrity_hash TEXT NOT NULL, 
    hash_algorithm TEXT NOT NULL, 
    collector_id TEXT NOT NULL, 
    collection_method TEXT NOT NULL, 
    trust_status TEXT NOT NULL, 
    supports JSONB NOT NULL, 
    contradicts JSONB NOT NULL, 
    data_origin TEXT NOT NULL, 
    CONSTRAINT pk_evidence PRIMARY KEY (evidence_id), 
    CONSTRAINT ck_evidence_evidence_claim_kind_enum CHECK (claim_kind IN ('OBSERVATION', 'SOURCE_ASSERTION', 'INFERENCE', 'HUMAN_REVIEW')), 
    CONSTRAINT ck_evidence_evidence_data_origin_enum CHECK (data_origin IN ('SYNTHETIC', 'OBSERVED')), 
    CONSTRAINT ck_evidence_evidence_integrity_hash_pattern CHECK (integrity_hash ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_evidence_evidence_contradicts_json CHECK (jsonb_typeof(contradicts) = 'array'), 
    CONSTRAINT ck_evidence_evidence_source_event_ids_json CHECK (jsonb_typeof(source_event_ids) = 'array'), 
    CONSTRAINT ck_evidence_evidence_supports_json CHECK (jsonb_typeof(supports) = 'array'), 
    CONSTRAINT ck_evidence_evidence_trust_status_enum CHECK (trust_status IN ('VERIFIED_ORIGIN', 'UNVERIFIED_ORIGIN', 'CONFLICTED')), 
    CONSTRAINT ck_evidence_evidence_evidence_id_nonempty CHECK (length(evidence_id) > 0), 
    CONSTRAINT fk_evidence_incident FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_evidence_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_evidence_environment_id UNIQUE (environment_id, evidence_id)
);

CREATE INDEX ix_evidence_incident_time ON evidence (incident_id, observed_at);

CREATE TABLE scope_resources (
    environment_id TEXT NOT NULL, 
    scope_id TEXT NOT NULL, 
    resource_id TEXT NOT NULL, 
    role TEXT NOT NULL, 
    CONSTRAINT pk_scope_resources PRIMARY KEY (environment_id, scope_id, resource_id, role), 
    CONSTRAINT ck_scope_resources_scope_resource_role CHECK (role IN ('SOURCE','TARGET')), 
    CONSTRAINT fk_scope_resources_environment_id_resources FOREIGN KEY(environment_id, resource_id) REFERENCES resources (environment_id, resource_id), 
    CONSTRAINT fk_scope_resources_environment_id_scopes FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id)
);

CREATE TABLE state_relations (
    relation_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    source_entity_id TEXT NOT NULL, 
    destination_entity_id TEXT NOT NULL, 
    relation_type TEXT NOT NULL, 
    state_version INTEGER NOT NULL, 
    evidence_ids JSONB NOT NULL, 
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_state_relations PRIMARY KEY (relation_id, environment_id), 
    CONSTRAINT ck_state_relations_state_relations_evidence_ids_json CHECK (jsonb_typeof(evidence_ids) = 'array'), 
    CONSTRAINT ck_state_relations_state_relations_environment_id_nonempty CHECK (length(environment_id) > 0), 
    CONSTRAINT ck_state_relations_state_relations_relation_id_nonempty CHECK (length(relation_id) > 0), 
    CONSTRAINT ck_state_relations_state_relations_row_version CHECK (row_version >= 1), 
    CONSTRAINT ck_state_relations_state_relations_state_version_minimum CHECK (state_version >= 1), 
    CONSTRAINT fk_relation_destination_entity_id FOREIGN KEY(environment_id, destination_entity_id) REFERENCES state_entities (environment_id, entity_id), 
    CONSTRAINT fk_relation_source_entity_id FOREIGN KEY(environment_id, source_entity_id) REFERENCES state_entities (environment_id, entity_id), 
    CONSTRAINT fk_state_relations_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE TABLE tasks (
    task_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    dependencies JSONB NOT NULL, 
    capability_id TEXT NOT NULL, 
    capability_version TEXT NOT NULL, 
    target_resource_ids JSONB NOT NULL, 
    scope_id TEXT NOT NULL, 
    parameters JSONB NOT NULL, 
    status TEXT NOT NULL, 
    priority TEXT NOT NULL, 
    timeout_seconds INTEGER NOT NULL, 
    max_attempts INTEGER NOT NULL, 
    attempt_count INTEGER NOT NULL, 
    expected_output TEXT NOT NULL, 
    evidence_ids JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    queued_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    claimed_at TIMESTAMP WITH TIME ZONE, 
    started_at TIMESTAMP WITH TIME ZONE, 
    finished_at TIMESTAMP WITH TIME ZONE, 
    active_lease_id TEXT, 
    worker_id TEXT, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_tasks PRIMARY KEY (task_id), 
    CONSTRAINT ck_tasks_tasks_dependencies_json CHECK (jsonb_typeof(dependencies) = 'array'), 
    CONSTRAINT ck_tasks_tasks_evidence_ids_json CHECK (jsonb_typeof(evidence_ids) = 'array'), 
    CONSTRAINT ck_tasks_tasks_parameters_json CHECK (jsonb_typeof(parameters) = 'object'), 
    CONSTRAINT ck_tasks_tasks_target_resource_ids_json CHECK (jsonb_typeof(target_resource_ids) = 'array'), 
    CONSTRAINT ck_tasks_tasks_priority_enum CHECK (priority IN ('P0', 'P1', 'P2', 'P3', 'P4')), 
    CONSTRAINT ck_tasks_tasks_status_enum CHECK (status IN ('QUEUED', 'BLOCKED', 'WAITING_APPROVAL', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'TIMED_OUT')), 
    CONSTRAINT ck_tasks_tasks_attempt_count_maximum CHECK (attempt_count <= 10), 
    CONSTRAINT ck_tasks_task_attempt_budget CHECK (attempt_count <= max_attempts), 
    CONSTRAINT ck_tasks_tasks_attempt_count_minimum CHECK (attempt_count >= 0), 
    CONSTRAINT ck_tasks_tasks_target_resource_ids_minitems CHECK (jsonb_array_length(target_resource_ids) >= 1), 
    CONSTRAINT ck_tasks_tasks_task_id_nonempty CHECK (length(task_id) > 0), 
    CONSTRAINT ck_tasks_tasks_max_attempts_maximum CHECK (max_attempts <= 10), 
    CONSTRAINT ck_tasks_tasks_max_attempts_minimum CHECK (max_attempts >= 1), 
    CONSTRAINT ck_tasks_tasks_row_version CHECK (row_version >= 1), 
    CONSTRAINT "ck_tasks_tasks_timeout_seconds_exclusiveMinimum" CHECK (timeout_seconds > 0), 
    CONSTRAINT fk_tasks_capability FOREIGN KEY(capability_id, capability_version) REFERENCES capabilities (capability_id, version), 
    CONSTRAINT fk_tasks_incident FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_tasks_scope FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), 
    CONSTRAINT fk_tasks_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_task_incident UNIQUE (environment_id, incident_id, task_id), 
    CONSTRAINT uq_tasks_environment_id UNIQUE (environment_id, task_id)
);

CREATE INDEX ix_tasks_dispatch ON tasks (status, priority, queued_at);

CREATE TABLE validation_scenarios (
    scenario_id TEXT NOT NULL, 
    version TEXT NOT NULL, 
    implementation_status TEXT NOT NULL, 
    objective TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    scope_id TEXT NOT NULL, 
    preconditions JSONB NOT NULL, 
    trigger_steps JSONB NOT NULL, 
    expected_events JSONB NOT NULL, 
    verification_spec_id TEXT NOT NULL, 
    cleanup_steps JSONB NOT NULL, 
    stop_conditions JSONB NOT NULL, 
    config_is_measured_performance BOOLEAN NOT NULL, 
    CONSTRAINT pk_validation_scenarios PRIMARY KEY (scenario_id, version), 
    CONSTRAINT ck_validation_scenarios_validation_scenarios_implementa_9ae7 CHECK (implementation_status IN ('DESIGN_ONLY', 'LAB_VERIFIED')), 
    CONSTRAINT ck_validation_scenarios_validation_scenarios_cleanup_steps_json CHECK (jsonb_typeof(cleanup_steps) = 'array'), 
    CONSTRAINT ck_validation_scenarios_validation_scenarios_expected_e_7908 CHECK (jsonb_typeof(expected_events) = 'array'), 
    CONSTRAINT ck_validation_scenarios_validation_scenarios_preconditions_json CHECK (jsonb_typeof(preconditions) = 'array'), 
    CONSTRAINT ck_validation_scenarios_validation_scenarios_stop_condi_0b76 CHECK (jsonb_typeof(stop_conditions) = 'array'), 
    CONSTRAINT ck_validation_scenarios_validation_scenarios_trigger_steps_json CHECK (jsonb_typeof(trigger_steps) = 'array'), 
    CONSTRAINT ck_validation_scenarios_validation_scenarios_config_is__7242 CHECK (config_is_measured_performance IS FALSE), 
    CONSTRAINT ck_validation_scenarios_validation_scenarios_scenario_i_8eb6 CHECK (length(scenario_id) > 0), 
    CONSTRAINT ck_validation_scenarios_validation_scenarios_version_nonempty CHECK (length(version) > 0), 
    CONSTRAINT fk_validation_scenarios_scope FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), 
    CONSTRAINT fk_validation_scenarios_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_scenario_environment_version UNIQUE (environment_id, scenario_id, version)
);

CREATE TABLE action_requests (
    action_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    task_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    capability_id TEXT NOT NULL, 
    capability_version TEXT NOT NULL, 
    source JSONB, 
    target JSONB NOT NULL, 
    parameters JSONB NOT NULL, 
    scope_id TEXT NOT NULL, 
    scope_version TEXT NOT NULL, 
    environment_profile_version TEXT NOT NULL, 
    policy_version TEXT NOT NULL, 
    expected_state_version INTEGER NOT NULL, 
    preconditions JSONB NOT NULL, 
    evidence_ids JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    ttl_seconds INTEGER NOT NULL, 
    idempotency_key TEXT NOT NULL, 
    ownership_tag TEXT NOT NULL, 
    rollback_policy_id TEXT NOT NULL, 
    action_digest TEXT NOT NULL, 
    CONSTRAINT pk_action_requests PRIMARY KEY (action_id), 
    CONSTRAINT ck_action_requests_action_digest_format CHECK (action_digest ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_action_requests_action_requests_evidence_ids_json CHECK (jsonb_typeof(evidence_ids) = 'array'), 
    CONSTRAINT ck_action_requests_action_requests_parameters_json CHECK (jsonb_typeof(parameters) = 'object'), 
    CONSTRAINT ck_action_requests_action_requests_preconditions_json CHECK (jsonb_typeof(preconditions) = 'array'), 
    CONSTRAINT ck_action_requests_action_requests_source_json CHECK (jsonb_typeof(source) = 'object'), 
    CONSTRAINT ck_action_requests_action_requests_target_json CHECK (jsonb_typeof(target) = 'object'), 
    CONSTRAINT ck_action_requests_action_resource_environment CHECK (target->>'environment_id' = environment_id AND (source IS NULL OR source->>'environment_id' = environment_id)), 
    CONSTRAINT ck_action_requests_action_requests_expected_state_versi_35aa CHECK (expected_state_version >= 1), 
    CONSTRAINT ck_action_requests_action_interval CHECK (expires_at > created_at), 
    CONSTRAINT ck_action_requests_action_requests_evidence_ids_minitems CHECK (jsonb_array_length(evidence_ids) >= 1), 
    CONSTRAINT ck_action_requests_action_requests_preconditions_minitems CHECK (jsonb_array_length(preconditions) >= 1), 
    CONSTRAINT ck_action_requests_action_requests_action_id_nonempty CHECK (length(action_id) > 0), 
    CONSTRAINT ck_action_requests_action_requests_ttl_seconds_minimum CHECK (ttl_seconds >= 0), 
    CONSTRAINT fk_action_requests_capability FOREIGN KEY(capability_id, capability_version) REFERENCES capabilities (capability_id, version), 
    CONSTRAINT fk_action_task FOREIGN KEY(environment_id, incident_id, task_id) REFERENCES tasks (environment_id, incident_id, task_id), 
    CONSTRAINT fk_action_requests_incident FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_action_requests_scope FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), 
    CONSTRAINT fk_action_requests_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_action_digest UNIQUE (action_id, action_digest), 
    CONSTRAINT uq_action_requests_environment_id UNIQUE (environment_id, action_id), 
    CONSTRAINT uq_action_idempotency UNIQUE (environment_id, idempotency_key), 
    CONSTRAINT uq_action_incident UNIQUE (environment_id, incident_id, action_id)
);

CREATE TABLE model_runs (
    run_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    task_id TEXT, 
    provider TEXT NOT NULL, 
    model TEXT NOT NULL, 
    model_revision TEXT, 
    prompt_version TEXT NOT NULL, 
    context_id TEXT NOT NULL, 
    input_hash TEXT NOT NULL, 
    output_hash TEXT NOT NULL, 
    route_reason TEXT NOT NULL, 
    fallback_from_run_id TEXT, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    finished_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    input_tokens INTEGER NOT NULL, 
    output_tokens INTEGER NOT NULL, 
    cached_tokens INTEGER NOT NULL, 
    latency_ms INTEGER NOT NULL, 
    cost_usd FLOAT, 
    schema_valid BOOLEAN NOT NULL, 
    safety_status TEXT NOT NULL, 
    CONSTRAINT pk_model_runs PRIMARY KEY (run_id), 
    CONSTRAINT ck_model_runs_model_runs_input_hash_pattern CHECK (input_hash ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_model_runs_model_runs_output_hash_pattern CHECK (output_hash ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_model_runs_model_runs_safety_status_enum CHECK (safety_status IN ('PASS', 'REJECTED', 'DEGRADED')), 
    CONSTRAINT ck_model_runs_model_runs_cached_tokens_minimum CHECK (cached_tokens >= 0), 
    CONSTRAINT ck_model_runs_model_runs_cost_usd_minimum CHECK (cost_usd >= 0), 
    CONSTRAINT ck_model_runs_model_runs_input_tokens_minimum CHECK (input_tokens >= 0), 
    CONSTRAINT ck_model_runs_model_runs_latency_ms_minimum CHECK (latency_ms >= 0), 
    CONSTRAINT ck_model_runs_model_runs_run_id_nonempty CHECK (length(run_id) > 0), 
    CONSTRAINT ck_model_runs_model_runs_output_tokens_minimum CHECK (output_tokens >= 0), 
    CONSTRAINT fk_model_fallback FOREIGN KEY(environment_id, fallback_from_run_id) REFERENCES model_runs (environment_id, run_id), 
    CONSTRAINT fk_model_context FOREIGN KEY(environment_id, incident_id, context_id) REFERENCES context_bundles (environment_id, incident_id, context_id), 
    CONSTRAINT fk_model_task FOREIGN KEY(environment_id, incident_id, task_id) REFERENCES tasks (environment_id, incident_id, task_id), 
    CONSTRAINT fk_model_runs_incident FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_model_runs_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_model_runs_environment_id UNIQUE (environment_id, run_id)
);

CREATE TABLE validation_runs (
    run_id TEXT NOT NULL, 
    scenario_id TEXT NOT NULL, 
    scenario_version TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    scope_id TEXT NOT NULL, 
    registered_by TEXT NOT NULL, 
    trusted_registration BOOLEAN NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expected_event_types JSONB NOT NULL, 
    allowed_side_effects JSONB NOT NULL, 
    cleanup_policy_id TEXT NOT NULL, 
    data_origin TEXT NOT NULL, 
    CONSTRAINT pk_validation_runs PRIMARY KEY (run_id), 
    CONSTRAINT ck_validation_runs_validation_runs_data_origin_enum CHECK (data_origin IN ('SYNTHETIC', 'OBSERVED')), 
    CONSTRAINT ck_validation_runs_validation_runs_allowed_side_effects_json CHECK (jsonb_typeof(allowed_side_effects) = 'array'), 
    CONSTRAINT ck_validation_runs_validation_runs_expected_event_types_json CHECK (jsonb_typeof(expected_event_types) = 'array'), 
    CONSTRAINT ck_validation_runs_validation_runs_run_id_nonempty CHECK (length(run_id) > 0), 
    CONSTRAINT fk_run_scenario FOREIGN KEY(environment_id, scenario_id, scenario_version) REFERENCES validation_scenarios (environment_id, scenario_id, version), 
    CONSTRAINT fk_validation_runs_scope FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), 
    CONSTRAINT fk_validation_runs_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_validation_runs_environment_id UNIQUE (environment_id, run_id)
);

CREATE TABLE worker_leases (
    lease_id TEXT NOT NULL, 
    task_id TEXT NOT NULL, 
    worker_id TEXT NOT NULL, 
    generation INTEGER NOT NULL, 
    acquired_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    renewed_at TIMESTAMP WITH TIME ZONE, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_worker_leases PRIMARY KEY (lease_id), 
    CONSTRAINT ck_worker_leases_lease_interval CHECK (expires_at > acquired_at AND (renewed_at IS NULL OR renewed_at >= acquired_at)), 
    CONSTRAINT ck_worker_leases_worker_leases_generation_minimum CHECK (generation >= 1), 
    CONSTRAINT ck_worker_leases_worker_leases_lease_id_nonempty CHECK (length(lease_id) > 0), 
    CONSTRAINT ck_worker_leases_worker_leases_row_version CHECK (row_version >= 1), 
    CONSTRAINT fk_lease_task FOREIGN KEY(task_id) REFERENCES tasks (task_id), 
    CONSTRAINT uq_task_lease_generation UNIQUE (task_id, generation), 
    CONSTRAINT uq_task_lease_id UNIQUE (task_id, lease_id)
);

CREATE INDEX ix_leases_expiry ON worker_leases (expires_at);

CREATE TABLE action_attempts (
    attempt_id TEXT NOT NULL, 
    action_id TEXT NOT NULL, 
    status TEXT NOT NULL, 
    fencing_generation INTEGER NOT NULL, 
    worker_id TEXT NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    finished_at TIMESTAMP WITH TIME ZONE, 
    device_receipt_id TEXT, 
    reconciliation_state TEXT NOT NULL, 
    evidence_ids JSONB NOT NULL, 
    error_code TEXT, 
    error_class TEXT, 
    device_response_hash TEXT, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_action_attempts PRIMARY KEY (attempt_id), 
    CONSTRAINT ck_action_attempts_action_attempts_device_response_hash_pattern CHECK (device_response_hash ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_action_attempts_action_attempts_evidence_ids_json CHECK (jsonb_typeof(evidence_ids) = 'array'), 
    CONSTRAINT ck_action_attempts_action_attempts_reconciliation_state_enum CHECK (reconciliation_state IN ('NOT_NEEDED', 'PENDING', 'CONFIRMED_APPLIED', 'CONFIRMED_NOT_APPLIED', 'PARTIAL', 'UNKNOWN')), 
    CONSTRAINT ck_action_attempts_action_attempts_status_enum CHECK (status IN ('PROPOSED', 'WAITING_APPROVAL', 'AUTHORIZED', 'DISPATCHED', 'EXECUTING', 'EXECUTED', 'EXECUTION_UNKNOWN', 'RECONCILING', 'COMPENSATING', 'COMPENSATED', 'COMPENSATION_FAILED', 'NEEDS_MANUAL', 'DENIED', 'EXPIRED', 'CANCELLED', 'FAILED')), 
    CONSTRAINT ck_action_attempts_action_attempts_fencing_generation_minimum CHECK (fencing_generation >= 1), 
    CONSTRAINT ck_action_attempts_attempt_interval CHECK (finished_at IS NULL OR finished_at >= started_at), 
    CONSTRAINT ck_action_attempts_action_attempts_attempt_id_nonempty CHECK (length(attempt_id) > 0), 
    CONSTRAINT ck_action_attempts_action_attempts_row_version CHECK (row_version >= 1), 
    CONSTRAINT fk_attempt_action FOREIGN KEY(action_id) REFERENCES action_requests (action_id)
);

CREATE INDEX ix_attempts_action_time ON action_attempts (action_id, started_at);

CREATE TABLE approvals (
    approval_id TEXT NOT NULL, 
    action_id TEXT NOT NULL, 
    action_digest TEXT NOT NULL, 
    actor_id TEXT NOT NULL, 
    actor_role TEXT NOT NULL, 
    decision TEXT NOT NULL, 
    reason TEXT NOT NULL, 
    policy_version TEXT NOT NULL, 
    approved_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_approvals PRIMARY KEY (approval_id), 
    CONSTRAINT ck_approvals_approvals_action_digest_pattern CHECK (action_digest ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_approvals_approvals_actor_role_enum CHECK (actor_role IN ('APPROVER', 'ADMIN')), 
    CONSTRAINT ck_approvals_approvals_decision_enum CHECK (decision IN ('APPROVED', 'REJECTED')), 
    CONSTRAINT ck_approvals_approval_interval CHECK (expires_at > approved_at), 
    CONSTRAINT ck_approvals_approvals_approval_id_nonempty CHECK (length(approval_id) > 0), 
    CONSTRAINT fk_approval_action_digest FOREIGN KEY(action_id, action_digest) REFERENCES action_requests (action_id, action_digest), 
    CONSTRAINT uq_approval_binding UNIQUE (approval_id, action_id, action_digest)
);

CREATE TABLE authorization_contexts (
    authorization_context_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    action_id TEXT NOT NULL, 
    action_digest TEXT NOT NULL, 
    principal_id TEXT NOT NULL, 
    principal_role TEXT NOT NULL, 
    environment_profile_version TEXT NOT NULL, 
    scope_id TEXT NOT NULL, 
    scope_version TEXT NOT NULL, 
    capability_id TEXT NOT NULL, 
    capability_version TEXT NOT NULL, 
    target_resource_id TEXT NOT NULL, 
    source_resource_id TEXT, 
    asset_criticality TEXT NOT NULL, 
    business_impact TEXT NOT NULL, 
    evidence_quality TEXT NOT NULL, 
    sensor_health_status TEXT NOT NULL, 
    autonomy_mode TEXT NOT NULL, 
    load_mode TEXT NOT NULL, 
    requested_risk TEXT NOT NULL, 
    policy_version TEXT NOT NULL, 
    budget_id TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_authorization_contexts PRIMARY KEY (authorization_context_id), 
    CONSTRAINT ck_authorization_contexts_authorization_contexts_action_a7fb CHECK (action_digest ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_authorization_contexts_authorization_contexts_asset__129b CHECK (asset_criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')), 
    CONSTRAINT ck_authorization_contexts_authorization_contexts_autono_1f8d CHECK (autonomy_mode IN ('OBSERVE_ONLY', 'ASSISTED', 'CONTROLLED_AUTONOMY', 'VALIDATION')), 
    CONSTRAINT ck_authorization_contexts_authorization_contexts_busine_3973 CHECK (business_impact IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')), 
    CONSTRAINT ck_authorization_contexts_authorization_contexts_eviden_9c6a CHECK (evidence_quality IN ('LOW', 'MEDIUM', 'HIGH')), 
    CONSTRAINT ck_authorization_contexts_authorization_contexts_load_mode_enum CHECK (load_mode IN ('NORMAL', 'HIGH_LOAD', 'EMERGENCY')), 
    CONSTRAINT ck_authorization_contexts_authorization_contexts_reques_67dd CHECK (requested_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')), 
    CONSTRAINT ck_authorization_contexts_authorization_contexts_sensor_3158 CHECK (sensor_health_status IN ('HEALTHY', 'DEGRADED', 'UNKNOWN')), 
    CONSTRAINT ck_authorization_contexts_authorization_contexts_author_6e8d CHECK (length(authorization_context_id) > 0), 
    CONSTRAINT fk_authctx_action_digest FOREIGN KEY(action_id, action_digest) REFERENCES action_requests (action_id, action_digest), 
    CONSTRAINT fk_authorization_contexts_capability FOREIGN KEY(capability_id, capability_version) REFERENCES capabilities (capability_id, version), 
    CONSTRAINT fk_authctx_action_env FOREIGN KEY(environment_id, action_id) REFERENCES action_requests (environment_id, action_id), 
    CONSTRAINT fk_authorization_contexts_scope FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), 
    CONSTRAINT fk_authctx_source_resource_id FOREIGN KEY(environment_id, source_resource_id) REFERENCES resources (environment_id, resource_id), 
    CONSTRAINT fk_authctx_target_resource_id FOREIGN KEY(environment_id, target_resource_id) REFERENCES resources (environment_id, resource_id), 
    CONSTRAINT fk_authorization_contexts_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_authctx_binding UNIQUE (authorization_context_id, action_id, action_digest), 
    CONSTRAINT uq_authorization_contexts_environment_id UNIQUE (environment_id, authorization_context_id)
);

CREATE TABLE normalized_events (
    event_id TEXT NOT NULL, 
    specversion TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    source_type TEXT NOT NULL, 
    collector_id TEXT NOT NULL, 
    origin_event_id TEXT NOT NULL, 
    provenance_group TEXT NOT NULL, 
    source_timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
    ingested_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    clock_status TEXT NOT NULL, 
    event_type TEXT NOT NULL, 
    activity_category TEXT NOT NULL, 
    activity_name TEXT NOT NULL, 
    outcome TEXT NOT NULL, 
    actor_resource_id TEXT, 
    source_resource_ids JSONB NOT NULL, 
    target_resource_ids JSONB NOT NULL, 
    observables JSONB NOT NULL, 
    severity_signal INTEGER NOT NULL, 
    raw_ref TEXT NOT NULL, 
    parser_version TEXT NOT NULL, 
    mapping_version TEXT NOT NULL, 
    fingerprint TEXT NOT NULL, 
    validation_run_id TEXT, 
    data_origin TEXT NOT NULL, 
    content_hash TEXT NOT NULL, 
    CONSTRAINT pk_normalized_events PRIMARY KEY (event_id), 
    CONSTRAINT ck_normalized_events_normalized_events_clock_status_enum CHECK (clock_status IN ('TRUSTED', 'SKEWED', 'UNKNOWN')), 
    CONSTRAINT ck_normalized_events_event_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_normalized_events_normalized_events_data_origin_enum CHECK (data_origin IN ('SYNTHETIC', 'OBSERVED')), 
    CONSTRAINT ck_normalized_events_normalized_events_observables_json CHECK (jsonb_typeof(observables) = 'array'), 
    CONSTRAINT ck_normalized_events_normalized_events_source_resource_ids_json CHECK (jsonb_typeof(source_resource_ids) = 'array'), 
    CONSTRAINT ck_normalized_events_normalized_events_target_resource_ids_json CHECK (jsonb_typeof(target_resource_ids) = 'array'), 
    CONSTRAINT ck_normalized_events_normalized_events_outcome_enum CHECK (outcome IN ('SUCCESS', 'FAILURE', 'UNKNOWN', 'PARTIAL', 'DENIED')), 
    CONSTRAINT ck_normalized_events_normalized_events_event_id_nonempty CHECK (length(event_id) > 0), 
    CONSTRAINT ck_normalized_events_normalized_events_severity_signal_maximum CHECK (severity_signal <= 10), 
    CONSTRAINT ck_normalized_events_normalized_events_severity_signal_minimum CHECK (severity_signal >= 0), 
    CONSTRAINT fk_event_actor FOREIGN KEY(environment_id, actor_resource_id) REFERENCES resources (environment_id, resource_id), 
    CONSTRAINT fk_event_run FOREIGN KEY(environment_id, validation_run_id) REFERENCES validation_runs (environment_id, run_id), 
    CONSTRAINT fk_normalized_events_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_event_origin UNIQUE (environment_id, collector_id, source_type, origin_event_id, event_type), 
    CONSTRAINT uq_normalized_events_environment_id UNIQUE (environment_id, event_id)
);

CREATE INDEX ix_events_env_time ON normalized_events (environment_id, source_timestamp);

CREATE INDEX ix_events_fingerprint ON normalized_events (environment_id, fingerprint);

CREATE INDEX ix_events_provenance ON normalized_events (environment_id, provenance_group);

CREATE TABLE plans (
    plan_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    context_id TEXT NOT NULL, 
    model_run_id TEXT, 
    hypotheses JSONB NOT NULL, 
    tasks JSONB NOT NULL, 
    stop_conditions JSONB NOT NULL, 
    max_replans INTEGER NOT NULL, 
    total_model_calls INTEGER NOT NULL, 
    CONSTRAINT pk_plans PRIMARY KEY (plan_id), 
    CONSTRAINT ck_plans_plans_hypotheses_json CHECK (jsonb_typeof(hypotheses) = 'array'), 
    CONSTRAINT ck_plans_plans_stop_conditions_json CHECK (jsonb_typeof(stop_conditions) = 'array'), 
    CONSTRAINT ck_plans_plans_tasks_json CHECK (jsonb_typeof(tasks) = 'array'), 
    CONSTRAINT ck_plans_plans_hypotheses_minitems CHECK (jsonb_array_length(hypotheses) >= 1), 
    CONSTRAINT ck_plans_plans_stop_conditions_minitems CHECK (jsonb_array_length(stop_conditions) >= 1), 
    CONSTRAINT ck_plans_plans_tasks_minitems CHECK (jsonb_array_length(tasks) >= 1), 
    CONSTRAINT ck_plans_plans_plan_id_nonempty CHECK (length(plan_id) > 0), 
    CONSTRAINT ck_plans_plans_max_replans_minimum CHECK (max_replans >= 0), 
    CONSTRAINT ck_plans_plans_total_model_calls_minimum CHECK (total_model_calls >= 0), 
    CONSTRAINT fk_plan_context FOREIGN KEY(environment_id, incident_id, context_id) REFERENCES context_bundles (environment_id, incident_id, context_id), 
    CONSTRAINT fk_plans_incident FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_plan_model FOREIGN KEY(environment_id, model_run_id) REFERENCES model_runs (environment_id, run_id), 
    CONSTRAINT fk_plans_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_plans_environment_id UNIQUE (environment_id, plan_id)
);

CREATE TABLE verification_results (
    verification_id TEXT NOT NULL, 
    verification_spec_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    action_id TEXT, 
    validation_run_id TEXT NOT NULL, 
    objective_type TEXT NOT NULL, 
    claim TEXT NOT NULL, 
    target_ids JSONB NOT NULL, 
    scope_id TEXT NOT NULL, 
    scenario_version TEXT NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    finished_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    security_status TEXT NOT NULL, 
    business_status TEXT NOT NULL, 
    observation_status TEXT NOT NULL, 
    status TEXT NOT NULL, 
    evidence_ids JSONB NOT NULL, 
    expected_result TEXT NOT NULL, 
    observed_result TEXT NOT NULL, 
    residual_risks JSONB NOT NULL, 
    recommended_next_step TEXT NOT NULL, 
    CONSTRAINT pk_verification_results PRIMARY KEY (verification_id), 
    CONSTRAINT ck_verification_results_verification_results_business_s_d0d3 CHECK (business_status IN ('PASS', 'FAIL', 'INCONCLUSIVE')), 
    CONSTRAINT ck_verification_results_verification_results_evidence_ids_json CHECK (jsonb_typeof(evidence_ids) = 'array'), 
    CONSTRAINT ck_verification_results_verification_results_residual_r_21c2 CHECK (jsonb_typeof(residual_risks) = 'array'), 
    CONSTRAINT ck_verification_results_verification_results_target_ids_json CHECK (jsonb_typeof(target_ids) = 'array'), 
    CONSTRAINT ck_verification_results_verification_results_objective__3691 CHECK (objective_type IN ('DETECTION', 'CONTAINMENT', 'REMEDIATION', 'RECOVERY', 'CLEANUP')), 
    CONSTRAINT ck_verification_results_verification_results_observatio_e476 CHECK (observation_status IN ('PASS', 'FAIL', 'INCONCLUSIVE')), 
    CONSTRAINT ck_verification_results_verification_results_security_s_a2c6 CHECK (security_status IN ('PASS', 'FAIL', 'INCONCLUSIVE')), 
    CONSTRAINT ck_verification_results_verification_three_check CHECK (status = CASE WHEN security_status = 'FAIL' OR business_status = 'FAIL' THEN 'FAIL' WHEN security_status = 'PASS' AND business_status = 'PASS' AND observation_status = 'PASS' THEN 'PASS' ELSE 'INCONCLUSIVE' END), 
    CONSTRAINT ck_verification_results_verification_results_status_enum CHECK (status IN ('PASS', 'FAIL', 'INCONCLUSIVE')), 
    CONSTRAINT ck_verification_results_verification_interval CHECK (finished_at >= started_at AND valid_until >= finished_at), 
    CONSTRAINT ck_verification_results_verification_results_evidence_i_609b CHECK (jsonb_array_length(evidence_ids) >= 1), 
    CONSTRAINT ck_verification_results_verification_results_target_ids_bbe2 CHECK (jsonb_array_length(target_ids) >= 1), 
    CONSTRAINT ck_verification_results_verification_results_verificati_9f78 CHECK (length(verification_id) > 0), 
    CONSTRAINT fk_verification_action FOREIGN KEY(environment_id, incident_id, action_id) REFERENCES action_requests (environment_id, incident_id, action_id), 
    CONSTRAINT fk_verification_results_incident FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_verification_results_scope FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), 
    CONSTRAINT fk_verification_run FOREIGN KEY(environment_id, validation_run_id) REFERENCES validation_runs (environment_id, run_id), 
    CONSTRAINT fk_verification_results_environment FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT fk_verification_spec FOREIGN KEY(verification_spec_id) REFERENCES verification_specs (verification_spec_id), 
    CONSTRAINT uq_verification_results_environment_id UNIQUE (environment_id, verification_id)
);

CREATE TABLE authorization_decisions (
    authorization_id TEXT NOT NULL, 
    authorization_context_id TEXT NOT NULL, 
    action_id TEXT NOT NULL, 
    action_digest TEXT NOT NULL, 
    outcome TEXT NOT NULL, 
    assessed_risk TEXT NOT NULL, 
    business_impact TEXT NOT NULL, 
    human_approval_required BOOLEAN NOT NULL, 
    approval_id TEXT, 
    policy_version TEXT NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    reasons JSONB NOT NULL, 
    CONSTRAINT pk_authorization_decisions PRIMARY KEY (authorization_id), 
    CONSTRAINT ck_authorization_decisions_high_impact_human CHECK ((assessed_risk <> 'R5' AND business_impact NOT IN ('HIGH','CRITICAL')) OR human_approval_required), 
    CONSTRAINT ck_authorization_decisions_authorization_decisions_acti_73ea CHECK (action_digest ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_authorization_decisions_authorization_decisions_asse_32fb CHECK (assessed_risk IN ('R0', 'R1', 'R2', 'R3', 'R4', 'R5')), 
    CONSTRAINT ck_authorization_decisions_authorization_decisions_busi_ba1b CHECK (business_impact IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')), 
    CONSTRAINT ck_authorization_decisions_authorization_decisions_reasons_json CHECK (jsonb_typeof(reasons) = 'array'), 
    CONSTRAINT ck_authorization_decisions_allow_requires_approval CHECK (outcome <> 'ALLOW' OR NOT human_approval_required OR approval_id IS NOT NULL), 
    CONSTRAINT ck_authorization_decisions_authorization_decisions_outcome_enum CHECK (outcome IN ('ALLOW', 'DENY', 'REQUIRE_APPROVAL', 'DOWNGRADE')), 
    CONSTRAINT ck_authorization_decisions_authorization_decisions_reas_2267 CHECK (jsonb_array_length(reasons) >= 1), 
    CONSTRAINT ck_authorization_decisions_authorization_decisions_auth_1cc5 CHECK (length(authorization_id) > 0), 
    CONSTRAINT fk_decision_approval FOREIGN KEY(approval_id, action_id, action_digest) REFERENCES approvals (approval_id, action_id, action_digest), 
    CONSTRAINT fk_decision_context_binding FOREIGN KEY(authorization_context_id, action_id, action_digest) REFERENCES authorization_contexts (authorization_context_id, action_id, action_digest)
);

CREATE TABLE event_receipts (
    receipt_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    event_id TEXT NOT NULL, 
    submitted_event_id TEXT NOT NULL, 
    trace_id TEXT NOT NULL, 
    raw_ref TEXT NOT NULL, 
    received_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    submission_hash TEXT NOT NULL, 
    disposition TEXT NOT NULL, 
    CONSTRAINT pk_event_receipts PRIMARY KEY (receipt_id), 
    CONSTRAINT ck_event_receipts_receipt_disposition CHECK (disposition IN ('ACCEPTED','DUPLICATE')), 
    CONSTRAINT ck_event_receipts_receipt_hash CHECK (submission_hash ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT fk_event_receipts_environment_id_normalized_events FOREIGN KEY(environment_id, event_id) REFERENCES normalized_events (environment_id, event_id)
);

CREATE INDEX ix_receipts_event ON event_receipts (environment_id, event_id);

CREATE INDEX ix_receipts_trace ON event_receipts (trace_id);

CREATE TABLE event_resources (
    environment_id TEXT NOT NULL, 
    event_id TEXT NOT NULL, 
    resource_id TEXT NOT NULL, 
    role TEXT NOT NULL, 
    CONSTRAINT pk_event_resources PRIMARY KEY (environment_id, event_id, resource_id, role), 
    CONSTRAINT ck_event_resources_event_resource_role CHECK (role IN ('SOURCE','TARGET')), 
    CONSTRAINT fk_event_resources_environment_id_normalized_events FOREIGN KEY(environment_id, event_id) REFERENCES normalized_events (environment_id, event_id), 
    CONSTRAINT fk_event_resources_environment_id_resources FOREIGN KEY(environment_id, resource_id) REFERENCES resources (environment_id, resource_id)
);

ALTER TABLE tasks ADD CONSTRAINT fk_task_active_lease FOREIGN KEY(task_id, active_lease_id) REFERENCES worker_leases (task_id, lease_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE verification_specs ADD CONSTRAINT fk_spec_scenario FOREIGN KEY(scenario_id, scenario_version) REFERENCES validation_scenarios (scenario_id, version) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE validation_scenarios ADD CONSTRAINT fk_scenario_spec FOREIGN KEY(verification_spec_id) REFERENCES verification_specs (verification_spec_id) DEFERRABLE INITIALLY DEFERRED;

CREATE FUNCTION zhiyu_reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'immutable record: %', TG_TABLE_NAME USING ERRCODE = '23514'; END;
        $$;

CREATE TRIGGER immutable_audit_entries BEFORE UPDATE OR DELETE ON audit_entries FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_event_receipts BEFORE UPDATE OR DELETE ON event_receipts FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_normalized_events BEFORE UPDATE OR DELETE ON normalized_events FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_action_requests BEFORE UPDATE OR DELETE ON action_requests FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_approvals BEFORE UPDATE OR DELETE ON approvals FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_authorization_contexts BEFORE UPDATE OR DELETE ON authorization_contexts FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_authorization_decisions BEFORE UPDATE OR DELETE ON authorization_decisions FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

ALTER TABLE normalized_events ADD CONSTRAINT ck_normalized_events_event_specversion CHECK (specversion = '1.0');

ALTER TABLE evidence ADD CONSTRAINT ck_evidence_evidence_hash_algorithm CHECK (hash_algorithm = 'SHA256');

ALTER TABLE verification_specs ADD CONSTRAINT ck_verification_specs_verification_aggregation CHECK (aggregation_rule = 'THREE_DIMENSION_STRICT');

INSERT INTO alembic_version (version_num) VALUES ('0001_m1_1') RETURNING alembic_version.version_num;

-- Running upgrade 0001_m1_1 -> 0002_adapters

CREATE TABLE raw_records (
    raw_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    collector_id TEXT NOT NULL, 
    source_type TEXT NOT NULL, 
    content BYTEA NOT NULL, 
    integrity_hash TEXT NOT NULL, 
    received_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_raw_records PRIMARY KEY (raw_id), 
    CONSTRAINT fk_raw_records_environment_id_environments FOREIGN KEY(environment_id) REFERENCES environments (environment_id), 
    CONSTRAINT uq_raw_environment_id UNIQUE (environment_id, raw_id), 
    CONSTRAINT ck_raw_records_raw_hash CHECK (integrity_hash ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_raw_records_raw_size CHECK (octet_length(content) <= 262144)
);

CREATE TABLE raw_deliveries (
    delivery_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    raw_id TEXT NOT NULL, 
    event_id TEXT, 
    trace_id TEXT NOT NULL, 
    disposition TEXT NOT NULL, 
    error_code TEXT, 
    error_field TEXT, 
    normalization_ms FLOAT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_raw_deliveries PRIMARY KEY (delivery_id), 
    CONSTRAINT fk_raw_deliveries_environment_id_raw_records FOREIGN KEY(environment_id, raw_id) REFERENCES raw_records (environment_id, raw_id), 
    CONSTRAINT fk_raw_deliveries_environment_id_normalized_events FOREIGN KEY(environment_id, event_id) REFERENCES normalized_events (environment_id, event_id), 
    CONSTRAINT ck_raw_deliveries_raw_disposition CHECK (disposition IN ('ACCEPTED','DUPLICATE','ERROR')), 
    CONSTRAINT ck_raw_deliveries_raw_error_pair CHECK ((disposition = 'ERROR') = (error_code IS NOT NULL)), 
    CONSTRAINT ck_raw_deliveries_raw_event_pair CHECK ((disposition = 'ERROR') = (event_id IS NULL)), 
    CONSTRAINT ck_raw_deliveries_normalization_duration CHECK (normalization_ms >= 0)
);

CREATE INDEX ix_raw_deliveries_environment_time ON raw_deliveries (environment_id, created_at, delivery_id);

CREATE TRIGGER immutable_raw_records BEFORE UPDATE OR DELETE ON raw_records FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_raw_deliveries BEFORE UPDATE OR DELETE ON raw_deliveries FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

UPDATE alembic_version SET version_num='0002_adapters' WHERE alembic_version.version_num = '0001_m1_1';

-- Running upgrade 0002_adapters -> 0003_correlation

CREATE TABLE intelligence_runs (
    run_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    processed INTEGER NOT NULL, 
    groups_created INTEGER NOT NULL, 
    decisions_created INTEGER NOT NULL, 
    correlation_ms FLOAT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_intelligence_runs PRIMARY KEY (run_id), 
    CONSTRAINT ck_intelligence_runs_intelligence_counts CHECK (processed >= 0 AND groups_created >= 0 AND decisions_created >= 0 AND correlation_ms >= 0), 
    CONSTRAINT fk_intelligence_runs_environment_id_environments FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE INDEX ix_intelligence_run_environment ON intelligence_runs (environment_id, created_at);

CREATE TABLE event_group_state (
    environment_id TEXT NOT NULL, 
    group_id TEXT NOT NULL, 
    key_hash TEXT NOT NULL, 
    window_start TIMESTAMP WITH TIME ZONE NOT NULL, 
    window_end TIMESTAMP WITH TIME ZONE NOT NULL, 
    status TEXT NOT NULL, 
    disposition TEXT NOT NULL, 
    version INTEGER NOT NULL, 
    summary JSONB NOT NULL, 
    config JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_event_group_state PRIMARY KEY (environment_id, group_id), 
    CONSTRAINT ck_event_group_state_group_disposition CHECK (disposition IN ('TIMELY','LATE','EXPIRED','FUTURE')), 
    CONSTRAINT ck_event_group_state_group_state_status CHECK (status IN ('OPEN','CLOSED')), 
    CONSTRAINT ck_event_group_state_group_state_bounds CHECK (version >= 1 AND window_end > window_start AND updated_at >= created_at), 
    CONSTRAINT fk_event_group_state_environment_id_event_groups FOREIGN KEY(environment_id, group_id) REFERENCES event_groups (environment_id, group_id), 
    CONSTRAINT uq_group_logical_key UNIQUE (environment_id, key_hash)
);

CREATE INDEX ix_group_state_window ON event_group_state (environment_id, status, window_end);

CREATE TABLE correlation_decision_inputs (
    environment_id TEXT NOT NULL, 
    decision_id TEXT NOT NULL, 
    event_id TEXT NOT NULL, 
    role TEXT NOT NULL, 
    reason TEXT NOT NULL, 
    CONSTRAINT pk_correlation_decision_inputs PRIMARY KEY (environment_id, decision_id, event_id, role), 
    CONSTRAINT ck_correlation_decision_inputs_decision_input_role CHECK (role IN ('INPUT','EXCLUDED')), 
    CONSTRAINT fk_correlation_decision_inputs_environment_id_correlati_9c1d FOREIGN KEY(environment_id, decision_id) REFERENCES correlation_decisions (environment_id, decision_id), 
    CONSTRAINT fk_correlation_decision_inputs_environment_id_normalized_events FOREIGN KEY(environment_id, event_id) REFERENCES normalized_events (environment_id, event_id)
);

CREATE TABLE event_group_members (
    environment_id TEXT NOT NULL, 
    event_id TEXT NOT NULL, 
    group_id TEXT NOT NULL, 
    added_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_event_group_members PRIMARY KEY (environment_id, event_id), 
    CONSTRAINT fk_event_group_members_environment_id_normalized_events FOREIGN KEY(environment_id, event_id) REFERENCES normalized_events (environment_id, event_id), 
    CONSTRAINT fk_event_group_members_environment_id_event_groups FOREIGN KEY(environment_id, group_id) REFERENCES event_groups (environment_id, group_id)
);

CREATE INDEX ix_members_group ON event_group_members (environment_id, group_id, event_id);

UPDATE alembic_version SET version_num='0003_correlation' WHERE alembic_version.version_num = '0002_adapters';

-- Running upgrade 0003_correlation -> 0004_incidents

ALTER TABLE evidence ADD CONSTRAINT uq_evidence_incident_owner UNIQUE (environment_id, incident_id, evidence_id);

CREATE TABLE incident_analysis (
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    merge_key TEXT NOT NULL, 
    policy_hash TEXT NOT NULL, 
    score INTEGER NOT NULL, 
    factors JSONB NOT NULL, 
    config JSONB NOT NULL, 
    last_observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_incident_analysis PRIMARY KEY (environment_id, incident_id), 
    CONSTRAINT ck_incident_analysis_incident_analysis_score CHECK (score BETWEEN 0 AND 100), 
    CONSTRAINT fk_incident_analysis_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id)
);

CREATE INDEX ix_incident_merge ON incident_analysis (environment_id, merge_key, policy_hash);

CREATE INDEX ix_incident_risk ON incident_analysis (environment_id, score, incident_id);

CREATE TABLE incident_groups (
    environment_id TEXT NOT NULL, 
    group_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    group_version INTEGER NOT NULL, 
    CONSTRAINT pk_incident_groups PRIMARY KEY (environment_id, group_id), 
    CONSTRAINT ck_incident_groups_incident_group_version CHECK (group_version >= 1), 
    CONSTRAINT fk_incident_groups_environment_id_event_groups FOREIGN KEY(environment_id, group_id) REFERENCES event_groups (environment_id, group_id), 
    CONSTRAINT fk_incident_groups_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id)
);

CREATE INDEX ix_incident_groups_incident ON incident_groups (environment_id, incident_id, group_id);

CREATE TABLE incident_promotions (
    environment_id TEXT NOT NULL, 
    group_id TEXT NOT NULL, 
    group_version INTEGER NOT NULL, 
    policy_hash TEXT NOT NULL, 
    incident_id TEXT, 
    outcome TEXT NOT NULL, 
    explanation JSONB NOT NULL, 
    promotion_ms FLOAT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_incident_promotions PRIMARY KEY (environment_id, group_id, group_version, policy_hash), 
    CONSTRAINT ck_incident_promotions_promotion_outcome CHECK (outcome IN ('CREATED','MERGED','UPDATED','NOT_PROMOTED')), 
    CONSTRAINT ck_incident_promotions_promotion_bounds CHECK (group_version >= 1 AND promotion_ms >= 0), 
    CONSTRAINT fk_incident_promotions_environment_id_event_groups FOREIGN KEY(environment_id, group_id) REFERENCES event_groups (environment_id, group_id), 
    CONSTRAINT fk_incident_promotions_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id)
);

CREATE TABLE incident_events (
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    event_id TEXT NOT NULL, 
    evidence_id TEXT NOT NULL, 
    CONSTRAINT pk_incident_events PRIMARY KEY (environment_id, incident_id, event_id), 
    CONSTRAINT fk_incident_events_environment_id_normalized_events FOREIGN KEY(environment_id, event_id) REFERENCES normalized_events (environment_id, event_id), 
    CONSTRAINT fk_incident_events_environment_id_evidence FOREIGN KEY(environment_id, incident_id, evidence_id) REFERENCES evidence (environment_id, incident_id, evidence_id), 
    CONSTRAINT fk_incident_events_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id)
);

UPDATE alembic_version SET version_num='0004_incidents' WHERE alembic_version.version_num = '0003_correlation';

-- Running upgrade 0004_incidents -> 0005_plans

CREATE TABLE response_plan_metadata (
    plan_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    incident_version INTEGER NOT NULL, 
    planner_version TEXT NOT NULL, 
    policy_version TEXT NOT NULL, 
    scope_id TEXT NOT NULL, 
    snapshot_hash TEXT NOT NULL, 
    inputs JSONB NOT NULL, 
    configuration JSONB NOT NULL, 
    reasons JSONB NOT NULL, 
    created_by TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    generation_ms FLOAT NOT NULL, 
    graph_ms FLOAT NOT NULL, 
    CONSTRAINT pk_response_plan_metadata PRIMARY KEY (plan_id), 
    CONSTRAINT ck_response_plan_metadata_response_plan_metrics CHECK (incident_version >= 1 AND generation_ms >= 0 AND graph_ms >= 0), 
    CONSTRAINT fk_response_plan_metadata_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_response_plan_metadata_environment_id_plans FOREIGN KEY(environment_id, plan_id) REFERENCES plans (environment_id, plan_id), 
    CONSTRAINT fk_response_plan_metadata_environment_id_scopes FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), 
    CONSTRAINT uq_response_plan_identity UNIQUE (environment_id, incident_id, incident_version, planner_version, policy_version), 
    CONSTRAINT uq_response_plan_environment UNIQUE (environment_id, plan_id)
);

CREATE INDEX ix_response_plan_time ON response_plan_metadata (environment_id, created_at, plan_id);

CREATE TABLE task_runtime (
    task_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    plan_id TEXT NOT NULL, 
    task_type TEXT NOT NULL, 
    ready_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    failure_code TEXT, 
    result_ref TEXT, 
    generation INTEGER NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_task_runtime PRIMARY KEY (task_id), 
    CONSTRAINT ck_task_runtime_task_runtime_generation CHECK (generation >= 0 AND row_version >= 1), 
    CONSTRAINT fk_task_runtime_environment_id_response_plan_metadata FOREIGN KEY(environment_id, plan_id) REFERENCES response_plan_metadata (environment_id, plan_id), 
    CONSTRAINT fk_task_runtime_environment_id_tasks FOREIGN KEY(environment_id, task_id) REFERENCES tasks (environment_id, task_id), 
    CONSTRAINT uq_runtime_plan_task UNIQUE (environment_id, plan_id, task_id)
);

CREATE INDEX ix_task_runtime_ready ON task_runtime (environment_id, ready_at, task_id);

CREATE TABLE task_graph_edges (
    environment_id TEXT NOT NULL, 
    plan_id TEXT NOT NULL, 
    task_id TEXT NOT NULL, 
    depends_on TEXT NOT NULL, 
    CONSTRAINT pk_task_graph_edges PRIMARY KEY (environment_id, plan_id, task_id, depends_on), 
    CONSTRAINT ck_task_graph_edges_task_edge_no_self CHECK (task_id <> depends_on), 
    CONSTRAINT fk_task_edge_dependency FOREIGN KEY(environment_id, plan_id, depends_on) REFERENCES task_runtime (environment_id, plan_id, task_id), 
    CONSTRAINT fk_task_edge_task FOREIGN KEY(environment_id, plan_id, task_id) REFERENCES task_runtime (environment_id, plan_id, task_id)
);

CREATE INDEX ix_task_edge_blocks ON task_graph_edges (environment_id, depends_on);

CREATE TRIGGER immutable_plans BEFORE UPDATE OR DELETE ON plans FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_task_graph_edges BEFORE UPDATE OR DELETE ON task_graph_edges FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE FUNCTION zhiyu_guard_plan_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' OR
             (to_jsonb(NEW) - 'graph_ms' - 'generation_ms') IS DISTINCT FROM
             (to_jsonb(OLD) - 'graph_ms' - 'generation_ms') THEN
            RAISE EXCEPTION 'immutable plan snapshot' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$;

CREATE TRIGGER immutable_response_plan_snapshot BEFORE UPDATE OR DELETE ON response_plan_metadata FOR EACH ROW EXECUTE FUNCTION zhiyu_guard_plan_snapshot();

UPDATE alembic_version SET version_num='0005_plans' WHERE alembic_version.version_num = '0004_incidents';

-- Running upgrade 0005_plans -> 0006_authority

CREATE TABLE capability_health_observations (
    observation_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    capability_id TEXT NOT NULL, 
    capability_version TEXT NOT NULL, 
    worker_pool TEXT NOT NULL, 
    checked_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    status TEXT NOT NULL, 
    latency_ms INTEGER, 
    failure_reason TEXT, 
    CONSTRAINT pk_capability_health_observations PRIMARY KEY (observation_id), 
    CONSTRAINT ck_capability_health_observations_capability_observation_status CHECK (status IN ('UNVERIFIED','HEALTHY','DEGRADED','OFFLINE')), 
    CONSTRAINT fk_capability_health_observations_capability_id_capabilities FOREIGN KEY(capability_id, capability_version) REFERENCES capabilities (capability_id, version), 
    CONSTRAINT fk_capability_health_observations_environment_id_environments FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE INDEX ix_capability_health_observed ON capability_health_observations (environment_id, capability_id, checked_at);

CREATE TABLE capability_runtime_config (
    capability_id TEXT NOT NULL, 
    version TEXT NOT NULL, 
    active BOOLEAN NOT NULL, 
    definition_hash TEXT NOT NULL, 
    supported_resource_types JSONB NOT NULL, 
    supported_profiles JSONB NOT NULL, 
    minimum_autonomy TEXT NOT NULL, 
    business_impact TEXT NOT NULL, 
    retry_policy JSONB NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_capability_runtime_config PRIMARY KEY (capability_id, version), 
    CONSTRAINT ck_capability_runtime_config_capability_runtime_impact CHECK (business_impact IN ('LOW','MEDIUM','HIGH','CRITICAL') AND row_version >= 1), 
    CONSTRAINT fk_capability_runtime_config_capability_id_capabilities FOREIGN KEY(capability_id, version) REFERENCES capabilities (capability_id, version)
);

CREATE TABLE response_controls (
    environment_id TEXT NOT NULL, 
    policy_version TEXT NOT NULL, 
    enabled BOOLEAN NOT NULL, 
    configuration JSONB NOT NULL, 
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    next_probe_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_response_controls PRIMARY KEY (environment_id), 
    CONSTRAINT ck_response_controls_response_control_interval CHECK (valid_until > valid_from AND row_version >= 1), 
    CONSTRAINT fk_response_controls_environment_id_environments FOREIGN KEY(environment_id) REFERENCES environments (environment_id)
);

CREATE TABLE response_budgets (
    budget_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    plan_id TEXT NOT NULL, 
    max_actions INTEGER NOT NULL, 
    used_actions INTEGER NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_response_budgets PRIMARY KEY (budget_id), 
    CONSTRAINT ck_response_budgets_response_budget_limit CHECK (max_actions >= 1 AND used_actions >= 0 AND used_actions <= max_actions), 
    CONSTRAINT fk_response_budgets_environment_id_response_plan_metadata FOREIGN KEY(environment_id, plan_id) REFERENCES response_plan_metadata (environment_id, plan_id), 
    CONSTRAINT uq_response_budget_environment UNIQUE (environment_id, budget_id), 
    CONSTRAINT uq_response_budget_plan UNIQUE (environment_id, plan_id)
);

CREATE TABLE action_control (
    action_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    task_id TEXT NOT NULL, 
    budget_id TEXT NOT NULL, 
    status TEXT NOT NULL, 
    authorization_id TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_action_control PRIMARY KEY (action_id), 
    CONSTRAINT ck_action_control_action_control_status CHECK (status IN ('PROPOSED','AUTHORIZED','WAITING_APPROVAL','DENIED','EXPIRED','DISPATCHED','EXECUTING','EXECUTED','FAILED','EXECUTION_UNKNOWN','RECONCILING','NEEDS_MANUAL','CANCELLED')), 
    CONSTRAINT fk_action_control_authorization_id_authorization_decisions FOREIGN KEY(authorization_id) REFERENCES authorization_decisions (authorization_id), 
    CONSTRAINT fk_action_control_environment_id_action_requests FOREIGN KEY(environment_id, action_id) REFERENCES action_requests (environment_id, action_id), 
    CONSTRAINT fk_action_control_environment_id_response_budgets FOREIGN KEY(environment_id, budget_id) REFERENCES response_budgets (environment_id, budget_id), 
    CONSTRAINT fk_action_control_environment_id_tasks FOREIGN KEY(environment_id, task_id) REFERENCES tasks (environment_id, task_id), 
    CONSTRAINT uq_action_control_task UNIQUE (environment_id, task_id)
);

CREATE INDEX ix_action_control_time ON action_control (environment_id, created_at, action_id);

CREATE TABLE response_authorization_snapshots (
    context_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    action_id TEXT NOT NULL, 
    budget_id TEXT NOT NULL, 
    inputs JSONB NOT NULL, 
    rule_id TEXT NOT NULL, 
    denied_dimensions JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    authorization_ms FLOAT NOT NULL, 
    policy_ms FLOAT NOT NULL, 
    CONSTRAINT pk_response_authorization_snapshots PRIMARY KEY (context_id), 
    CONSTRAINT ck_response_authorization_snapshots_response_authorizat_ec6b CHECK (authorization_ms >= 0 AND policy_ms >= 0), 
    CONSTRAINT fk_response_authorization_snapshots_context_id_authoriz_b449 FOREIGN KEY(context_id) REFERENCES authorization_contexts (authorization_context_id), 
    CONSTRAINT fk_response_authorization_snapshots_environment_id_acti_2a78 FOREIGN KEY(environment_id, action_id) REFERENCES action_requests (environment_id, action_id), 
    CONSTRAINT fk_response_authorization_snapshots_environment_id_resp_2375 FOREIGN KEY(environment_id, budget_id) REFERENCES response_budgets (environment_id, budget_id)
);

CREATE TRIGGER immutable_response_authorization_snapshots BEFORE UPDATE OR DELETE ON response_authorization_snapshots FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_capability_health_observations BEFORE UPDATE OR DELETE ON capability_health_observations FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

UPDATE alembic_version SET version_num='0006_authority' WHERE alembic_version.version_num = '0005_plans';

-- Running upgrade 0006_authority -> 0007_execution

CREATE TABLE action_dispatches (
    attempt_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    action_id TEXT NOT NULL, 
    task_id TEXT NOT NULL, 
    lease_id TEXT NOT NULL, 
    generation INTEGER NOT NULL, 
    authorization_id TEXT NOT NULL, 
    gateway_ms FLOAT NOT NULL, 
    CONSTRAINT pk_action_dispatches PRIMARY KEY (attempt_id), 
    CONSTRAINT ck_action_dispatches_dispatch_generation CHECK (generation >= 1 AND gateway_ms >= 0), 
    CONSTRAINT fk_action_dispatches_attempt_id_action_attempts FOREIGN KEY(attempt_id) REFERENCES action_attempts (attempt_id), 
    CONSTRAINT fk_action_dispatches_authorization_id_authorization_decisions FOREIGN KEY(authorization_id) REFERENCES authorization_decisions (authorization_id), 
    CONSTRAINT fk_action_dispatches_environment_id_action_requests FOREIGN KEY(environment_id, action_id) REFERENCES action_requests (environment_id, action_id), 
    CONSTRAINT fk_action_dispatches_environment_id_tasks FOREIGN KEY(environment_id, task_id) REFERENCES tasks (environment_id, task_id), 
    CONSTRAINT fk_action_dispatches_task_id_worker_leases FOREIGN KEY(task_id, lease_id) REFERENCES worker_leases (task_id, lease_id), 
    CONSTRAINT uq_action_dispatch_generation UNIQUE (action_id, generation)
);

CREATE TABLE action_execution_results (
    attempt_id TEXT NOT NULL, 
    execution_outcome TEXT NOT NULL, 
    executor TEXT NOT NULL, 
    executor_version TEXT NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    executor_ms FLOAT NOT NULL, 
    output JSONB NOT NULL, 
    output_hash TEXT NOT NULL, 
    error_code TEXT, 
    retryable BOOLEAN NOT NULL, 
    side_effect TEXT NOT NULL, 
    CONSTRAINT pk_action_execution_results PRIMARY KEY (attempt_id), 
    CONSTRAINT ck_action_execution_results_action_result_outcome CHECK (execution_outcome IN ('EXECUTION_SUCCESS','EXECUTION_FAILURE','TIMEOUT','DENIED','STALE')), 
    CONSTRAINT ck_action_execution_results_action_result_hash CHECK (output_hash ~ '^[0-9a-f]{64}$'), 
    CONSTRAINT ck_action_execution_results_action_result_read_only CHECK (side_effect = 'NONE' AND completed_at >= started_at AND executor_ms >= 0), 
    CONSTRAINT fk_action_execution_results_attempt_id_action_dispatches FOREIGN KEY(attempt_id) REFERENCES action_dispatches (attempt_id)
);

ALTER TABLE task_runtime ADD COLUMN retry_allowed BOOLEAN DEFAULT 'false' NOT NULL;

CREATE TRIGGER immutable_action_dispatches BEFORE UPDATE OR DELETE ON action_dispatches FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_action_execution_results BEFORE UPDATE OR DELETE ON action_execution_results FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

UPDATE alembic_version SET version_num='0007_execution' WHERE alembic_version.version_num = '0006_authority';

-- Running upgrade 0007_execution -> 0008_verification

CREATE TABLE verification_runtime (
    spec_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    plan_id TEXT NOT NULL, 
    task_id TEXT NOT NULL, 
    action_id TEXT NOT NULL, 
    action_result_id TEXT NOT NULL, 
    scope_id TEXT NOT NULL, 
    run_id TEXT NOT NULL, 
    policy JSONB NOT NULL, 
    binding JSONB NOT NULL, 
    spec_hash TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    generation_ms FLOAT NOT NULL, 
    CONSTRAINT pk_verification_runtime PRIMARY KEY (spec_id), 
    CONSTRAINT fk_verification_runtime_spec_id_verification_specs FOREIGN KEY(spec_id) REFERENCES verification_specs (verification_spec_id), 
    CONSTRAINT fk_verification_runtime_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_verification_runtime_environment_id_task_runtime FOREIGN KEY(environment_id, plan_id, task_id) REFERENCES task_runtime (environment_id, plan_id, task_id), 
    CONSTRAINT fk_verification_runtime_environment_id_action_requests FOREIGN KEY(environment_id, action_id) REFERENCES action_requests (environment_id, action_id), 
    CONSTRAINT fk_verification_runtime_action_result_id_action_executi_cdac FOREIGN KEY(action_result_id) REFERENCES action_execution_results (attempt_id), 
    CONSTRAINT fk_verification_runtime_environment_id_scopes FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), 
    CONSTRAINT fk_verification_runtime_environment_id_validation_runs FOREIGN KEY(environment_id, run_id) REFERENCES validation_runs (environment_id, run_id), 
    CONSTRAINT uq_verification_runtime_env UNIQUE (environment_id, spec_id), 
    CONSTRAINT ck_verification_runtime_verification_runtime_interval CHECK (valid_until > created_at AND generation_ms >= 0)
);

CREATE TABLE verification_checks (
    spec_id TEXT NOT NULL, 
    check_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    definition JSONB NOT NULL, 
    status TEXT NOT NULL, 
    generation INTEGER NOT NULL, 
    worker_id TEXT, 
    lease_until TIMESTAMP WITH TIME ZONE, 
    started_at TIMESTAMP WITH TIME ZONE, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_verification_checks PRIMARY KEY (spec_id, check_id), 
    CONSTRAINT fk_verification_checks_environment_id_verification_runtime FOREIGN KEY(environment_id, spec_id) REFERENCES verification_runtime (environment_id, spec_id), 
    CONSTRAINT ck_verification_checks_verification_check_status CHECK (status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','TIMEOUT','INCONCLUSIVE','CANCELLED')), 
    CONSTRAINT ck_verification_checks_verification_check_generation CHECK (generation >= 0 AND row_version >= 1), 
    CONSTRAINT ck_verification_checks_verification_check_lease CHECK ((status = 'RUNNING') = (worker_id IS NOT NULL AND lease_until IS NOT NULL))
);

CREATE TABLE verification_observations (
    spec_id TEXT NOT NULL, 
    check_id TEXT NOT NULL, 
    evidence_id TEXT NOT NULL, 
    generation INTEGER NOT NULL, 
    execution_status TEXT NOT NULL, 
    assertion_status TEXT NOT NULL, 
    samples JSONB NOT NULL, 
    assertions JSONB NOT NULL, 
    reason TEXT NOT NULL, 
    executor_version TEXT NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    checked_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    latency_ms FLOAT NOT NULL, 
    CONSTRAINT pk_verification_observations PRIMARY KEY (spec_id, check_id), 
    CONSTRAINT fk_verification_observations_spec_id_verification_checks FOREIGN KEY(spec_id, check_id) REFERENCES verification_checks (spec_id, check_id), 
    CONSTRAINT fk_verification_observations_evidence_id_evidence FOREIGN KEY(evidence_id) REFERENCES evidence (evidence_id), 
    CONSTRAINT uq_verification_observation_evidence UNIQUE (evidence_id), 
    CONSTRAINT ck_verification_observations_verification_assertion_status CHECK (assertion_status IN ('PASS','FAIL','INCONCLUSIVE')), 
    CONSTRAINT ck_verification_observations_verification_observation_interval CHECK (checked_at >= started_at AND generation >= 1 AND latency_ms >= 0)
);

CREATE TRIGGER immutable_verification_runtime BEFORE UPDATE OR DELETE ON verification_runtime FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_verification_observations BEFORE UPDATE OR DELETE ON verification_observations FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

UPDATE alembic_version SET version_num='0008_verification' WHERE alembic_version.version_num = '0007_execution';

-- Running upgrade 0008_verification -> 0009_decisions

CREATE TABLE verification_effectiveness (
    verification_id TEXT NOT NULL, 
    raw_dimensions JSONB NOT NULL, 
    qualification_failures JSONB NOT NULL, 
    decision JSONB NOT NULL, 
    decided_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    decision_ms FLOAT NOT NULL, 
    CONSTRAINT pk_verification_effectiveness PRIMARY KEY (verification_id), 
    CONSTRAINT fk_verification_effectiveness_verification_id_verificat_50be FOREIGN KEY(verification_id) REFERENCES verification_results (verification_id)
);

CREATE TRIGGER immutable_verification_effectiveness BEFORE UPDATE OR DELETE ON verification_effectiveness FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

UPDATE alembic_version SET version_num='0009_decisions' WHERE alembic_version.version_num = '0008_verification';

-- Running upgrade 0009_decisions -> 0010_replan

CREATE TABLE response_cycles (
    plan_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    expected_version INTEGER NOT NULL, 
    semantic_hash TEXT NOT NULL, 
    root_plan_id TEXT NOT NULL, 
    parent_plan_id TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_response_cycles PRIMARY KEY (plan_id), 
    CONSTRAINT fk_response_cycles_environment_id_plans FOREIGN KEY(environment_id, plan_id) REFERENCES plans (environment_id, plan_id), 
    CONSTRAINT fk_response_cycles_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_response_cycles_root_plan_id_plans FOREIGN KEY(root_plan_id) REFERENCES plans (plan_id), 
    CONSTRAINT fk_response_cycles_parent_plan_id_plans FOREIGN KEY(parent_plan_id) REFERENCES plans (plan_id)
);

CREATE TABLE replan_budgets (
    root_plan_id TEXT NOT NULL, 
    configuration JSONB NOT NULL, 
    current_replan_count INTEGER NOT NULL, 
    reserved_actions INTEGER NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_replan_budgets PRIMARY KEY (root_plan_id), 
    CONSTRAINT fk_replan_budgets_root_plan_id_plans FOREIGN KEY(root_plan_id) REFERENCES plans (plan_id), 
    CONSTRAINT ck_replan_budgets_replan_budget_counts CHECK (current_replan_count >= 0 AND reserved_actions >= 0)
);

CREATE TABLE replan_decisions (
    verification_id TEXT NOT NULL, 
    root_plan_id TEXT NOT NULL, 
    parent_plan_id TEXT NOT NULL, 
    new_plan_id TEXT, 
    status TEXT NOT NULL, 
    reason TEXT NOT NULL, 
    replan_count INTEGER NOT NULL, 
    policy_version TEXT NOT NULL, 
    plan_fingerprint TEXT NOT NULL, 
    action_fingerprint TEXT NOT NULL, 
    evidence_fingerprint TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    latency_ms FLOAT NOT NULL, 
    CONSTRAINT pk_replan_decisions PRIMARY KEY (verification_id), 
    CONSTRAINT fk_replan_decisions_verification_id_verification_results FOREIGN KEY(verification_id) REFERENCES verification_results (verification_id), 
    CONSTRAINT fk_replan_decisions_root_plan_id_plans FOREIGN KEY(root_plan_id) REFERENCES plans (plan_id), 
    CONSTRAINT fk_replan_decisions_parent_plan_id_plans FOREIGN KEY(parent_plan_id) REFERENCES plans (plan_id), 
    CONSTRAINT fk_replan_decisions_new_plan_id_plans FOREIGN KEY(new_plan_id) REFERENCES plans (plan_id), 
    CONSTRAINT uq_replan_new_plan UNIQUE (new_plan_id), 
    CONSTRAINT ck_replan_decisions_replan_status CHECK (status IN ('NO_REPLAN','CREATED','REPLAN_EXHAUSTED','REQUIRE_APPROVAL','BLOCKED'))
);

CREATE TABLE verification_state_updates (
    verification_id TEXT NOT NULL, 
    entity_ids JSONB NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    latency_ms FLOAT NOT NULL, 
    CONSTRAINT pk_verification_state_updates PRIMARY KEY (verification_id), 
    CONSTRAINT fk_verification_state_updates_verification_id_verificat_c53d FOREIGN KEY(verification_id) REFERENCES verification_results (verification_id)
);

CREATE TRIGGER immutable_replan_decisions BEFORE UPDATE OR DELETE ON replan_decisions FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TRIGGER immutable_verification_state_updates BEFORE UPDATE OR DELETE ON verification_state_updates FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE FUNCTION zhiyu_m4_protect_contract() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
IF TG_TABLE_NAME = 'verification_checks' THEN
  IF TG_OP = 'DELETE' OR NEW.definition IS DISTINCT FROM OLD.definition OR NEW.spec_id <> OLD.spec_id OR NEW.check_id <> OLD.check_id OR NEW.environment_id <> OLD.environment_id THEN
    RAISE EXCEPTION 'immutable verification check identity';
  END IF;
ELSE
  IF EXISTS (SELECT 1 FROM verification_runtime WHERE spec_id = OLD.verification_spec_id) THEN
    RAISE EXCEPTION 'immutable managed verification contract';
  END IF;
END IF;
RETURN NEW;
END $$;

CREATE TRIGGER m4_frozen_specs BEFORE UPDATE OR DELETE ON verification_specs FOR EACH ROW EXECUTE FUNCTION zhiyu_m4_protect_contract();

CREATE TRIGGER m4_frozen_results BEFORE UPDATE OR DELETE ON verification_results FOR EACH ROW EXECUTE FUNCTION zhiyu_m4_protect_contract();

CREATE TRIGGER m4_frozen_checks BEFORE UPDATE OR DELETE ON verification_checks FOR EACH ROW EXECUTE FUNCTION zhiyu_m4_protect_contract();

UPDATE alembic_version SET version_num='0010_replan' WHERE alembic_version.version_num = '0009_decisions';

-- Running upgrade 0010_replan -> 0011_ai_context

CREATE TABLE ai_state_snapshots (
    snapshot_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    incident_version INTEGER NOT NULL, 
    body JSONB NOT NULL, 
    body_hash TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_ai_state_snapshots PRIMARY KEY (snapshot_id), 
    CONSTRAINT fk_ai_state_snapshots_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT uq_ai_state_environment UNIQUE (environment_id, snapshot_id), 
    CONSTRAINT ck_ai_state_snapshots_ai_state_integrity CHECK (body_hash ~ '^[0-9a-f]{64}$' AND incident_version >= 1 AND valid_until > created_at)
);

CREATE TRIGGER immutable_ai_state_snapshots BEFORE UPDATE OR DELETE ON ai_state_snapshots FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE TABLE decision_contexts (
    context_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    snapshot_id TEXT NOT NULL, 
    scope_id TEXT NOT NULL, 
    body JSONB NOT NULL, 
    manifest JSONB NOT NULL, 
    context_hash TEXT NOT NULL, 
    policy JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    build_ms FLOAT NOT NULL, 
    CONSTRAINT pk_decision_contexts PRIMARY KEY (context_id), 
    CONSTRAINT fk_decision_contexts_context_id_context_bundles FOREIGN KEY(context_id) REFERENCES context_bundles (context_id), 
    CONSTRAINT fk_decision_contexts_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_decision_contexts_environment_id_ai_state_snapshots FOREIGN KEY(environment_id, snapshot_id) REFERENCES ai_state_snapshots (environment_id, snapshot_id), 
    CONSTRAINT fk_decision_contexts_environment_id_scopes FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), 
    CONSTRAINT uq_decision_context_environment UNIQUE (environment_id, context_id), 
    CONSTRAINT ck_decision_contexts_decision_context_integrity CHECK (context_hash ~ '^[0-9a-f]{64}$' AND valid_until > created_at AND build_ms >= 0)
);

CREATE INDEX ix_decision_context_incident ON decision_contexts (environment_id, incident_id, created_at, context_id);

CREATE TRIGGER immutable_decision_contexts BEFORE UPDATE OR DELETE ON decision_contexts FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE FUNCTION zhiyu_m5_protect_context() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
IF EXISTS (SELECT 1 FROM decision_contexts WHERE context_id = OLD.context_id) THEN
RAISE EXCEPTION 'immutable managed model context';
END IF;
RETURN NEW;
END $$;

CREATE TRIGGER m5_context_contract BEFORE UPDATE OR DELETE ON context_bundles FOR EACH ROW EXECUTE FUNCTION zhiyu_m5_protect_context();

UPDATE alembic_version SET version_num='0011_ai_context' WHERE alembic_version.version_num = '0010_replan';

-- Running upgrade 0011_ai_context -> 0012_model_gateway

CREATE TABLE ai_incident_budgets (
    incident_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    configuration JSONB NOT NULL, 
    call_count INTEGER NOT NULL, 
    charged_tokens INTEGER NOT NULL, 
    input_tokens INTEGER NOT NULL, 
    output_tokens INTEGER NOT NULL, 
    ai_replans INTEGER NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_ai_incident_budgets PRIMARY KEY (incident_id), 
    CONSTRAINT fk_ai_incident_budgets_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT ck_ai_incident_budgets_ai_budget_nonnegative CHECK (call_count >= 0 AND charged_tokens >= 0 AND input_tokens >= 0 AND output_tokens >= 0 AND ai_replans >= 0)
);

CREATE TABLE model_requests (
    request_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    context_id TEXT NOT NULL, 
    task_type TEXT NOT NULL, 
    routing_version TEXT NOT NULL, 
    configuration_hash TEXT NOT NULL, 
    configuration JSONB NOT NULL, 
    input_body JSONB NOT NULL, 
    input_hash TEXT NOT NULL, 
    status TEXT NOT NULL, 
    worker_id TEXT, 
    reserved_tokens INTEGER NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    lease_until TIMESTAMP WITH TIME ZONE NOT NULL, 
    row_version INTEGER DEFAULT '1' NOT NULL, 
    CONSTRAINT pk_model_requests PRIMARY KEY (request_id), 
    CONSTRAINT fk_model_requests_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_model_requests_environment_id_decision_contexts FOREIGN KEY(environment_id, context_id) REFERENCES decision_contexts (environment_id, context_id), 
    CONSTRAINT uq_model_request_environment UNIQUE (environment_id, request_id), 
    CONSTRAINT ck_model_requests_model_request_state CHECK (task_type IN ('ANALYSIS','PLAN') AND status IN ('RUNNING','COMPLETED','FALLBACK')), 
    CONSTRAINT ck_model_requests_model_request_integrity CHECK (input_hash ~ '^[0-9a-f]{64}$' AND configuration_hash ~ '^[0-9a-f]{64}$' AND reserved_tokens >= 0 AND lease_until > started_at)
);

CREATE INDEX ix_model_request_incident ON model_requests (environment_id, incident_id, started_at, request_id);

CREATE TABLE model_receipts (
    request_id TEXT NOT NULL, 
    model_run_id TEXT, 
    status TEXT NOT NULL, 
    error_code TEXT, 
    output JSONB, 
    usage_known BOOLEAN NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    provider_ms FLOAT NOT NULL, 
    overhead_ms FLOAT NOT NULL, 
    schema_validation_ms FLOAT NOT NULL, 
    CONSTRAINT pk_model_receipts PRIMARY KEY (request_id), 
    CONSTRAINT fk_model_receipts_request_id_model_requests FOREIGN KEY(request_id) REFERENCES model_requests (request_id), 
    CONSTRAINT fk_model_receipts_model_run_id_model_runs FOREIGN KEY(model_run_id) REFERENCES model_runs (run_id), 
    CONSTRAINT uq_model_receipt_run UNIQUE (model_run_id), 
    CONSTRAINT ck_model_receipts_model_receipt_integrity CHECK (status IN ('COMPLETED','FALLBACK') AND provider_ms >= 0 AND overhead_ms >= 0 AND schema_validation_ms >= 0)
);

CREATE TRIGGER immutable_model_receipts BEFORE UPDATE OR DELETE ON model_receipts FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE FUNCTION zhiyu_m5_protect_model() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
IF TG_TABLE_NAME = 'model_runs' THEN
  IF EXISTS (SELECT 1 FROM model_receipts WHERE model_run_id = OLD.run_id) THEN
    RAISE EXCEPTION 'immutable managed ModelRun';
  END IF;
ELSIF TG_TABLE_NAME = 'model_requests' THEN
  IF TG_OP = 'DELETE' OR OLD.status <> 'RUNNING'
    OR NEW.input_hash IS DISTINCT FROM OLD.input_hash
    OR NEW.input_body IS DISTINCT FROM OLD.input_body
    OR NEW.configuration IS DISTINCT FROM OLD.configuration
    OR NEW.configuration_hash IS DISTINCT FROM OLD.configuration_hash
    OR NEW.context_id <> OLD.context_id OR NEW.request_id <> OLD.request_id
    OR NEW.environment_id <> OLD.environment_id OR NEW.incident_id <> OLD.incident_id
    OR NEW.task_type <> OLD.task_type OR NEW.routing_version <> OLD.routing_version
    OR NEW.started_at <> OLD.started_at OR NEW.lease_until <> OLD.lease_until
    OR NEW.reserved_tokens <> OLD.reserved_tokens THEN
    RAISE EXCEPTION 'immutable model request identity';
  END IF;
END IF;
RETURN NEW;
END $$;

CREATE TRIGGER m5_model_run_contract BEFORE UPDATE OR DELETE ON model_runs FOR EACH ROW EXECUTE FUNCTION zhiyu_m5_protect_model();

CREATE TRIGGER m5_model_request_identity BEFORE UPDATE OR DELETE ON model_requests FOR EACH ROW EXECUTE FUNCTION zhiyu_m5_protect_model();

UPDATE alembic_version SET version_num='0012_model_gateway' WHERE alembic_version.version_num = '0011_ai_context';

-- Running upgrade 0012_model_gateway -> 0013_situation_analysis

CREATE TABLE ai_situation_analyses (
    analysis_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    context_id TEXT NOT NULL, 
    request_id TEXT NOT NULL, 
    model_run_id TEXT, 
    state_entity_id TEXT, 
    status TEXT NOT NULL, 
    output JSONB, 
    grounding JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    grounding_ms FLOAT NOT NULL, 
    CONSTRAINT pk_ai_situation_analyses PRIMARY KEY (analysis_id), 
    CONSTRAINT fk_ai_situation_analyses_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_ai_situation_analyses_environment_id_decision_contexts FOREIGN KEY(environment_id, context_id) REFERENCES decision_contexts (environment_id, context_id), 
    CONSTRAINT fk_ai_situation_analyses_environment_id_model_requests FOREIGN KEY(environment_id, request_id) REFERENCES model_requests (environment_id, request_id), 
    CONSTRAINT fk_ai_situation_analyses_model_run_id_model_runs FOREIGN KEY(model_run_id) REFERENCES model_runs (run_id), 
    CONSTRAINT fk_ai_situation_analyses_environment_id_state_entities FOREIGN KEY(environment_id, state_entity_id) REFERENCES state_entities (environment_id, entity_id), 
    CONSTRAINT uq_analysis_model_request UNIQUE (request_id), 
    CONSTRAINT uq_analysis_environment UNIQUE (environment_id, analysis_id), 
    CONSTRAINT ck_ai_situation_analyses_analysis_status CHECK (status IN ('REFERENCE_GROUNDED','REJECTED','FALLBACK') AND grounding_ms >= 0)
);

CREATE INDEX ix_analysis_incident ON ai_situation_analyses (environment_id, incident_id, created_at, analysis_id);

CREATE TRIGGER immutable_ai_analysis BEFORE UPDATE OR DELETE ON ai_situation_analyses FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE FUNCTION zhiyu_protect_model_state() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
IF EXISTS (SELECT 1 FROM ai_situation_analyses WHERE state_entity_id = OLD.entity_id AND environment_id = OLD.environment_id) THEN
RAISE EXCEPTION 'immutable model inference'; END IF;
IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
RETURN NEW; END $$;

CREATE TRIGGER m5_model_state BEFORE UPDATE OR DELETE ON state_entities FOR EACH ROW EXECUTE FUNCTION zhiyu_protect_model_state();

UPDATE alembic_version SET version_num='0013_situation_analysis' WHERE alembic_version.version_num = '0012_model_gateway';

-- Running upgrade 0013_situation_analysis -> 0014_ai_proposals

CREATE TABLE ai_plan_proposals (
    proposal_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    incident_version INTEGER NOT NULL, 
    context_id TEXT NOT NULL, 
    analysis_id TEXT NOT NULL, 
    request_id TEXT NOT NULL, 
    model_run_id TEXT, 
    parent_verification_id TEXT, 
    plan_id TEXT, 
    mode TEXT NOT NULL, 
    status TEXT NOT NULL, 
    output JSONB, 
    validation JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    planning_ms FLOAT NOT NULL, 
    CONSTRAINT pk_ai_plan_proposals PRIMARY KEY (proposal_id), 
    CONSTRAINT fk_ai_plan_proposals_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_ai_plan_proposals_environment_id_decision_contexts FOREIGN KEY(environment_id, context_id) REFERENCES decision_contexts (environment_id, context_id), 
    CONSTRAINT fk_ai_plan_proposals_environment_id_ai_situation_analyses FOREIGN KEY(environment_id, analysis_id) REFERENCES ai_situation_analyses (environment_id, analysis_id), 
    CONSTRAINT fk_ai_plan_proposals_environment_id_model_requests FOREIGN KEY(environment_id, request_id) REFERENCES model_requests (environment_id, request_id), 
    CONSTRAINT fk_ai_plan_proposals_model_run_id_model_runs FOREIGN KEY(model_run_id) REFERENCES model_runs (run_id), 
    CONSTRAINT fk_ai_plan_proposals_parent_verification_id_verificatio_5eb3 FOREIGN KEY(parent_verification_id) REFERENCES verification_results (verification_id), 
    CONSTRAINT fk_ai_plan_proposals_environment_id_plans FOREIGN KEY(environment_id, plan_id) REFERENCES plans (environment_id, plan_id), 
    CONSTRAINT uq_ai_proposal_request UNIQUE (request_id), 
    CONSTRAINT ck_ai_plan_proposals_proposal_status CHECK (status IN ('ACCEPTED','SHADOW','REJECTED','FALLBACK') AND mode IN ('SHADOW','ASSISTED') AND planning_ms >= 0 AND incident_version >= 1), 
    CONSTRAINT ck_ai_plan_proposals_proposal_accepted_plan CHECK ((status = 'ACCEPTED') = (plan_id IS NOT NULL))
);

CREATE INDEX ix_ai_proposals_incident ON ai_plan_proposals (environment_id, incident_id, created_at, proposal_id);

CREATE UNIQUE INDEX uq_ai_accepted_lineage ON ai_plan_proposals (environment_id, incident_id, incident_version) WHERE plan_id IS NOT NULL;

CREATE TRIGGER immutable_ai_proposals BEFORE UPDATE OR DELETE ON ai_plan_proposals FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

CREATE FUNCTION zhiyu_protect_ai_plan() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
IF EXISTS (SELECT 1 FROM ai_plan_proposals WHERE plan_id = OLD.plan_id) THEN RAISE EXCEPTION 'immutable accepted AI plan'; END IF;
IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END $$;

CREATE TRIGGER m5_ai_plan BEFORE UPDATE OR DELETE ON plans FOR EACH ROW EXECUTE FUNCTION zhiyu_protect_ai_plan();

UPDATE alembic_version SET version_num='0014_ai_proposals' WHERE alembic_version.version_num = '0013_situation_analysis';

-- Running upgrade 0014_ai_proposals -> 0015_ai_decisions

CREATE TABLE ai_decisions (
    context_id TEXT NOT NULL, 
    environment_id TEXT NOT NULL, 
    incident_id TEXT NOT NULL, 
    status TEXT NOT NULL, 
    plan_id TEXT, 
    receipt JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    decision_ms FLOAT NOT NULL, 
    fallback_ms FLOAT NOT NULL, 
    CONSTRAINT pk_ai_decisions PRIMARY KEY (context_id), 
    CONSTRAINT fk_ai_decisions_environment_id_decision_contexts FOREIGN KEY(environment_id, context_id) REFERENCES decision_contexts (environment_id, context_id), 
    CONSTRAINT fk_ai_decisions_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), 
    CONSTRAINT fk_ai_decisions_environment_id_plans FOREIGN KEY(environment_id, plan_id) REFERENCES plans (environment_id, plan_id), 
    CONSTRAINT ck_ai_decisions_ai_decision_status CHECK (status IN ('AI_ASSISTED','DETERMINISTIC_FALLBACK','SHADOW','REJECTED') AND decision_ms >= 0 AND fallback_ms >= 0)
);

CREATE TRIGGER immutable_ai_decisions BEFORE UPDATE OR DELETE ON ai_decisions FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation();

UPDATE alembic_version SET version_num='0015_ai_decisions' WHERE alembic_version.version_num = '0014_ai_proposals';

-- Running upgrade 0015_ai_decisions -> 0016_lab_remediation

ALTER TABLE action_execution_results DROP CONSTRAINT ck_action_execution_results_action_result_read_only;

ALTER TABLE action_execution_results ADD CONSTRAINT ck_action_execution_results_action_result_read_only CHECK (side_effect IN ('NONE','LAB_PATH') AND completed_at >= started_at AND executor_ms >= 0);

UPDATE alembic_version SET version_num='0016_lab_remediation' WHERE alembic_version.version_num = '0015_ai_decisions';

COMMIT;

