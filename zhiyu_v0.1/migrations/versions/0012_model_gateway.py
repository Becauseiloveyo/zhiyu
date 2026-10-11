"""Durable bounded model requests and terminal ModelRun receipts."""

from alembic import op

revision = "0012_model_gateway"
down_revision = "0011_ai_context"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE ai_incident_budgets (\n\tincident_id TEXT NOT NULL, \n\tenvironment_id TEXT NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tcall_count INTEGER NOT NULL, \n\tcharged_tokens INTEGER NOT NULL, \n\tinput_tokens INTEGER NOT NULL, \n\toutput_tokens INTEGER NOT NULL, \n\tai_replans INTEGER NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trow_version INTEGER DEFAULT '1' NOT NULL, \n\tCONSTRAINT pk_ai_incident_budgets PRIMARY KEY (incident_id), \n\tCONSTRAINT fk_ai_incident_budgets_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), \n\tCONSTRAINT ck_ai_incident_budgets_ai_budget_nonnegative CHECK (call_count >= 0 AND charged_tokens >= 0 AND input_tokens >= 0 AND output_tokens >= 0 AND ai_replans >= 0)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE model_requests (\n\trequest_id TEXT NOT NULL, \n\tenvironment_id TEXT NOT NULL, \n\tincident_id TEXT NOT NULL, \n\tcontext_id TEXT NOT NULL, \n\ttask_type TEXT NOT NULL, \n\trouting_version TEXT NOT NULL, \n\tconfiguration_hash TEXT NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tinput_body JSONB NOT NULL, \n\tinput_hash TEXT NOT NULL, \n\tstatus TEXT NOT NULL, \n\tworker_id TEXT, \n\treserved_tokens INTEGER NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tlease_until TIMESTAMP WITH TIME ZONE NOT NULL, \n\trow_version INTEGER DEFAULT '1' NOT NULL, \n\tCONSTRAINT pk_model_requests PRIMARY KEY (request_id), \n\tCONSTRAINT fk_model_requests_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), \n\tCONSTRAINT fk_model_requests_environment_id_decision_contexts FOREIGN KEY(environment_id, context_id) REFERENCES decision_contexts (environment_id, context_id), \n\tCONSTRAINT uq_model_request_environment UNIQUE (environment_id, request_id), \n\tCONSTRAINT ck_model_requests_model_request_state CHECK (task_type IN ('ANALYSIS','PLAN') AND status IN ('RUNNING','COMPLETED','FALLBACK')), \n\tCONSTRAINT ck_model_requests_model_request_integrity CHECK (input_hash ~ '^[0-9a-f]{64}$' AND configuration_hash ~ '^[0-9a-f]{64}$' AND reserved_tokens >= 0 AND lease_until > started_at)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_model_request_incident ON model_requests (environment_id, incident_id, started_at, request_id)"
    )
    op.execute(
        "\nCREATE TABLE model_receipts (\n\trequest_id TEXT NOT NULL, \n\tmodel_run_id TEXT, \n\tstatus TEXT NOT NULL, \n\terror_code TEXT, \n\toutput JSONB, \n\tusage_known BOOLEAN NOT NULL, \n\tcompleted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tprovider_ms FLOAT NOT NULL, \n\toverhead_ms FLOAT NOT NULL, \n\tschema_validation_ms FLOAT NOT NULL, \n\tCONSTRAINT pk_model_receipts PRIMARY KEY (request_id), \n\tCONSTRAINT fk_model_receipts_request_id_model_requests FOREIGN KEY(request_id) REFERENCES model_requests (request_id), \n\tCONSTRAINT fk_model_receipts_model_run_id_model_runs FOREIGN KEY(model_run_id) REFERENCES model_runs (run_id), \n\tCONSTRAINT uq_model_receipt_run UNIQUE (model_run_id), \n\tCONSTRAINT ck_model_receipts_model_receipt_integrity CHECK (status IN ('COMPLETED','FALLBACK') AND provider_ms >= 0 AND overhead_ms >= 0 AND schema_validation_ms >= 0)\n)\n\n"
    )
    op.execute(
        "CREATE TRIGGER immutable_model_receipts BEFORE UPDATE OR DELETE ON model_receipts FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute("""CREATE FUNCTION zhiyu_m5_protect_model() RETURNS trigger LANGUAGE plpgsql AS $$
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
END $$""")
    op.execute(
        "CREATE TRIGGER m5_model_run_contract BEFORE UPDATE OR DELETE ON model_runs FOR EACH ROW EXECUTE FUNCTION zhiyu_m5_protect_model()"
    )
    op.execute(
        "CREATE TRIGGER m5_model_request_identity BEFORE UPDATE OR DELETE ON model_requests FOR EACH ROW EXECUTE FUNCTION zhiyu_m5_protect_model()"
    )


def downgrade():
    op.execute("DROP TRIGGER m5_model_run_contract ON model_runs")
    op.execute("DROP TRIGGER m5_model_request_identity ON model_requests")
    op.execute("DROP FUNCTION zhiyu_m5_protect_model()")
    op.drop_table("model_receipts")
    op.drop_table("model_requests")
    op.drop_table("ai_incident_budgets")
