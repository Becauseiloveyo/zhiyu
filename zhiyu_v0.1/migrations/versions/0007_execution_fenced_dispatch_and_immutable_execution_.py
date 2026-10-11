"""fenced dispatch and immutable execution receipts"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_execution"
down_revision: Union[str, None] = "0006_authority"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fixed additive dispatch/receipt metadata; execution is separate from verification.
    op.create_table(
        "action_dispatches",
        sa.Column("attempt_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("lease_id", sa.Text(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("authorization_id", sa.Text(), nullable=False),
        sa.Column("gateway_ms", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "generation >= 1 AND gateway_ms >= 0", name=op.f("ck_action_dispatches_dispatch_generation")
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["action_attempts.attempt_id"],
            name=op.f("fk_action_dispatches_attempt_id_action_attempts"),
        ),
        sa.ForeignKeyConstraint(
            ["authorization_id"],
            ["authorization_decisions.authorization_id"],
            name=op.f("fk_action_dispatches_authorization_id_authorization_decisions"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "action_id"],
            ["action_requests.environment_id", "action_requests.action_id"],
            name=op.f("fk_action_dispatches_environment_id_action_requests"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "task_id"],
            ["tasks.environment_id", "tasks.task_id"],
            name=op.f("fk_action_dispatches_environment_id_tasks"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id", "lease_id"],
            ["worker_leases.task_id", "worker_leases.lease_id"],
            name=op.f("fk_action_dispatches_task_id_worker_leases"),
        ),
        sa.PrimaryKeyConstraint("attempt_id", name=op.f("pk_action_dispatches")),
        sa.UniqueConstraint("action_id", "generation", name="uq_action_dispatch_generation"),
    )
    op.create_table(
        "action_execution_results",
        sa.Column("attempt_id", sa.Text(), nullable=False),
        sa.Column("execution_outcome", sa.Text(), nullable=False),
        sa.Column("executor", sa.Text(), nullable=False),
        sa.Column("executor_version", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executor_ms", sa.Float(), nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_hash", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("side_effect", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "execution_outcome IN ('EXECUTION_SUCCESS','EXECUTION_FAILURE','TIMEOUT','DENIED','STALE')",
            name=op.f("ck_action_execution_results_action_result_outcome"),
        ),
        sa.CheckConstraint(
            "output_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_action_execution_results_action_result_hash")
        ),
        sa.CheckConstraint(
            "side_effect = 'NONE' AND completed_at >= started_at AND executor_ms >= 0",
            name=op.f("ck_action_execution_results_action_result_read_only"),
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["action_dispatches.attempt_id"],
            name=op.f("fk_action_execution_results_attempt_id_action_dispatches"),
        ),
        sa.PrimaryKeyConstraint("attempt_id", name=op.f("pk_action_execution_results")),
    )
    op.add_column(
        "task_runtime", sa.Column("retry_allowed", sa.Boolean(), server_default="false", nullable=False)
    )
    for table in ("action_dispatches", "action_execution_results"):
        op.execute(
            f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
        )


def downgrade() -> None:
    for table in ("action_dispatches", "action_execution_results"):
        op.execute(f"DROP TRIGGER immutable_{table} ON {table}")
    op.drop_column("task_runtime", "retry_allowed")
    op.drop_table("action_execution_results")
    op.drop_table("action_dispatches")
