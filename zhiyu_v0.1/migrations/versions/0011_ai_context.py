"""Bounded immutable context and state snapshots; unchanged ai.5 contracts."""

from alembic import op

revision = "0011_ai_context"
down_revision = "0010_replan"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE ai_state_snapshots (\n\tsnapshot_id TEXT NOT NULL, \n\tenvironment_id TEXT NOT NULL, \n\tincident_id TEXT NOT NULL, \n\tincident_version INTEGER NOT NULL, \n\tbody JSONB NOT NULL, \n\tbody_hash TEXT NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tvalid_until TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_ai_state_snapshots PRIMARY KEY (snapshot_id), \n\tCONSTRAINT fk_ai_state_snapshots_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), \n\tCONSTRAINT uq_ai_state_environment UNIQUE (environment_id, snapshot_id), \n\tCONSTRAINT ck_ai_state_snapshots_ai_state_integrity CHECK (body_hash ~ '^[0-9a-f]{64}$' AND incident_version >= 1 AND valid_until > created_at)\n)\n\n"
    )
    op.execute(
        "CREATE TRIGGER immutable_ai_state_snapshots BEFORE UPDATE OR DELETE ON ai_state_snapshots FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute(
        "\nCREATE TABLE decision_contexts (\n\tcontext_id TEXT NOT NULL, \n\tenvironment_id TEXT NOT NULL, \n\tincident_id TEXT NOT NULL, \n\tsnapshot_id TEXT NOT NULL, \n\tscope_id TEXT NOT NULL, \n\tbody JSONB NOT NULL, \n\tmanifest JSONB NOT NULL, \n\tcontext_hash TEXT NOT NULL, \n\tpolicy JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tvalid_until TIMESTAMP WITH TIME ZONE NOT NULL, \n\tbuild_ms FLOAT NOT NULL, \n\tCONSTRAINT pk_decision_contexts PRIMARY KEY (context_id), \n\tCONSTRAINT fk_decision_contexts_context_id_context_bundles FOREIGN KEY(context_id) REFERENCES context_bundles (context_id), \n\tCONSTRAINT fk_decision_contexts_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), \n\tCONSTRAINT fk_decision_contexts_environment_id_ai_state_snapshots FOREIGN KEY(environment_id, snapshot_id) REFERENCES ai_state_snapshots (environment_id, snapshot_id), \n\tCONSTRAINT fk_decision_contexts_environment_id_scopes FOREIGN KEY(environment_id, scope_id) REFERENCES scopes (environment_id, scope_id), \n\tCONSTRAINT uq_decision_context_environment UNIQUE (environment_id, context_id), \n\tCONSTRAINT ck_decision_contexts_decision_context_integrity CHECK (context_hash ~ '^[0-9a-f]{64}$' AND valid_until > created_at AND build_ms >= 0)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_decision_context_incident ON decision_contexts (environment_id, incident_id, created_at, context_id)"
    )
    op.execute(
        "CREATE TRIGGER immutable_decision_contexts BEFORE UPDATE OR DELETE ON decision_contexts FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute("""CREATE FUNCTION zhiyu_m5_protect_context() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
IF EXISTS (SELECT 1 FROM decision_contexts WHERE context_id = OLD.context_id) THEN
RAISE EXCEPTION 'immutable managed model context';
END IF;
RETURN NEW;
END $$""")
    op.execute(
        "CREATE TRIGGER m5_context_contract BEFORE UPDATE OR DELETE ON context_bundles FOR EACH ROW EXECUTE FUNCTION zhiyu_m5_protect_context()"
    )


def downgrade():
    op.execute("DROP TRIGGER m5_context_contract ON context_bundles")
    op.execute("DROP FUNCTION zhiyu_m5_protect_context()")
    op.drop_table("decision_contexts")
    op.drop_table("ai_state_snapshots")
