"""Immutable AI/deterministic decision receipt."""

from alembic import op

revision = "0015_ai_decisions"
down_revision = "0014_ai_proposals"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE ai_decisions (\n\tcontext_id TEXT NOT NULL, \n\tenvironment_id TEXT NOT NULL, \n\tincident_id TEXT NOT NULL, \n\tstatus TEXT NOT NULL, \n\tplan_id TEXT, \n\treceipt JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdecision_ms FLOAT NOT NULL, \n\tfallback_ms FLOAT NOT NULL, \n\tCONSTRAINT pk_ai_decisions PRIMARY KEY (context_id), \n\tCONSTRAINT fk_ai_decisions_environment_id_decision_contexts FOREIGN KEY(environment_id, context_id) REFERENCES decision_contexts (environment_id, context_id), \n\tCONSTRAINT fk_ai_decisions_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), \n\tCONSTRAINT fk_ai_decisions_environment_id_plans FOREIGN KEY(environment_id, plan_id) REFERENCES plans (environment_id, plan_id), \n\tCONSTRAINT ck_ai_decisions_ai_decision_status CHECK (status IN ('AI_ASSISTED','DETERMINISTIC_FALLBACK','SHADOW','REJECTED') AND decision_ms >= 0 AND fallback_ms >= 0)\n)\n\n"
    )
    op.execute(
        "CREATE TRIGGER immutable_ai_decisions BEFORE UPDATE OR DELETE ON ai_decisions FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )


def downgrade():
    op.drop_table("ai_decisions")
