"""Internal persistence metadata. These are not new domain contracts."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db import (  # noqa: F401
    ai_analysis,
    ai_context,
    ai_decisions,
    ai_gateway,
    ai_planning,
    incident_intelligence,
    intelligence,
    response_authority,
    response_execution,
    response_planning,
    verification_decisions,
    verification_replan,
    verification_runtime,
)
from zhiyu.db.base import Base


class AuditHeadRow(Base):
    __tablename__ = "audit_heads"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    integrity_hash: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(["environment_id"], ["environments.environment_id"]),
        CheckConstraint("sequence >= 0", name="sequence_nonnegative"),
        CheckConstraint("(sequence = 0) = (integrity_hash IS NULL)", name="head_empty_pair"),
    )


class EventReceiptRow(Base):
    """Retain the raw reference of EVERY accepted delivery, including retransmits."""

    __tablename__ = "event_receipts"
    receipt_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_id: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_event_id: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str] = mapped_column(Text, nullable=False)
    raw_ref: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submission_hash: Mapped[str] = mapped_column(Text, nullable=False)
    disposition: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "event_id"], ["normalized_events.environment_id", "normalized_events.event_id"]
        ),
        CheckConstraint("disposition IN ('ACCEPTED','DUPLICATE')", name="receipt_disposition"),
        CheckConstraint("submission_hash ~ '^[0-9a-f]{64}$'", name="receipt_hash"),
        Index("ix_receipts_event", "environment_id", "event_id"),
        Index("ix_receipts_trace", "trace_id"),
    )


class ScopeResourceRow(Base):
    __tablename__ = "scope_resources"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    scope_id: Mapped[str] = mapped_column(Text, primary_key=True)
    resource_id: Mapped[str] = mapped_column(Text, primary_key=True)
    role: Mapped[str] = mapped_column(Text, primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(["environment_id", "scope_id"], ["scopes.environment_id", "scopes.scope_id"]),
        ForeignKeyConstraint(
            ["environment_id", "resource_id"], ["resources.environment_id", "resources.resource_id"]
        ),
        CheckConstraint("role IN ('SOURCE','TARGET')", name="scope_resource_role"),
    )


class EventResourceRow(Base):
    __tablename__ = "event_resources"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    resource_id: Mapped[str] = mapped_column(Text, primary_key=True)
    role: Mapped[str] = mapped_column(Text, primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "event_id"], ["normalized_events.environment_id", "normalized_events.event_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "resource_id"], ["resources.environment_id", "resources.resource_id"]
        ),
        CheckConstraint("role IN ('SOURCE','TARGET')", name="event_resource_role"),
    )


class RawRecordRow(Base):
    __tablename__ = "raw_records"
    raw_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    collector_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    integrity_hash: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(["environment_id"], ["environments.environment_id"]),
        UniqueConstraint("environment_id", "raw_id", name="uq_raw_environment_id"),
        CheckConstraint("integrity_hash ~ '^[0-9a-f]{64}$'", name="raw_hash"),
        CheckConstraint("octet_length(content) <= 262144", name="raw_size"),
    )


class RawDeliveryRow(Base):
    __tablename__ = "raw_deliveries"
    delivery_id: Mapped[str] = mapped_column(Text, primary_key=True)
    environment_id: Mapped[str] = mapped_column(Text, nullable=False)
    raw_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_id: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(Text, nullable=False)
    disposition: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_field: Mapped[str | None] = mapped_column(Text)
    normalization_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "raw_id"], ["raw_records.environment_id", "raw_records.raw_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "event_id"], ["normalized_events.environment_id", "normalized_events.event_id"]
        ),
        CheckConstraint("disposition IN ('ACCEPTED','DUPLICATE','ERROR')", name="raw_disposition"),
        CheckConstraint("(disposition = 'ERROR') = (error_code IS NOT NULL)", name="raw_error_pair"),
        CheckConstraint("(disposition = 'ERROR') = (event_id IS NULL)", name="raw_event_pair"),
        CheckConstraint("normalization_ms >= 0", name="normalization_duration"),
        Index("ix_raw_deliveries_environment_time", "environment_id", "created_at", "delivery_id"),
    )
