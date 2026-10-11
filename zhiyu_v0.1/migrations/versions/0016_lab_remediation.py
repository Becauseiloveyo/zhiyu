"""Internal bounded Lab receipt semantics; frozen contracts and historical migrations unchanged."""

from alembic import op

revision = "0016_lab_remediation"
down_revision = "0015_ai_decisions"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE action_execution_results DROP CONSTRAINT ck_action_execution_results_action_result_read_only"
    )
    op.execute(
        "ALTER TABLE action_execution_results ADD CONSTRAINT ck_action_execution_results_action_result_read_only CHECK (side_effect IN ('NONE','LAB_PATH') AND completed_at >= started_at AND executor_ms >= 0)"
    )


def downgrade():
    # Fail closed if new receipts exist; never erase immutable evidence to make downgrade pass.
    op.execute(
        "ALTER TABLE action_execution_results DROP CONSTRAINT ck_action_execution_results_action_result_read_only"
    )
    op.execute(
        "ALTER TABLE action_execution_results ADD CONSTRAINT ck_action_execution_results_action_result_read_only CHECK (side_effect = 'NONE' AND completed_at >= started_at AND executor_ms >= 0)"
    )
