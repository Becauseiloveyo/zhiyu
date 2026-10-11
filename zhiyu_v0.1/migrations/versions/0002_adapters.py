"""Immutable raw provenance and per-record adapter results.

Revision ID: 0002_adapters
Revises: 0001_m1_1
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_adapters"
down_revision = "0001_m1_1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_records",
        sa.Column("raw_id", sa.Text(), primary_key=True),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("collector_id", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("integrity_hash", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.environment_id"]),
        sa.UniqueConstraint("environment_id", "raw_id", name="uq_raw_environment_id"),
        sa.CheckConstraint("integrity_hash ~ '^[0-9a-f]{64}$'", name="raw_hash"),
        sa.CheckConstraint("octet_length(content) <= 262144", name="raw_size"),
    )
    op.create_table(
        "raw_deliveries",
        sa.Column("delivery_id", sa.Text(), primary_key=True),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("raw_id", sa.Text(), nullable=False),
        sa.Column("event_id", sa.Text()),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("disposition", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text()),
        sa.Column("error_field", sa.Text()),
        sa.Column("normalization_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["environment_id", "raw_id"], ["raw_records.environment_id", "raw_records.raw_id"]
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "event_id"], ["normalized_events.environment_id", "normalized_events.event_id"]
        ),
        sa.CheckConstraint("disposition IN ('ACCEPTED','DUPLICATE','ERROR')", name="raw_disposition"),
        sa.CheckConstraint("(disposition = 'ERROR') = (error_code IS NOT NULL)", name="raw_error_pair"),
        sa.CheckConstraint("(disposition = 'ERROR') = (event_id IS NULL)", name="raw_event_pair"),
        sa.CheckConstraint("normalization_ms >= 0", name="normalization_duration"),
    )
    op.create_index(
        "ix_raw_deliveries_environment_time",
        "raw_deliveries",
        ["environment_id", "created_at", "delivery_id"],
    )
    for table in ("raw_records", "raw_deliveries"):
        op.execute(
            f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
        )


def downgrade() -> None:
    op.drop_table("raw_deliveries")
    op.drop_table("raw_records")
