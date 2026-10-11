"""Immutable model interpretation and reference-grounding receipt."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKeyConstraint, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db.base import Base


class SituationAnalysisRow(Base):
    __tablename__ = "ai_situation_analyses"
    analysis_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[str] = mapped_column(Text)
    context_id: Mapped[str] = mapped_column(Text)
    request_id: Mapped[str] = mapped_column(Text)
    model_run_id: Mapped[str | None] = mapped_column(Text)
    state_entity_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    grounding: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    grounding_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "context_id"],
            ["decision_contexts.environment_id", "decision_contexts.context_id"],
        ),
        ForeignKeyConstraint(
            ["environment_id", "request_id"], ["model_requests.environment_id", "model_requests.request_id"]
        ),
        ForeignKeyConstraint(["model_run_id"], ["model_runs.run_id"]),
        ForeignKeyConstraint(
            ["environment_id", "state_entity_id"],
            ["state_entities.environment_id", "state_entities.entity_id"],
        ),
        UniqueConstraint("request_id", name="uq_analysis_model_request"),
        UniqueConstraint("environment_id", "analysis_id", name="uq_analysis_environment"),
        CheckConstraint(
            "status IN ('REFERENCE_GROUNDED','REJECTED','FALLBACK') AND grounding_ms >= 0",
            name="analysis_status",
        ),
        Index("ix_analysis_incident", "environment_id", "incident_id", "created_at", "analysis_id"),
    )
