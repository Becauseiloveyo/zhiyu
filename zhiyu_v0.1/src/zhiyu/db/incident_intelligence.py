"""Persistence metadata and relational lineage, not a second Incident contract."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKeyConstraint, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db.base import Base


class IncidentAnalysisRow(Base):
    __tablename__ = "incident_analysis"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    incident_id: Mapped[str] = mapped_column(Text, primary_key=True)
    merge_key: Mapped[str] = mapped_column(Text, nullable=False)
    policy_hash: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    factors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        CheckConstraint("score BETWEEN 0 AND 100", name="incident_analysis_score"),
        Index("ix_incident_merge", "environment_id", "merge_key", "policy_hash"),
        Index("ix_incident_risk", "environment_id", "score", "incident_id"),
    )


class IncidentGroupRow(Base):
    __tablename__ = "incident_groups"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    group_id: Mapped[str] = mapped_column(Text, primary_key=True)
    incident_id: Mapped[str] = mapped_column(Text, nullable=False)
    group_version: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "group_id"], ["event_groups.environment_id", "event_groups.group_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        CheckConstraint("group_version >= 1", name="incident_group_version"),
        Index("ix_incident_groups_incident", "environment_id", "incident_id", "group_id"),
    )


class IncidentEventRow(Base):
    __tablename__ = "incident_events"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    incident_id: Mapped[str] = mapped_column(Text, primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    evidence_id: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "event_id"], ["normalized_events.environment_id", "normalized_events.event_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "incident_id", "evidence_id"],
            ["evidence.environment_id", "evidence.incident_id", "evidence.evidence_id"],
        ),
    )


class PromotionRecordRow(Base):
    __tablename__ = "incident_promotions"
    environment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    group_id: Mapped[str] = mapped_column(Text, primary_key=True)
    group_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    incident_id: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    promotion_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "group_id"], ["event_groups.environment_id", "event_groups.group_id"]
        ),
        ForeignKeyConstraint(
            ["environment_id", "incident_id"], ["incidents.environment_id", "incidents.incident_id"]
        ),
        CheckConstraint("outcome IN ('CREATED','MERGED','UPDATED','NOT_PROMOTED')", name="promotion_outcome"),
        CheckConstraint("group_version >= 1 AND promotion_ms >= 0", name="promotion_bounds"),
    )
