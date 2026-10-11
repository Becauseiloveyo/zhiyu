"""Internal indexes/relations for frozen EventGroup and CorrelationDecision contracts."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db.base import Base


class GroupStateRow(Base):
    __tablename__ = "event_group_state"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    group_id: Mapped[str] = mapped_column(Text, primary_key=True)
    key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    disposition: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "group_id"], ["event_groups.environment_id", "event_groups.group_id"]
        ),
        UniqueConstraint("environment_id", "key_hash", name="uq_group_logical_key"),
        CheckConstraint("status IN ('OPEN','CLOSED')", name="group_state_status"),
        CheckConstraint("disposition IN ('TIMELY','LATE','EXPIRED','FUTURE')", name="group_disposition"),
        CheckConstraint(
            "version >= 1 AND window_end > window_start AND updated_at >= created_at",
            name="group_state_bounds",
        ),
        Index("ix_group_state_window", "environment_id", "status", "window_end"),
    )


class GroupMemberRow(Base):
    __tablename__ = "event_group_members"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    group_id: Mapped[str] = mapped_column(Text, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "event_id"], ["normalized_events.environment_id", "normalized_events.event_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "group_id"], ["event_groups.environment_id", "event_groups.group_id"]
        ),
        Index("ix_members_group", "environment_id", "group_id", "event_id"),
    )


class DecisionInputRow(Base):
    __tablename__ = "correlation_decision_inputs"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    decision_id: Mapped[str] = mapped_column(Text, primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    role: Mapped[str] = mapped_column(Text, primary_key=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "decision_id"],
            ["correlation_decisions.environment_id", "correlation_decisions.decision_id"],
        ),
        ForeignKeyConstraint(
            ["environment_id", "event_id"], ["normalized_events.environment_id", "normalized_events.event_id"]
        ),
        CheckConstraint("role IN ('INPUT','EXCLUDED')", name="decision_input_role"),
    )


class IntelligenceRunRow(Base):
    __tablename__ = "intelligence_runs"
    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    processed: Mapped[int] = mapped_column(Integer, nullable=False)
    groups_created: Mapped[int] = mapped_column(Integer, nullable=False)
    decisions_created: Mapped[int] = mapped_column(Integer, nullable=False)
    correlation_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(["environment_id"], ["environments.environment_id"]),
        CheckConstraint(
            "processed >= 0 AND groups_created >= 0 AND decisions_created >= 0 AND correlation_ms >= 0",
            name="intelligence_counts",
        ),
        Index("ix_intelligence_run_environment", "environment_id", "created_at"),
    )
