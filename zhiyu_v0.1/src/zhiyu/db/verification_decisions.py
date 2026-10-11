"""Internal effect interpretation retains raw versus qualified verdicts."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKeyConstraint, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zhiyu.db.base import Base


class EffectivenessRow(Base):
    __tablename__ = "verification_effectiveness"
    verification_id: Mapped[str] = mapped_column(Text, primary_key=True)
    raw_dimensions: Mapped[dict[str, Any]] = mapped_column(JSONB)
    qualification_failures: Mapped[list[Any]] = mapped_column(JSONB)
    decision: Mapped[dict[str, Any]] = mapped_column(JSONB)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decision_ms: Mapped[float] = mapped_column(Float)
    __table_args__ = (ForeignKeyConstraint(["verification_id"], ["verification_results.verification_id"]),)
