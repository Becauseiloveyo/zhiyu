"""managed capability and authorization snapshots"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_authority"
down_revision: Union[str, None] = "0005_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fixed additive runtime metadata; original contract tables are reused.
    op.create_table(
        "capability_health_observations",
        sa.Column("observation_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("capability_id", sa.Text(), nullable=False),
        sa.Column("capability_version", sa.Text(), nullable=False),
        sa.Column("worker_pool", sa.Text(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('UNVERIFIED','HEALTHY','DEGRADED','OFFLINE')",
            name=op.f("ck_capability_health_observations_capability_observation_status"),
        ),
        sa.ForeignKeyConstraint(
            ["capability_id", "capability_version"],
            ["capabilities.capability_id", "capabilities.version"],
            name=op.f("fk_capability_health_observations_capability_id_capabilities"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["environments.environment_id"],
            name=op.f("fk_capability_health_observations_environment_id_environments"),
        ),
        sa.PrimaryKeyConstraint("observation_id", name=op.f("pk_capability_health_observations")),
    )
    op.create_index(
        "ix_capability_health_observed",
        "capability_health_observations",
        ["environment_id", "capability_id", "checked_at"],
        unique=False,
    )
    op.create_table(
        "capability_runtime_config",
        sa.Column("capability_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("definition_hash", sa.Text(), nullable=False),
        sa.Column("supported_resource_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("supported_profiles", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minimum_autonomy", sa.Text(), nullable=False),
        sa.Column("business_impact", sa.Text(), nullable=False),
        sa.Column("retry_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "business_impact IN ('LOW','MEDIUM','HIGH','CRITICAL') AND row_version >= 1",
            name=op.f("ck_capability_runtime_config_capability_runtime_impact"),
        ),
        sa.ForeignKeyConstraint(
            ["capability_id", "version"],
            ["capabilities.capability_id", "capabilities.version"],
            name=op.f("fk_capability_runtime_config_capability_id_capabilities"),
        ),
        sa.PrimaryKeyConstraint("capability_id", "version", name=op.f("pk_capability_runtime_config")),
    )
    op.create_table(
        "response_controls",
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_probe_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "valid_until > valid_from AND row_version >= 1",
            name=op.f("ck_response_controls_response_control_interval"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["environments.environment_id"],
            name=op.f("fk_response_controls_environment_id_environments"),
        ),
        sa.PrimaryKeyConstraint("environment_id", name=op.f("pk_response_controls")),
    )
    op.create_table(
        "response_budgets",
        sa.Column("budget_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column("max_actions", sa.Integer(), nullable=False),
        sa.Column("used_actions", sa.Integer(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "max_actions >= 1 AND used_actions >= 0 AND used_actions <= max_actions",
            name=op.f("ck_response_budgets_response_budget_limit"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "plan_id"],
            ["response_plan_metadata.environment_id", "response_plan_metadata.plan_id"],
            name=op.f("fk_response_budgets_environment_id_response_plan_metadata"),
        ),
        sa.PrimaryKeyConstraint("budget_id", name=op.f("pk_response_budgets")),
        sa.UniqueConstraint("environment_id", "budget_id", name="uq_response_budget_environment"),
        sa.UniqueConstraint("environment_id", "plan_id", name="uq_response_budget_plan"),
    )
    op.create_table(
        "action_control",
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("budget_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("authorization_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "status IN ('PROPOSED','AUTHORIZED','WAITING_APPROVAL','DENIED','EXPIRED','DISPATCHED','EXECUTING','EXECUTED','FAILED','EXECUTION_UNKNOWN','RECONCILING','NEEDS_MANUAL','CANCELLED')",
            name=op.f("ck_action_control_action_control_status"),
        ),
        sa.ForeignKeyConstraint(
            ["authorization_id"],
            ["authorization_decisions.authorization_id"],
            name=op.f("fk_action_control_authorization_id_authorization_decisions"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "action_id"],
            ["action_requests.environment_id", "action_requests.action_id"],
            name=op.f("fk_action_control_environment_id_action_requests"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "budget_id"],
            ["response_budgets.environment_id", "response_budgets.budget_id"],
            name=op.f("fk_action_control_environment_id_response_budgets"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "task_id"],
            ["tasks.environment_id", "tasks.task_id"],
            name=op.f("fk_action_control_environment_id_tasks"),
        ),
        sa.PrimaryKeyConstraint("action_id", name=op.f("pk_action_control")),
        sa.UniqueConstraint("environment_id", "task_id", name="uq_action_control_task"),
    )
    op.create_index(
        "ix_action_control_time",
        "action_control",
        ["environment_id", "created_at", "action_id"],
        unique=False,
    )
    op.create_table(
        "response_authorization_snapshots",
        sa.Column("context_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("budget_id", sa.Text(), nullable=False),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_id", sa.Text(), nullable=False),
        sa.Column("denied_dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authorization_ms", sa.Float(), nullable=False),
        sa.Column("policy_ms", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "authorization_ms >= 0 AND policy_ms >= 0",
            name=op.f("ck_response_authorization_snapshots_response_authorization_latency"),
        ),
        sa.ForeignKeyConstraint(
            ["context_id"],
            ["authorization_contexts.authorization_context_id"],
            name=op.f("fk_response_authorization_snapshots_context_id_authorization_contexts"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "action_id"],
            ["action_requests.environment_id", "action_requests.action_id"],
            name=op.f("fk_response_authorization_snapshots_environment_id_action_requests"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "budget_id"],
            ["response_budgets.environment_id", "response_budgets.budget_id"],
            name=op.f("fk_response_authorization_snapshots_environment_id_response_budgets"),
        ),
        sa.PrimaryKeyConstraint("context_id", name=op.f("pk_response_authorization_snapshots")),
    )
    for table in ("response_authorization_snapshots", "capability_health_observations"):
        op.execute(
            f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
        )


def downgrade() -> None:
    for table in ("response_authorization_snapshots", "capability_health_observations"):
        op.execute(f"DROP TRIGGER immutable_{table} ON {table}")
    op.drop_table("response_authorization_snapshots")
    op.drop_index("ix_action_control_time", table_name="action_control")
    op.drop_table("action_control")
    op.drop_table("response_budgets")
    op.drop_table("response_controls")
    op.drop_table("capability_runtime_config")
    op.drop_index("ix_capability_health_observed", table_name="capability_health_observations")
    op.drop_table("capability_health_observations")
