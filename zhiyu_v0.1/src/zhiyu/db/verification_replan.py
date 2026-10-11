"""Internal opt-in lifecycle binding, durable budgets, lineage and state history."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKeyConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db.base import Base, Versioned


class ResponseCycleRow(Versioned, Base):
    __tablename__ = "response_cycles"
    plan_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[str] = mapped_column(Text)
    expected_version: Mapped[int] = mapped_column(Integer)
    semantic_hash: Mapped[str] = mapped_column(Text)
    root_plan_id: Mapped[str] = mapped_column(Text)
    parent_plan_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(["environment_id", "plan_id"], ["plans.environment_id", "plans.plan_id"]),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        ForeignKeyConstraint(["root_plan_id"], ["plans.plan_id"]),
        ForeignKeyConstraint(["parent_plan_id"], ["plans.plan_id"]),
    )


class ReplanBudgetRow(Versioned, Base):
    __tablename__ = "replan_budgets"
    root_plan_id: Mapped[str] = mapped_column(Text, primary_key=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB)
    current_replan_count: Mapped[int] = mapped_column(Integer)
    reserved_actions: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(["root_plan_id"], ["plans.plan_id"]),
        CheckConstraint("current_replan_count >= 0 AND reserved_actions >= 0", name="replan_budget_counts"),
    )


class ReplanDecisionRow(Base):
    __tablename__ = "replan_decisions"
    verification_id: Mapped[str] = mapped_column(Text, primary_key=True)
    root_plan_id: Mapped[str] = mapped_column(Text)
    parent_plan_id: Mapped[str] = mapped_column(Text)
    new_plan_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    replan_count: Mapped[int] = mapped_column(Integer)
    policy_version: Mapped[str] = mapped_column(Text)
    plan_fingerprint: Mapped[str] = mapped_column(Text)
    action_fingerprint: Mapped[str] = mapped_column(Text)
    evidence_fingerprint: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(["verification_id"], ["verification_results.verification_id"]),
        ForeignKeyConstraint(["root_plan_id"], ["plans.plan_id"]),
        ForeignKeyConstraint(["parent_plan_id"], ["plans.plan_id"]),
        ForeignKeyConstraint(["new_plan_id"], ["plans.plan_id"]),
        UniqueConstraint("new_plan_id", name="uq_replan_new_plan"),
        CheckConstraint(
            "status IN ('NO_REPLAN','CREATED','REPLAN_EXHAUSTED','REQUIRE_APPROVAL','BLOCKED')",
            name="replan_status",
        ),
    )


class VerificationStateUpdateRow(Base):
    __tablename__ = "verification_state_updates"
    verification_id: Mapped[str] = mapped_column(Text, primary_key=True)
    entity_ids: Mapped[list[Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (ForeignKeyConstraint(["verification_id"], ["verification_results.verification_id"]),)
