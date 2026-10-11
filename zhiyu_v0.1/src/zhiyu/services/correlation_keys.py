import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.intelligence_config import IntelligenceConfig
from zhiyu.domain.contracts import NormalizedEvent


def observable_values(event: NormalizedEvent, kind: str, role: str) -> list[str]:
    return sorted({x.value for x in event.observables if x.observable_type == kind and x.role == role})


def metadata_values(event: NormalizedEvent, prefix: str, role: str | None = None) -> list[str]:
    return sorted(
        {
            x.value[len(prefix) :]
            for x in event.observables
            if x.observable_type == "OTHER"
            and x.value.startswith(prefix)
            and (role is None or x.role == role)
        }
    )


@dataclass(frozen=True)
class CorrelationKey:
    digest: str
    dimensions: dict[str, str]
    window_start: datetime
    window_end: datetime
    disposition: str
    confidence: float


class CorrelationKeyBuilder:
    def __init__(self, config: IntelligenceConfig) -> None:
        self.config = config

    def build(self, event: NormalizedEvent) -> CorrelationKey:
        interval = self.config.window(event.activity_category)
        start = datetime.fromtimestamp(int(event.source_timestamp.timestamp()) // interval * interval, UTC)
        end = start + timedelta(seconds=interval)
        source = observable_values(event, "IP", "SOURCE") or event.source_resource_ids
        target = observable_values(event, "IP", "TARGET") or event.target_resource_ids
        user = observable_values(event, "USER", "SOURCE")
        dimensions = {
            "environment": event.environment_id,
            "source": json.dumps(sorted(source)),
            "user": json.dumps(user),
            "actor_resource": event.actor_resource_id or "",
            "target": json.dumps(sorted(target)),
            "service": json.dumps(metadata_values(event, "port=", "TARGET")),
            "transport": json.dumps(metadata_values(event, "transport=")),
            "activity": event.activity_category,
            "action": event.activity_name,
            "outcome": event.outcome,
            "validation": event.validation_run_id or "unregistered",
            "data_origin": event.data_origin,
            "key_version": self.config.key_version,
            "config_hash": canonical_hash(self.config.model_dump()),
            "rule_version": self.config.rule_version,
        }
        # Cross-vendor joins are deliberately limited to explicit authentication facts.
        if event.activity_category != "authentication":
            dimensions["vendor_rule"] = json.dumps(
                [
                    event.source_type,
                    metadata_values(event, "vendor.rule_id="),
                    metadata_values(event, "vendor.signature_id="),
                ]
            )
        disposition = "TIMELY"
        delay = (event.ingested_at - event.source_timestamp).total_seconds()
        if delay > self.config.expired_after_seconds:
            disposition = "EXPIRED"
        elif delay < -self.config.maximum_future_seconds:
            disposition = "FUTURE"
        elif event.ingested_at > end + timedelta(seconds=self.config.allowed_lateness_seconds):
            disposition = "LATE"
        # Missing source/target cannot provide a safe generic join key.
        if not source or not target or disposition != "TIMELY":
            dimensions["isolation_event"] = event.event_id
        dimensions["window_start"] = start.isoformat()
        dimensions["disposition"] = disposition
        coverage = (bool(source) + bool(target) + bool(user) + bool(dimensions["activity"])) / 4
        return CorrelationKey(canonical_hash(dimensions), dimensions, start, end, disposition, coverage)
