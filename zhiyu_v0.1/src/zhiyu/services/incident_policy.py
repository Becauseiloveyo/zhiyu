from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.incident_config import IncidentConfig
from zhiyu.db.intelligence import GroupStateRow
from zhiyu.db.models import EnvironmentRow
from zhiyu.domain.contracts import EventGroup, NormalizedEvent


@dataclass(frozen=True)
class RiskAssessment:
    score: int
    priority: Literal["P0", "P1", "P2", "P3", "P4"]
    factors: dict[str, Any]


class IncidentRiskCalculator:
    def __init__(self, config: IncidentConfig) -> None:
        self.config = config

    def calculate(
        self, events: list[NormalizedEvent], *, verified_count: int, validation: bool
    ) -> RiskAssessment:
        roots = {event.provenance_group for event in events}
        assets = {
            f"{event.environment_id}/{asset}" for event in events for asset in event.target_resource_ids
        }
        criticality = max(
            (
                self.config.asset_criticality.get(asset, self.config.default_asset_criticality)
                for asset in assets
            ),
            default=0,
        )
        if not 0 <= criticality <= 5:
            raise ValueError("configured asset criticality must be 0..5")
        categories = {event.activity_category for event in events}
        weights = {"authentication": 10, "network_alert": 8, "security_alert": 8, "process": 6, "web": 4}
        components = {
            "severity": max(event.severity_signal for event in events) * self.config.severity_weight,
            "independent_sources": min(max(len(roots) - 1, 0), 3) * self.config.independence_weight,
            "asset_criticality": criticality * self.config.criticality_weight,
            "repeated_behavior": min(len(events) - 1, 10) * self.config.repetition_weight,
            "activity": max(weights.get(category, 0) for category in categories),
            "evidence_quality": round(verified_count / len(events) * self.config.evidence_weight),
            "validation_context": -self.config.validation_reduction if validation else 0,
        }
        score = min(100, max(0, sum(components.values())))
        priority = next(
            priority
            for threshold, priority in ((85, "P0"), (65, "P1"), (45, "P2"), (20, "P3"), (0, "P4"))
            if score >= threshold
        )
        return RiskAssessment(
            score,
            cast(Literal["P0", "P1", "P2", "P3", "P4"], priority),
            {
                "calculator_version": self.config.risk_version,
                "components": components,
                "event_count": len(events),
                "independent_source_count": len(roots),
                "asset_criticality": criticality,
                "verified_raw_count": verified_count,
                "semantics": "deterministic weighted evidence factors; not an AI probability",
            },
        )


class IncidentPromotionPolicy:
    def __init__(self, config: IncidentConfig) -> None:
        self.config = config

    def evaluate(
        self,
        group: EventGroup,
        state: GroupStateRow,
        events: list[NormalizedEvent],
        risk: RiskAssessment,
        environment: EnvironmentRow,
        now: datetime,
    ) -> tuple[bool, list[str]]:
        reasons = []
        if state.disposition != "TIMELY":
            reasons.append("non_timely_group")
        if group.first_seen_at > now:
            reasons.append("source_time_in_future")
        if (now - group.last_seen_at).total_seconds() > self.config.evidence_ttl_seconds:
            reasons.append("expired_evidence")
        if any(event.validation_run_id for event in events):
            reasons.append("registered_validation_context")
        if environment.deployment_stage == "PRODUCTION" and any(e.data_origin == "SYNTHETIC" for e in events):
            reasons.append("synthetic_in_production")
        if not any(event.target_resource_ids for event in events):
            reasons.append("target_not_bound_to_resource")
        if risk.score < self.config.promotion_score:
            reasons.append("risk_below_threshold")
        maximum = max(event.severity_signal for event in events)
        security_activity = group.grouping_keys["activity"] in {
            "authentication",
            "network_alert",
            "security_alert",
            "process",
        }
        supported_pattern = (
            maximum >= 9
            or (len(events) >= 3 and risk.factors["independent_source_count"] >= 2)
            or (len(events) >= 5 and maximum >= 5)
        )
        if not security_activity or not supported_pattern:
            reasons.append("insufficient_security_pattern")
        if environment.asset_domain in {"OT", "MIXED"} and risk.factors["independent_source_count"] < 2:
            reasons.append("ot_profile_requires_corroboration")
        return not reasons, reasons or ["security_pattern_and_risk_threshold_met"]

    def merge_key(self, group: EventGroup) -> str:
        return canonical_hash(
            {
                key: value
                for key, value in group.grouping_keys.items()
                if key not in {"window_start", "disposition", "isolation_event", "closed_window_group"}
            }
        )
