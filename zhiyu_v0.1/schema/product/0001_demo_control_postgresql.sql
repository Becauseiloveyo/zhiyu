-- Product-only schema; explicit migration: tools/m9_product_migrate.py
CREATE TABLE zhiyu_product.demo_runs (
	run_id TEXT NOT NULL, 
	environment_id TEXT NOT NULL, 
	scope_id TEXT NOT NULL, 
	scenario_id TEXT NOT NULL, 
	template_sha256 TEXT NOT NULL, 
	profile_id TEXT NOT NULL, 
	actor_id TEXT NOT NULL, 
	idempotency_key TEXT NOT NULL, 
	request_sha256 TEXT NOT NULL, 
	predecessor_id TEXT, 
	run_mode TEXT NOT NULL, 
	model_source TEXT NOT NULL, 
	status TEXT NOT NULL, 
	cleanup_status TEXT NOT NULL, 
	cancel_requested BOOLEAN NOT NULL, 
	version INTEGER NOT NULL, 
	step_index INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	deadline TIMESTAMP WITH TIME ZONE NOT NULL, 
	lease_owner TEXT, 
	lease_until TIMESTAMP WITH TIME ZONE, 
	error_code TEXT, 
	actual_outcome TEXT NOT NULL, 
	CONSTRAINT pk_demo_runs PRIMARY KEY (run_id), 
	CONSTRAINT fk_demo_runs_predecessor_id_demo_runs FOREIGN KEY(predecessor_id) REFERENCES zhiyu_product.demo_runs (run_id), 
	CONSTRAINT uq_demo_request UNIQUE (environment_id, actor_id, idempotency_key), 
	CONSTRAINT ck_demo_runs_scenario CHECK (scenario_id IN ('A','B','C','D','E')), 
	CONSTRAINT ck_demo_runs_digests CHECK (template_sha256 ~ '^[a-f0-9]{64}$' AND request_sha256 ~ '^[a-f0-9]{64}$'), 
	CONSTRAINT ck_demo_runs_mode CHECK (run_mode = 'LIVE'), 
	CONSTRAINT ck_demo_runs_model_source CHECK (model_source IN ('NONE','REAL_LOCAL_MODEL','SCRIPTED_NOT_AI')), 
	CONSTRAINT ck_demo_runs_status CHECK (status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED','NEEDS_RECONCILIATION')), 
	CONSTRAINT ck_demo_runs_cleanup_status CHECK (cleanup_status IN ('NOT_STARTED','QUEUED','RUNNING','CLEAN','NEEDS_MANUAL')), 
	CONSTRAINT ck_demo_runs_checkpoint CHECK (version >= 1 AND step_index BETWEEN 0 AND 4), 
	CONSTRAINT ck_demo_runs_deadline CHECK (deadline > created_at), 
	CONSTRAINT ck_demo_runs_lease_pair CHECK ((lease_owner IS NULL) = (lease_until IS NULL)), 
	CONSTRAINT ck_demo_runs_outcome CHECK (actual_outcome IN ('UNKNOWN','PASS','FAIL','INCONCLUSIVE','REJECTED','FALLBACK')), 
	CONSTRAINT ck_demo_runs_idempotency_key CHECK (length(idempotency_key) BETWEEN 16 AND 80)
);

CREATE TABLE zhiyu_product.demo_run_steps (
	run_id TEXT NOT NULL, 
	position INTEGER NOT NULL, 
	operation TEXT NOT NULL, 
	status TEXT NOT NULL, 
	generation INTEGER NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	output JSONB NOT NULL, 
	CONSTRAINT pk_demo_run_steps PRIMARY KEY (run_id, position), 
	CONSTRAINT fk_demo_run_steps_run_id_demo_runs FOREIGN KEY(run_id) REFERENCES zhiyu_product.demo_runs (run_id), 
	CONSTRAINT ck_demo_run_steps_position CHECK (position BETWEEN 0 AND 3 OR position = 100), 
	CONSTRAINT ck_demo_run_steps_operation CHECK (operation IN ('PREFLIGHT','TRIGGER','VERIFY','ARCHIVE','CLEANUP')), 
	CONSTRAINT ck_demo_run_steps_status CHECK (status IN ('STARTED','COMPLETED','FAILED','UNKNOWN')), 
	CONSTRAINT ck_demo_run_steps_generation CHECK (generation > 0), 
	CONSTRAINT ck_demo_run_steps_bounded_output CHECK (jsonb_typeof(output) = 'object' AND octet_length(output::text) <= 16384)
);

CREATE INDEX ix_demo_queue ON zhiyu_product.demo_runs (status, created_at);

CREATE INDEX ix_demo_scope ON zhiyu_product.demo_runs (environment_id, scope_id, created_at);
