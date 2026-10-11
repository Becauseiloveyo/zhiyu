"""Internal planning metadata and relational graph; ai.5 domain rows remain canonical."""

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


class ResponsePlanRow(Base):
    __tablename__ = "response_plan_metadata"
    plan_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[str] = mapped_column(Text)
    incident_version: Mapped[int] = mapped_column(Integer)
    planner_version: Mapped[str] = mapped_column(Text)
    policy_version: Mapped[str] = mapped_column(Text)
    scope_id: Mapped[str] = mapped_column(Text)
    snapshot_hash: Mapped[str] = mapped_column(Text)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB)
    reasons: Mapped[list[Any]] = mapped_column(JSONB)
    created_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    generation_ms: Mapped[float] = mapped_column(Float)
    graph_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(["environment_id", "plan_id"], ["plans.environment_id", "plans.plan_id"]),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        ForeignKeyConstraint(["environment_id", "scope_id"], ["scopes.environment_id", "scopes.scope_id"]),
        UniqueConstraint("environment_id", "plan_id", name="uq_response_plan_environment"),
        UniqueConstraint(
            "environment_id",
            "incident_id",
            "incident_version",
            "planner_version",
            "policy_version",
            name="uq_response_plan_identity",
        ),
        CheckConstraint(
            "incident_version >= 1 AND generation_ms >= 0 AND graph_ms >= 0", name="response_plan_metrics"
        ),
        Index("ix_response_plan_time", "environment_id", "created_at", "plan_id"),
    )


class TaskRuntimeRow(Versioned, Base):
    __tablename__ = "task_runtime"
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    plan_id: Mapped[str] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(Text)
    ready_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(Text)
    result_ref: Mapped[str | None] = mapped_column(Text)
    generation: Mapped[int] = mapped_column(Integer, default=0)
    retry_allowed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    __table_args__ = (
        ForeignKeyConstraint(["environment_id", "task_id"], ["tasks.environment_id", "tasks.task_id"]),
        ForeignKeyConstraint(
            ["environment_id", "plan_id"],
            ["response_plan_metadata.environment_id", "response_plan_metadata.plan_id"],
        ),
        UniqueConstraint("environment_id", "plan_id", "task_id", name="uq_runtime_plan_task"),
        CheckConstraint("generation >= 0 AND row_version >= 1", name="task_runtime_generation"),
        Index("ix_task_runtime_ready", "environment_id", "ready_at", "task_id"),
    )


class TaskEdgeRow(Base):
    __tablename__ = "task_graph_edges"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    depends_on: Mapped[str] = mapped_column(Text, primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "plan_id", "task_id"],
            ["task_runtime.environment_id", "task_runtime.plan_id", "task_runtime.task_id"],
            name="fk_task_edge_task",
        ),
        ForeignKeyConstraint(
            ["environment_id", "plan_id", "depends_on"],
            ["task_runtime.environment_id", "task_runtime.plan_id", "task_runtime.task_id"],
            name="fk_task_edge_dependency",
        ),
        CheckConstraint("task_id <> depends_on", name="task_edge_no_self"),
        Index("ix_task_edge_blocks", "environment_id", "depends_on"),
    )
