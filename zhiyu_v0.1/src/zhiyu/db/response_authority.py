"""Managed capability/policy configuration and execution authorization metadata."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
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


class CapabilityConfigRow(Versioned, Base):
    __tablename__ = "capability_runtime_config"
    capability_id: Mapped[str] = mapped_column(Text, primary_key=True)
    version: Mapped[str] = mapped_column(Text, primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean)
    definition_hash: Mapped[str] = mapped_column(Text)
    supported_resource_types: Mapped[list[Any]] = mapped_column(JSONB)
    supported_profiles: Mapped[list[Any]] = mapped_column(JSONB)
    minimum_autonomy: Mapped[str] = mapped_column(Text)
    business_impact: Mapped[str] = mapped_column(Text)
    retry_policy: Mapped[dict[str, Any]] = mapped_column(JSONB)
    __table_args__ = (
        ForeignKeyConstraint(
            ["capability_id", "version"], ["capabilities.capability_id", "capabilities.version"]
        ),
        CheckConstraint(
            "business_impact IN ('LOW','MEDIUM','HIGH','CRITICAL') AND row_version >= 1",
            name="capability_runtime_impact",
        ),
    )


class ResponseControlRow(Versioned, Base):
    __tablename__ = "response_controls"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    policy_version: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_probe_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(["environment_id"], ["environments.environment_id"]),
        CheckConstraint("valid_until > valid_from AND row_version >= 1", name="response_control_interval"),
    )


class CapabilityHealthObservationRow(Base):
    __tablename__ = "capability_health_observations"
    observation_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    capability_id: Mapped[str] = mapped_column(Text)
    capability_version: Mapped[str] = mapped_column(Text)
    worker_pool: Mapped[str] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(["environment_id"], ["environments.environment_id"]),
        ForeignKeyConstraint(
            ["capability_id", "capability_version"], ["capabilities.capability_id", "capabilities.version"]
        ),
        CheckConstraint(
            "status IN ('UNVERIFIED','HEALTHY','DEGRADED','OFFLINE')", name="capability_observation_status"
        ),
        Index("ix_capability_health_observed", "environment_id", "capability_id", "checked_at"),
    )


class ResponseBudgetRow(Versioned, Base):
    __tablename__ = "response_budgets"
    budget_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    plan_id: Mapped[str] = mapped_column(Text)
    max_actions: Mapped[int] = mapped_column(Integer)
    used_actions: Mapped[int] = mapped_column(Integer)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "plan_id"],
            ["response_plan_metadata.environment_id", "response_plan_metadata.plan_id"],
        ),
        UniqueConstraint("environment_id", "plan_id", name="uq_response_budget_plan"),
        UniqueConstraint("environment_id", "budget_id", name="uq_response_budget_environment"),
        CheckConstraint(
            "max_actions >= 1 AND used_actions >= 0 AND used_actions <= max_actions",
            name="response_budget_limit",
        ),
    )


class AuthorizationSnapshotRow(Base):
    __tablename__ = "response_authorization_snapshots"
    context_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    action_id: Mapped[str] = mapped_column(Text)
    budget_id: Mapped[str] = mapped_column(Text)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB)
    rule_id: Mapped[str] = mapped_column(Text)
    denied_dimensions: Mapped[list[Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    authorization_ms: Mapped[float] = mapped_column(Float)
    policy_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(["context_id"], ["authorization_contexts.authorization_context_id"]),
        ForeignKeyConstraint(
            ["environment_id", "action_id"], ["action_requests.environment_id", "action_requests.action_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "budget_id"], ["response_budgets.environment_id", "response_budgets.budget_id"]
        ),
        CheckConstraint("authorization_ms >= 0 AND policy_ms >= 0", name="response_authorization_latency"),
    )


class ActionControlRow(Versioned, Base):
    __tablename__ = "action_control"
    action_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    task_id: Mapped[str] = mapped_column(Text)
    budget_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    authorization_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "action_id"], ["action_requests.environment_id", "action_requests.action_id"]
        ),
        ForeignKeyConstraint(["environment_id", "task_id"], ["tasks.environment_id", "tasks.task_id"]),
        ForeignKeyConstraint(
            ["environment_id", "budget_id"], ["response_budgets.environment_id", "response_budgets.budget_id"]
        ),
        ForeignKeyConstraint(["authorization_id"], ["authorization_decisions.authorization_id"]),
        UniqueConstraint("environment_id", "task_id", name="uq_action_control_task"),
        CheckConstraint(
            "status IN ('PROPOSED','AUTHORIZED','WAITING_APPROVAL','DENIED','EXPIRED','DISPATCHED','EXECUTING','EXECUTED','FAILED','EXECUTION_UNKNOWN','RECONCILING','NEEDS_MANUAL','CANCELLED')",
            name="action_control_status",
        ),
        Index("ix_action_control_time", "environment_id", "created_at", "action_id"),
    )
