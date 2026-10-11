"""Opt-in response cycle, bounded replan and state history."""

from alembic import op

revision = "0010_replan"
down_revision = "0009_decisions"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE response_cycles (\n\tplan_id TEXT NOT NULL, \n\tenvironment_id TEXT NOT NULL, \n\tincident_id TEXT NOT NULL, \n\texpected_version INTEGER NOT NULL, \n\tsemantic_hash TEXT NOT NULL, \n\troot_plan_id TEXT NOT NULL, \n\tparent_plan_id TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trow_version INTEGER DEFAULT '1' NOT NULL, \n\tCONSTRAINT pk_response_cycles PRIMARY KEY (plan_id), \n\tCONSTRAINT fk_response_cycles_environment_id_plans FOREIGN KEY(environment_id, plan_id) REFERENCES plans (environment_id, plan_id), \n\tCONSTRAINT fk_response_cycles_environment_id_incidents FOREIGN KEY(environment_id, incident_id) REFERENCES incidents (environment_id, incident_id), \n\tCONSTRAINT fk_response_cycles_root_plan_id_plans FOREIGN KEY(root_plan_id) REFERENCES plans (plan_id), \n\tCONSTRAINT fk_response_cycles_parent_plan_id_plans FOREIGN KEY(parent_plan_id) REFERENCES plans (plan_id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE replan_budgets (\n\troot_plan_id TEXT NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tcurrent_replan_count INTEGER NOT NULL, \n\treserved_actions INTEGER NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trow_version INTEGER DEFAULT '1' NOT NULL, \n\tCONSTRAINT pk_replan_budgets PRIMARY KEY (root_plan_id), \n\tCONSTRAINT fk_replan_budgets_root_plan_id_plans FOREIGN KEY(root_plan_id) REFERENCES plans (plan_id), \n\tCONSTRAINT ck_replan_budgets_replan_budget_counts CHECK (current_replan_count >= 0 AND reserved_actions >= 0)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE replan_decisions (\n\tverification_id TEXT NOT NULL, \n\troot_plan_id TEXT NOT NULL, \n\tparent_plan_id TEXT NOT NULL, \n\tnew_plan_id TEXT, \n\tstatus TEXT NOT NULL, \n\treason TEXT NOT NULL, \n\treplan_count INTEGER NOT NULL, \n\tpolicy_version TEXT NOT NULL, \n\tplan_fingerprint TEXT NOT NULL, \n\taction_fingerprint TEXT NOT NULL, \n\tevidence_fingerprint TEXT NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tlatency_ms FLOAT NOT NULL, \n\tCONSTRAINT pk_replan_decisions PRIMARY KEY (verification_id), \n\tCONSTRAINT fk_replan_decisions_verification_id_verification_results FOREIGN KEY(verification_id) REFERENCES verification_results (verification_id), \n\tCONSTRAINT fk_replan_decisions_root_plan_id_plans FOREIGN KEY(root_plan_id) REFERENCES plans (plan_id), \n\tCONSTRAINT fk_replan_decisions_parent_plan_id_plans FOREIGN KEY(parent_plan_id) REFERENCES plans (plan_id), \n\tCONSTRAINT fk_replan_decisions_new_plan_id_plans FOREIGN KEY(new_plan_id) REFERENCES plans (plan_id), \n\tCONSTRAINT uq_replan_new_plan UNIQUE (new_plan_id), \n\tCONSTRAINT ck_replan_decisions_replan_status CHECK (status IN ('NO_REPLAN','CREATED','REPLAN_EXHAUSTED','REQUIRE_APPROVAL','BLOCKED'))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE verification_state_updates (\n\tverification_id TEXT NOT NULL, \n\tentity_ids JSONB NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tlatency_ms FLOAT NOT NULL, \n\tCONSTRAINT pk_verification_state_updates PRIMARY KEY (verification_id), \n\tCONSTRAINT fk_verification_state_updates_verification_id_verificat_c53d FOREIGN KEY(verification_id) REFERENCES verification_results (verification_id)\n)\n\n"
    )
    op.execute(
        "CREATE TRIGGER immutable_replan_decisions BEFORE UPDATE OR DELETE ON replan_decisions FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )
    op.execute(
        "CREATE TRIGGER immutable_verification_state_updates BEFORE UPDATE OR DELETE ON verification_state_updates FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )

    op.execute("""CREATE FUNCTION zhiyu_m4_protect_contract() RETURNS trigger LANGUAGE plpgsql AS $$
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
END $$""")
    op.execute(
        "CREATE TRIGGER m4_frozen_specs BEFORE UPDATE OR DELETE ON verification_specs FOR EACH ROW EXECUTE FUNCTION zhiyu_m4_protect_contract()"
    )
    op.execute(
        "CREATE TRIGGER m4_frozen_results BEFORE UPDATE OR DELETE ON verification_results FOR EACH ROW EXECUTE FUNCTION zhiyu_m4_protect_contract()"
    )
    op.execute(
        "CREATE TRIGGER m4_frozen_checks BEFORE UPDATE OR DELETE ON verification_checks FOR EACH ROW EXECUTE FUNCTION zhiyu_m4_protect_contract()"
    )


def downgrade():
    op.execute("DROP TRIGGER m4_frozen_specs ON verification_specs")
    op.execute("DROP TRIGGER m4_frozen_results ON verification_results")
    op.execute("DROP TRIGGER m4_frozen_checks ON verification_checks")
    op.execute("DROP FUNCTION zhiyu_m4_protect_contract()")
    op.drop_table("verification_state_updates")
    op.drop_table("replan_decisions")
    op.drop_table("replan_budgets")
    op.drop_table("response_cycles")
