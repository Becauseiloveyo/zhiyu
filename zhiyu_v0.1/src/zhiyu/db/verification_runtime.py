"""Internal bindings, fenced check jobs and immutable independent observations."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKeyConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db.base import Base, Versioned


class VerificationRuntimeRow(Base):
    __tablename__ = "verification_runtime"
    spec_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[str] = mapped_column(Text)
    plan_id: Mapped[str] = mapped_column(Text)
    task_id: Mapped[str] = mapped_column(Text)
    action_id: Mapped[str] = mapped_column(Text)
    action_result_id: Mapped[str] = mapped_column(Text)
    scope_id: Mapped[str] = mapped_column(Text)
    run_id: Mapped[str] = mapped_column(Text)
    policy: Mapped[dict[str, Any]] = mapped_column(JSONB)
    binding: Mapped[dict[str, Any]] = mapped_column(JSONB)
    spec_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    generation_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(["spec_id"], ["verification_specs.verification_spec_id"]),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "plan_id", "task_id"],
            ["task_runtime.environment_id", "task_runtime.plan_id", "task_runtime.task_id"],
        ),
        ForeignKeyConstraint(
            ["environment_id", "action_id"], ["action_requests.environment_id", "action_requests.action_id"]
        ),
        ForeignKeyConstraint(["action_result_id"], ["action_execution_results.attempt_id"]),
        ForeignKeyConstraint(["environment_id", "scope_id"], ["scopes.environment_id", "scopes.scope_id"]),
        ForeignKeyConstraint(
            ["environment_id", "run_id"], ["validation_runs.environment_id", "validation_runs.run_id"]
        ),
        UniqueConstraint("environment_id", "spec_id", name="uq_verification_runtime_env"),
        CheckConstraint(
            "valid_until > created_at AND generation_ms >= 0", name="verification_runtime_interval"
        ),
    )


class VerificationCheckRow(Versioned, Base):
    __tablename__ = "verification_checks"
    spec_id: Mapped[str] = mapped_column(Text, primary_key=True)
    check_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, default="PENDING")
    generation: Mapped[int] = mapped_column(Integer, default=0)
    worker_id: Mapped[str | None] = mapped_column(Text)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "spec_id"],
            ["verification_runtime.environment_id", "verification_runtime.spec_id"],
        ),
        CheckConstraint(
            "status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','TIMEOUT','INCONCLUSIVE','CANCELLED')",
            name="verification_check_status",
        ),
        CheckConstraint("generation >= 0 AND row_version >= 1", name="verification_check_generation"),
        CheckConstraint(
            "(status = 'RUNNING') = (worker_id IS NOT NULL AND lease_until IS NOT NULL)",
            name="verification_check_lease",
        ),
    )


class VerificationObservationRow(Base):
    __tablename__ = "verification_observations"
    spec_id: Mapped[str] = mapped_column(Text, primary_key=True)
    check_id: Mapped[str] = mapped_column(Text, primary_key=True)
    evidence_id: Mapped[str] = mapped_column(Text)
    generation: Mapped[int] = mapped_column(Integer)
    execution_status: Mapped[str] = mapped_column(Text)
    assertion_status: Mapped[str] = mapped_column(Text)
    samples: Mapped[list[Any]] = mapped_column(JSONB)
    assertions: Mapped[list[Any]] = mapped_column(JSONB)
    reason: Mapped[str] = mapped_column(Text)
    executor_version: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(
            ["spec_id", "check_id"], ["verification_checks.spec_id", "verification_checks.check_id"]
        ),
        ForeignKeyConstraint(["evidence_id"], ["evidence.evidence_id"]),
        UniqueConstraint("evidence_id", name="uq_verification_observation_evidence"),
        CheckConstraint(
            "assertion_status IN ('PASS','FAIL','INCONCLUSIVE')", name="verification_assertion_status"
        ),
        CheckConstraint(
            "checked_at >= started_at AND generation >= 1 AND latency_ms >= 0",
            name="verification_observation_interval",
        ),
    )
