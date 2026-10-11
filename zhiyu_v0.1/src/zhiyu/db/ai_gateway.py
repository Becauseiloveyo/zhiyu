"""Internal durable model request/reservation metadata; terminal ModelRun is frozen ai.5."""

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

from zhiyu.db.base import Base, Versioned


class AIIncidentBudgetRow(Versioned, Base):
    __tablename__ = "ai_incident_budgets"
    incident_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB)
    call_count: Mapped[int] = mapped_column(Integer)
    charged_tokens: Mapped[int] = mapped_column(Integer)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    ai_replans: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        CheckConstraint(
            "call_count >= 0 AND charged_tokens >= 0 AND input_tokens >= 0 AND output_tokens >= 0 AND ai_replans >= 0",
            name="ai_budget_nonnegative",
        ),
    )


class ModelRequestRow(Versioned, Base):
    __tablename__ = "model_requests"
    request_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[str] = mapped_column(Text)
    context_id: Mapped[str] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(Text)
    routing_version: Mapped[str] = mapped_column(Text)
    configuration_hash: Mapped[str] = mapped_column(Text)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB)
    input_body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    input_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    worker_id: Mapped[str | None] = mapped_column(Text)
    reserved_tokens: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "context_id"],
            ["decision_contexts.environment_id", "decision_contexts.context_id"],
        ),
        UniqueConstraint("environment_id", "request_id", name="uq_model_request_environment"),
        CheckConstraint(
            "task_type IN ('ANALYSIS','PLAN') AND status IN ('RUNNING','COMPLETED','FALLBACK')",
            name="model_request_state",
        ),
        CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$' AND configuration_hash ~ '^[0-9a-f]{64}$' AND reserved_tokens >= 0 AND lease_until > started_at",
            name="model_request_integrity",
        ),
        Index("ix_model_request_incident", "environment_id", "incident_id", "started_at", "request_id"),
    )


class ModelReceiptRow(Base):
    __tablename__ = "model_receipts"
    request_id: Mapped[str] = mapped_column(Text, primary_key=True)
    model_run_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    usage_known: Mapped[bool] = mapped_column()
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider_ms: Mapped[float] = mapped_column(Float)
    overhead_ms: Mapped[float] = mapped_column(Float)
    schema_validation_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(["request_id"], ["model_requests.request_id"]),
        ForeignKeyConstraint(["model_run_id"], ["model_runs.run_id"]),
        UniqueConstraint("model_run_id", name="uq_model_receipt_run"),
        CheckConstraint(
            "status IN ('COMPLETED','FALLBACK') AND provider_ms >= 0 AND overhead_ms >= 0 AND schema_validation_ms >= 0",
            name="model_receipt_integrity",
        ),
    )
