"""Terminal proposal validation and at most one accepted AI lineage per incident version."""

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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db.base import Base


class AIProposalRow(Base):
    __tablename__ = "ai_plan_proposals"
    proposal_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[str] = mapped_column(Text)
    incident_version: Mapped[int] = mapped_column(Integer)
    context_id: Mapped[str] = mapped_column(Text)
    analysis_id: Mapped[str] = mapped_column(Text)
    request_id: Mapped[str] = mapped_column(Text)
    model_run_id: Mapped[str | None] = mapped_column(Text)
    parent_verification_id: Mapped[str | None] = mapped_column(Text)
    plan_id: Mapped[str | None] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    validation: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    planning_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "context_id"],
            ["decision_contexts.environment_id", "decision_contexts.context_id"],
        ),
        ForeignKeyConstraint(
            ["environment_id", "analysis_id"],
            ["ai_situation_analyses.environment_id", "ai_situation_analyses.analysis_id"],
        ),
        ForeignKeyConstraint(
            ["environment_id", "request_id"], ["model_requests.environment_id", "model_requests.request_id"]
        ),
        ForeignKeyConstraint(["model_run_id"], ["model_runs.run_id"]),
        ForeignKeyConstraint(["parent_verification_id"], ["verification_results.verification_id"]),
        ForeignKeyConstraint(["environment_id", "plan_id"], ["plans.environment_id", "plans.plan_id"]),
        UniqueConstraint("request_id", name="uq_ai_proposal_request"),
        CheckConstraint(
            "status IN ('ACCEPTED','SHADOW','REJECTED','FALLBACK') AND mode IN ('SHADOW','ASSISTED') AND planning_ms >= 0 AND incident_version >= 1",
            name="proposal_status",
        ),
        CheckConstraint("(status = 'ACCEPTED') = (plan_id IS NOT NULL)", name="proposal_accepted_plan"),
        Index(
            "uq_ai_accepted_lineage",
            "environment_id",
            "incident_id",
            "incident_version",
            unique=True,
            postgresql_where=text("plan_id IS NOT NULL"),
        ),
        Index("ix_ai_proposals_incident", "environment_id", "incident_id", "created_at", "proposal_id"),
    )
