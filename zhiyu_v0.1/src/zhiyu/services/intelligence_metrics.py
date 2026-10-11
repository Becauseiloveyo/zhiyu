from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.incident_intelligence import PromotionRecordRow
from zhiyu.db.infrastructure import EventReceiptRow, RawDeliveryRow
from zhiyu.db.intelligence import GroupMemberRow, GroupStateRow, IntelligenceRunRow
from zhiyu.db.models import EventRow


def metrics(db: Session, environment_id: str, principal: ServicePrincipal) -> dict[str, Any]:
    principal.require("incidents:read", environment_id)

    def count(row: Any, *filters: Any) -> int:
        return (
            db.scalar(
                select(func.count()).select_from(row).where(row.environment_id == environment_id, *filters)
            )
            or 0
        )

    states = list(db.scalars(select(GroupStateRow).where(GroupStateRow.environment_id == environment_id)))
    durations = sorted(
        db.scalars(
            select(IntelligenceRunRow.correlation_ms).where(
                IntelligenceRunRow.environment_id == environment_id, IntelligenceRunRow.processed > 0
            )
        )
    )
    grouped, groups = count(GroupMemberRow), len(states)
    normalized = count(EventRow)
    promotion_times = sorted(
        db.scalars(
            select(PromotionRecordRow.promotion_ms).where(PromotionRecordRow.environment_id == environment_id)
        )
    )
    return {
        "environment_id": environment_id,
        "raw_event_count": count(RawDeliveryRow),
        "normalized_event_count": normalized,
        "adapter_error_count": count(RawDeliveryRow, RawDeliveryRow.disposition == "ERROR"),
        "duplicate_count": count(EventReceiptRow, EventReceiptRow.disposition == "DUPLICATE"),
        "grouped_event_count": grouped,
        "event_group_count": groups,
        "pending_event_count": normalized - grouped,
        "compression_ratio": grouped / groups if groups else 0,
        "compression_semantics": "retained member events divided by groups; no evidence deletion",
        "correlation_latency_ms": {
            "samples": len(durations),
            "mean": sum(durations) / len(durations) if durations else 0,
            "p95": durations[min(len(durations) - 1, int(len(durations) * 0.95))] if durations else 0,
        },
        "group_size_distribution": dict(sorted(Counter(s.summary["event_count"] for s in states).items())),
        "independent_source_distribution": dict(
            sorted(Counter(s.summary["independent_sources"] for s in states).items())
        ),
        "source_type_diversity_distribution": dict(
            sorted(Counter(len(s.summary["source_types"]) for s in states).items())
        ),
        "promotion_latency_ms": {
            "samples": len(promotion_times),
            "mean": sum(promotion_times) / len(promotion_times) if promotion_times else 0,
            "p95": promotion_times[min(len(promotion_times) - 1, int(len(promotion_times) * 0.95))]
            if promotion_times
            else 0,
        },
    }
