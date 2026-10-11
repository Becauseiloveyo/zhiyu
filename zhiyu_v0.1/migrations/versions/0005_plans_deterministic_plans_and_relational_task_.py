"""deterministic plans and relational task graph"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_plans"
down_revision: Union[str, None] = "0004_incidents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fixed additive migration, reviewed against the frozen contract tables.
    op.create_table(
        "response_plan_metadata",
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.Text(), nullable=False),
        sa.Column("incident_version", sa.Integer(), nullable=False),
        sa.Column("planner_version", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=False),
        sa.Column("snapshot_hash", sa.Text(), nullable=False),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generation_ms", sa.Float(), nullable=False),
        sa.Column("graph_ms", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "incident_version >= 1 AND generation_ms >= 0 AND graph_ms >= 0",
            name=op.f("ck_response_plan_metadata_response_plan_metrics"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "incident_id"],
            ["incidents.environment_id", "incidents.incident_id"],
            name=op.f("fk_response_plan_metadata_environment_id_incidents"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "plan_id"],
            ["plans.environment_id", "plans.plan_id"],
            name=op.f("fk_response_plan_metadata_environment_id_plans"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "scope_id"],
            ["scopes.environment_id", "scopes.scope_id"],
            name=op.f("fk_response_plan_metadata_environment_id_scopes"),
        ),
        sa.PrimaryKeyConstraint("plan_id", name=op.f("pk_response_plan_metadata")),
        sa.UniqueConstraint(
            "environment_id",
            "incident_id",
            "incident_version",
            "planner_version",
            "policy_version",
            name="uq_response_plan_identity",
        ),
        sa.UniqueConstraint("environment_id", "plan_id", name="uq_response_plan_environment"),
    )
    op.create_index(
        "ix_response_plan_time",
        "response_plan_metadata",
        ["environment_id", "created_at", "plan_id"],
        unique=False,
    )
    op.create_table(
        "task_runtime",
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_code", sa.Text(), nullable=True),
        sa.Column("result_ref", sa.Text(), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "generation >= 0 AND row_version >= 1", name=op.f("ck_task_runtime_task_runtime_generation")
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "plan_id"],
            ["response_plan_metadata.environment_id", "response_plan_metadata.plan_id"],
            name=op.f("fk_task_runtime_environment_id_response_plan_metadata"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "task_id"],
            ["tasks.environment_id", "tasks.task_id"],
            name=op.f("fk_task_runtime_environment_id_tasks"),
        ),
        sa.PrimaryKeyConstraint("task_id", name=op.f("pk_task_runtime")),
        sa.UniqueConstraint("environment_id", "plan_id", "task_id", name="uq_runtime_plan_task"),
    )
    op.create_index(
        "ix_task_runtime_ready", "task_runtime", ["environment_id", "ready_at", "task_id"], unique=False
    )
    op.create_table(
        "task_graph_edges",
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("depends_on", sa.Text(), nullable=False),
        sa.CheckConstraint("task_id <> depends_on", name=op.f("ck_task_graph_edges_task_edge_no_self")),
        sa.ForeignKeyConstraint(
            ["environment_id", "plan_id", "depends_on"],
            ["task_runtime.environment_id", "task_runtime.plan_id", "task_runtime.task_id"],
            name="fk_task_edge_dependency",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "plan_id", "task_id"],
            ["task_runtime.environment_id", "task_runtime.plan_id", "task_runtime.task_id"],
            name="fk_task_edge_task",
        ),
        sa.PrimaryKeyConstraint(
            "environment_id", "plan_id", "task_id", "depends_on", name=op.f("pk_task_graph_edges")
        ),
    )
    op.create_index("ix_task_edge_blocks", "task_graph_edges", ["environment_id", "depends_on"], unique=False)
    for table in ("plans", "task_graph_edges"):
        op.execute(
            f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
        )
    op.execute("""CREATE FUNCTION zhiyu_guard_plan_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' OR
             (to_jsonb(NEW) - 'graph_ms' - 'generation_ms') IS DISTINCT FROM
             (to_jsonb(OLD) - 'graph_ms' - 'generation_ms') THEN
            RAISE EXCEPTION 'immutable plan snapshot' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$""")
    op.execute(
        "CREATE TRIGGER immutable_response_plan_snapshot BEFORE UPDATE OR DELETE ON response_plan_metadata FOR EACH ROW EXECUTE FUNCTION zhiyu_guard_plan_snapshot()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER immutable_response_plan_snapshot ON response_plan_metadata")
    op.execute("DROP FUNCTION zhiyu_guard_plan_snapshot()")
    op.execute("DROP TRIGGER immutable_plans ON plans")
    op.execute("DROP TRIGGER immutable_task_graph_edges ON task_graph_edges")
    op.drop_index("ix_task_edge_blocks", table_name="task_graph_edges")
    op.drop_table("task_graph_edges")
    op.drop_index("ix_task_runtime_ready", table_name="task_runtime")
    op.drop_table("task_runtime")
    op.drop_index("ix_response_plan_time", table_name="response_plan_metadata")
    op.drop_table("response_plan_metadata")
