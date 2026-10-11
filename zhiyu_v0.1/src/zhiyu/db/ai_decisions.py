"""Immutable choice of AI, shadow comparison, deterministic fallback, or rejection."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKeyConstraint, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db.base import Base


class AIDecisionRow(Base):
    __tablename__ = "ai_decisions"
    context_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    plan_id: Mapped[str | None] = mapped_column(Text)
    receipt: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decision_ms: Mapped[float] = mapped_column(Float)
    fallback_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "context_id"],
            ["decision_contexts.environment_id", "decision_contexts.context_id"],
        ),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        ForeignKeyConstraint(["environment_id", "plan_id"], ["plans.environment_id", "plans.plan_id"]),
        CheckConstraint(
            "status IN ('AI_ASSISTED','DETERMINISTIC_FALLBACK','SHADOW','REJECTED') AND decision_ms >= 0 AND fallback_ms >= 0",
            name="ai_decision_status",
        ),
    )
