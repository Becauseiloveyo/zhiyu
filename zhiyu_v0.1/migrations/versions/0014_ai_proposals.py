"""Immutable AI proposal decisions and accepted lineage."""

from alembic import op

revision = "0014_ai_proposals"
down_revision = "0013_situation_analysis"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE ai_plan_proposals (\n\tproposal_id TEXT NOT NULL, \n\tenvironment_id TEXT NOT NULL, \n\tincident_id TEXT NOT NULL, \n\tincident_version INTEGER NOT NULL, \n\tcontext_id TEXT NOT NULL, \n\tanalysis_id TEXT NOT NULL, \n\trequest_id TEXT NOT NULL, \n\tmodel_run_id TEXT, \n\tparent_verification_id TEXT, \n\tplan_id TEXT, \n\tmode TEXT NOT NULL, \n\tstatus TEXT NOT NULL, \n\toutput JSONB, \n\tvalidation JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tplanning_ms FLOAT NOT NULL, \n\tCONSTRAINT pk_ai_plan_proposals PRIMARY KEY (proposal_id), \n\tCONSTRAINT fk_ai_plan_proposals_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), \n\tCONSTRAINT fk_ai_plan_proposals_environment_id_decision_contexts FOREIGN KEY(environment_id, context_id) REFERENCES decision_contexts (environment_id, context_id), \n\tCONSTRAINT fk_ai_plan_proposals_environment_id_ai_situation_analyses FOREIGN KEY(environment_id, analysis_id) REFERENCES ai_situation_analyses (environment_id, analysis_id), \n\tCONSTRAINT fk_ai_plan_proposals_environment_id_model_requests FOREIGN KEY(environment_id, request_id) REFERENCES model_requests (environment_id, request_id), \n\tCONSTRAINT fk_ai_plan_proposals_model_run_id_model_runs FOREIGN KEY(model_run_id) REFERENCES model_runs (run_id), \n\tCONSTRAINT fk_ai_plan_proposals_parent_verification_id_verificatio_5eb3 FOREIGN KEY(parent_verification_id) REFERENCES verification_results (verification_id), \n\tCONSTRAINT fk_ai_plan_proposals_environment_id_plans FOREIGN KEY(environment_id, plan_id) REFERENCES plans (environment_id, plan_id), \n\tCONSTRAINT uq_ai_proposal_request UNIQUE (request_id), \n\tCONSTRAINT ck_ai_plan_proposals_proposal_status CHECK (status IN ('ACCEPTED','SHADOW','REJECTED','FALLBACK') AND mode IN ('SHADOW','ASSISTED') AND planning_ms >= 0 AND incident_version >= 1), \n\tCONSTRAINT ck_ai_plan_proposals_proposal_accepted_plan CHECK ((status = 'ACCEPTED') = (plan_id IS NOT NULL))\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_ai_proposals_incident ON ai_plan_proposals (environment_id, incident_id, created_at, proposal_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_ai_accepted_lineage ON ai_plan_proposals (environment_id, incident_id, incident_version) WHERE plan_id IS NOT NULL"
    )
    op.execute(
        "CREATE TRIGGER immutable_ai_proposals BEFORE UPDATE OR DELETE ON ai_plan_proposals FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute("""CREATE FUNCTION zhiyu_protect_ai_plan() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
IF EXISTS (SELECT 1 FROM ai_plan_proposals WHERE plan_id = OLD.plan_id) THEN RAISE EXCEPTION 'immutable accepted AI plan'; END IF;
IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END $$""")
    op.execute(
        "CREATE TRIGGER m5_ai_plan BEFORE UPDATE OR DELETE ON plans FOR EACH ROW EXECUTE FUNCTION zhiyu_protect_ai_plan()"
    )


def downgrade():
    op.execute("DROP TRIGGER m5_ai_plan ON plans")
    op.execute("DROP FUNCTION zhiyu_protect_ai_plan()")
    op.drop_table("ai_plan_proposals")
