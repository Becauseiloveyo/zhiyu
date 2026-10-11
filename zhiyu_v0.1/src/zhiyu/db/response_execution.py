"""Attempt dispatch identity and immutable execution receipts, not security verdicts."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db.base import Base


class ActionDispatchRow(Base):
    __tablename__ = "action_dispatches"
    attempt_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    action_id: Mapped[str] = mapped_column(Text)
    task_id: Mapped[str] = mapped_column(Text)
    lease_id: Mapped[str] = mapped_column(Text)
    generation: Mapped[int] = mapped_column(Integer)
    authorization_id: Mapped[str] = mapped_column(Text)
    gateway_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(["attempt_id"], ["action_attempts.attempt_id"]),
        ForeignKeyConstraint(
            ["environment_id", "action_id"], ["action_requests.environment_id", "action_requests.action_id"]
        ),
        ForeignKeyConstraint(["environment_id", "task_id"], ["tasks.environment_id", "tasks.task_id"]),
        ForeignKeyConstraint(["task_id", "lease_id"], ["worker_leases.task_id", "worker_leases.lease_id"]),
        ForeignKeyConstraint(["authorization_id"], ["authorization_decisions.authorization_id"]),
        UniqueConstraint("action_id", "generation", name="uq_action_dispatch_generation"),
        CheckConstraint("generation >= 1 AND gateway_ms >= 0", name="dispatch_generation"),
    )


class ActionResultRow(Base):
    __tablename__ = "action_execution_results"
    attempt_id: Mapped[str] = mapped_column(Text, primary_key=True)
    execution_outcome: Mapped[str] = mapped_column(Text)
    executor: Mapped[str] = mapped_column(Text)
    executor_version: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    executor_ms: Mapped[float] = mapped_column(Float)
    output: Mapped[dict[str, Any]] = mapped_column(JSONB)
    output_hash: Mapped[str] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    retryable: Mapped[bool] = mapped_column(Boolean)
    side_effect: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(["attempt_id"], ["action_dispatches.attempt_id"]),
        CheckConstraint(
            "execution_outcome IN ('EXECUTION_SUCCESS','EXECUTION_FAILURE','TIMEOUT','DENIED','STALE')",
            name="action_result_outcome",
        ),
        CheckConstraint(
            "side_effect IN ('NONE','LAB_PATH') AND completed_at >= started_at AND executor_ms >= 0",
            name="action_result_read_only",
        ),
        CheckConstraint("output_hash ~ '^[0-9a-f]{64}$'", name="action_result_hash"),
    )
