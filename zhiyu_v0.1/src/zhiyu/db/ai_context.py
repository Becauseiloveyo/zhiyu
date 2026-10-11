"""Internal immutable state/context snapshots alongside frozen ContextBundle."""

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


class AIStateSnapshotRow(Base):
    __tablename__ = "ai_state_snapshots"
    snapshot_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[str] = mapped_column(Text)
    incident_version: Mapped[int] = mapped_column(Integer)
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    body_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        UniqueConstraint("environment_id", "snapshot_id", name="uq_ai_state_environment"),
        CheckConstraint(
            "body_hash ~ '^[0-9a-f]{64}$' AND incident_version >= 1 AND valid_until > created_at",
            name="ai_state_integrity",
        ),
    )


class DecisionContextRow(Base):
    __tablename__ = "decision_contexts"
    context_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[str] = mapped_column(Text)
    snapshot_id: Mapped[str] = mapped_column(Text)
    scope_id: Mapped[str] = mapped_column(Text)
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB)
    context_hash: Mapped[str] = mapped_column(Text)
    policy: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    build_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(["context_id"], ["context_bundles.context_id"]),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "snapshot_id"],
            ["ai_state_snapshots.environment_id", "ai_state_snapshots.snapshot_id"],
        ),
        ForeignKeyConstraint(["environment_id", "scope_id"], ["scopes.environment_id", "scopes.scope_id"]),
        UniqueConstraint("environment_id", "context_id", name="uq_decision_context_environment"),
        CheckConstraint(
            "context_hash ~ '^[0-9a-f]{64}$' AND valid_until > created_at AND build_ms >= 0",
            name="decision_context_integrity",
        ),
        Index("ix_decision_context_incident", "environment_id", "incident_id", "created_at", "context_id"),
    )
