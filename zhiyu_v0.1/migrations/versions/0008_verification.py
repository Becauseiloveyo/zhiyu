"""Independent verification bindings and fenced observations."""

from alembic import op

revision = "0008_verification"
down_revision = "0007_execution"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE verification_runtime (\n\tspec_id TEXT NOT NULL, \n\tenvironment_id TEXT NOT NULL, \n\tincident_id TEXT NOT NULL, \n\tplan_id TEXT NOT NULL, \n\ttask_id TEXT NOT NULL, \n\taction_id TEXT NOT NULL, \n\taction_result_id TEXT NOT NULL, \n\tscope_id TEXT NOT NULL, \n\trun_id TEXT NOT NULL, \n\tpolicy JSONB NOT NULL, \n\tbinding JSONB NOT NULL, \n\tspec_hash TEXT NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tvalid_until TIMESTAMP WITH TIME ZONE NOT NULL, \n\tgeneration_ms FLOAT NOT NULL, \n\tCONSTRAINT pk_verification_runtime PRIMARY KEY (spec_id), \n\tCONSTRAINT fk_verification_runtime_spec_id_verification_specs FOREIGN KEY(spec_id) REFERENCES verification_specs (verification_spec_id), \n\tCONSTRAINT fk_verification_runtime_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), \n\tCONSTRAINT fk_verification_runtime_environment_id_task_runtime FOREIGN KEY(environment_id, plan_id, task_id) REFERENCES task_runtime (environment_id, plan_id, task_id), \n\tCONSTRAINT fk_verification_runtime_environment_id_action_requests FOREIGN KEY(environment_id, action_id) REFERENCES action_requests (environment_id, action_id), \n\tCONSTRAINT fk_verification_runtime_action_result_id_action_executi_cdac FOREIGN KEY(action_result_id) REFERENCES action_execution_results (attempt_id), \n\tCONSTRAINT fk_verification_runtime_environment_id_scopes FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), \n\tCONSTRAINT fk_verification_runtime_environment_id_validation_runs FOREIGN KEY(environment_id, run_id) REFERENCES validation_runs (environment_id, run_id), \n\tCONSTRAINT uq_verification_runtime_env UNIQUE (environment_id, spec_id), \n\tCONSTRAINT ck_verification_runtime_verification_runtime_interval CHECK (valid_until > created_at AND generation_ms >= 0)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE verification_checks (\n\tspec_id TEXT NOT NULL, \n\tcheck_id TEXT NOT NULL, \n\tenvironment_id TEXT NOT NULL, \n\tdefinition JSONB NOT NULL, \n\tstatus TEXT NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tworker_id TEXT, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\tstarted_at TIMESTAMP WITH TIME ZONE, \n\trow_version INTEGER DEFAULT '1' NOT NULL, \n\tCONSTRAINT pk_verification_checks PRIMARY KEY (spec_id, check_id), \n\tCONSTRAINT fk_verification_checks_environment_id_verification_runtime FOREIGN KEY(environment_id, spec_id) REFERENCES verification_runtime (environment_id, spec_id), \n\tCONSTRAINT ck_verification_checks_verification_check_status CHECK (status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','TIMEOUT','INCONCLUSIVE','CANCELLED')), \n\tCONSTRAINT ck_verification_checks_verification_check_generation CHECK (generation >= 0 AND row_version >= 1), \n\tCONSTRAINT ck_verification_checks_verification_check_lease CHECK ((status = 'RUNNING') = (worker_id IS NOT NULL AND lease_until IS NOT NULL))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE verification_observations (\n\tspec_id TEXT NOT NULL, \n\tcheck_id TEXT NOT NULL, \n\tevidence_id TEXT NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\texecution_status TEXT NOT NULL, \n\tassertion_status TEXT NOT NULL, \n\tsamples JSONB NOT NULL, \n\tassertions JSONB NOT NULL, \n\treason TEXT NOT NULL, \n\texecutor_version TEXT NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tchecked_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tlatency_ms FLOAT NOT NULL, \n\tCONSTRAINT pk_verification_observations PRIMARY KEY (spec_id, check_id), \n\tCONSTRAINT fk_verification_observations_spec_id_verification_checks FOREIGN KEY(spec_id, check_id) REFERENCES verification_checks (spec_id, check_id), \n\tCONSTRAINT fk_verification_observations_evidence_id_evidence FOREIGN KEY(evidence_id) REFERENCES evidence (evidence_id), \n\tCONSTRAINT uq_verification_observation_evidence UNIQUE (evidence_id), \n\tCONSTRAINT ck_verification_observations_verification_assertion_status CHECK (assertion_status IN ('PASS','FAIL','INCONCLUSIVE')), \n\tCONSTRAINT ck_verification_observations_verification_observation_interval CHECK (checked_at >= started_at AND generation >= 1 AND latency_ms >= 0)\n)\n\n"
    )
    op.execute(
        "CREATE TRIGGER immutable_verification_runtime BEFORE UPDATE OR DELETE ON verification_runtime FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute(
        "CREATE TRIGGER immutable_verification_observations BEFORE UPDATE OR DELETE ON verification_observations FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )


def downgrade():
    op.drop_table("verification_observations")
    op.drop_table("verification_checks")
    op.drop_table("verification_runtime")
