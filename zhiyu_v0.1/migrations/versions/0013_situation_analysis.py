"""Immutable grounded analysis and model-inference provenance."""

from alembic import op

revision = "0013_situation_analysis"
down_revision = "0012_model_gateway"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE ai_situation_analyses (\n\tanalysis_id TEXT NOT NULL, \n\tenvironment_id TEXT NOT NULL, \n\tincident_id TEXT NOT NULL, \n\tcontext_id TEXT NOT NULL, \n\trequest_id TEXT NOT NULL, \n\tmodel_run_id TEXT, \n\tstate_entity_id TEXT, \n\tstatus TEXT NOT NULL, \n\toutput JSONB, \n\tgrounding JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tgrounding_ms FLOAT NOT NULL, \n\tCONSTRAINT pk_ai_situation_analyses PRIMARY KEY (analysis_id), \n\tCONSTRAINT fk_ai_situation_analyses_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), \n\tCONSTRAINT fk_ai_situation_analyses_environment_id_decision_contexts FOREIGN KEY(environment_id, context_id) REFERENCES decision_contexts (environment_id, context_id), \n\tCONSTRAINT fk_ai_situation_analyses_environment_id_model_requests FOREIGN KEY(environment_id, request_id) REFERENCES model_requests (environment_id, request_id), \n\tCONSTRAINT fk_ai_situation_analyses_model_run_id_model_runs FOREIGN KEY(model_run_id) REFERENCES model_runs (run_id), \n\tCONSTRAINT fk_ai_situation_analyses_environment_id_state_entities FOREIGN KEY(environment_id, state_entity_id) REFERENCES state_entities (environment_id, entity_id), \n\tCONSTRAINT uq_analysis_model_request UNIQUE (request_id), \n\tCONSTRAINT uq_analysis_environment UNIQUE (environment_id, analysis_id), \n\tCONSTRAINT ck_ai_situation_analyses_analysis_status CHECK (status IN ('REFERENCE_GROUNDED','REJECTED','FALLBACK') AND grounding_ms >= 0)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_analysis_incident ON ai_situation_analyses (environment_id, incident_id, created_at, analysis_id)"
    )
    op.execute(
        "CREATE TRIGGER immutable_ai_analysis BEFORE UPDATE OR DELETE ON ai_situation_analyses FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute("""CREATE FUNCTION zhiyu_protect_model_state() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
IF EXISTS (SELECT 1 FROM ai_situation_analyses WHERE state_entity_id = OLD.entity_id AND environment_id = OLD.environment_id) THEN
RAISE EXCEPTION 'immutable model inference'; END IF;
IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
RETURN NEW; END $$""")
    op.execute(
        "CREATE TRIGGER m5_model_state BEFORE UPDATE OR DELETE ON state_entities FOR EACH ROW EXECUTE FUNCTION zhiyu_protect_model_state()"
    )


def downgrade():
    op.execute("DROP TRIGGER m5_model_state ON state_entities")
    op.execute("DROP FUNCTION zhiyu_protect_model_state()")
    op.drop_table("ai_situation_analyses")
