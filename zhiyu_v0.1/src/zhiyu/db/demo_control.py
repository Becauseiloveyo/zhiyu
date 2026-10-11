"""Internal competition orchestration metadata, not a second security fact store."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from zhiyu.db.base import Base as CoreBase


class ProductBase(DeclarativeBase):
    metadata = MetaData(schema="zhiyu_product", naming_convention=CoreBase.metadata.naming_convention)


class DemoRunRow(ProductBase):
    __tablename__ = "demo_runs"
    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    scope_id: Mapped[str] = mapped_column(Text)
    scenario_id: Mapped[str] = mapped_column(Text)
    template_sha256: Mapped[str] = mapped_column(Text)
    profile_id: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(Text)
    request_sha256: Mapped[str] = mapped_column(Text)
    predecessor_id: Mapped[str | None] = mapped_column(Text)
    run_mode: Mapped[str] = mapped_column(Text)
    model_source: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    cleanup_status: Mapped[str] = mapped_column(Text)
    cancel_requested: Mapped[bool] = mapped_column(Boolean)
    version: Mapped[int] = mapped_column(Integer)
    step_index: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(Text)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(Text)
    actual_outcome: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(["predecessor_id"], ["zhiyu_product.demo_runs.run_id"]),
        UniqueConstraint("environment_id", "actor_id", "idempotency_key", name="uq_demo_request"),
        Index("ix_demo_queue", "status", "created_at"),
        Index("ix_demo_scope", "environment_id", "scope_id", "created_at"),
        CheckConstraint("scenario_id IN ('A','B','C','D','E')", name="scenario"),
        CheckConstraint(
            "template_sha256 ~ '^[a-f0-9]{64}$' AND request_sha256 ~ '^[a-f0-9]{64}$'", name="digests"
        ),
        CheckConstraint("run_mode = 'LIVE'", name="mode"),
        CheckConstraint("model_source IN ('NONE','REAL_LOCAL_MODEL','SCRIPTED_NOT_AI')", name="model_source"),
        CheckConstraint(
            "status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED','NEEDS_RECONCILIATION')",
            name="status",
        ),
        CheckConstraint(
            "cleanup_status IN ('NOT_STARTED','QUEUED','RUNNING','CLEAN','NEEDS_MANUAL')",
            name="cleanup_status",
        ),
        CheckConstraint("version >= 1 AND step_index BETWEEN 0 AND 4", name="checkpoint"),
        CheckConstraint("deadline > created_at", name="deadline"),
        CheckConstraint("(lease_owner IS NULL) = (lease_until IS NULL)", name="lease_pair"),
        CheckConstraint(
            "actual_outcome IN ('UNKNOWN','PASS','FAIL','INCONCLUSIVE','REJECTED','FALLBACK')", name="outcome"
        ),
        CheckConstraint("length(idempotency_key) BETWEEN 16 AND 80", name="idempotency_key"),
    )


class DemoStepRow(ProductBase):
    __tablename__ = "demo_run_steps"
    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    generation: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    output: Mapped[dict[str, Any]] = mapped_column(JSONB)
    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["zhiyu_product.demo_runs.run_id"]),
        CheckConstraint("position BETWEEN 0 AND 3 OR position = 100", name="position"),
        CheckConstraint(
            "operation IN ('PREFLIGHT','TRIGGER','VERIFY','ARCHIVE','CLEANUP')", name="operation"
        ),
        CheckConstraint("status IN ('STARTED','COMPLETED','FAILED','UNKNOWN')", name="status"),
        CheckConstraint("generation > 0", name="generation"),
        CheckConstraint(
            "jsonb_typeof(output) = 'object' AND octet_length(output::text) <= 16384", name="bounded_output"
        ),
    )
