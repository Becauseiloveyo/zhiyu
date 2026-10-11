from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from typing import Any, Literal

from pydantic import ValidationError

from zhiyu.core.canonical import canonical_hash
from zhiyu.domain.contracts import NormalizedEvent, Observable

ERROR_CODES = frozenset(
    {
        "malformed_json",
        "missing_required_identity",
        "unsupported_event_type",
        "invalid_timestamp",
        "invalid_ip",
        "invalid_protocol",
        "mapping_error",
        "contract_validation_error",
    }
)
MAPPING_VERSION = "sensor-map/1.0.0"
PARSER_VERSION = "sensor-json/1.0.0"
SURICATA_SEVERITY = {1: 9, 2: 6, 3: 3, 4: 1}
WAZUH_SEVERITY = {level: round(level * 10 / 15) for level in range(16)}


class AdapterError(ValueError):
    def __init__(self, code: str, field: str) -> None:
        if code not in ERROR_CODES:
            raise ValueError("unregistered adapter error")
        self.code, self.field = code, field
        super().__init__(f"{code}: {field}")


@dataclass(frozen=True)
class AdapterContext:
    environment_id: str
    collector_id: str
    source_type: str
    ingested_at: datetime
    raw_ref: str
    provenance_root: str
    data_origin: Literal["SYNTHETIC", "OBSERVED"] = "OBSERVED"
    origin_event_id: str | None = None
    # Governed resource locator matches, never resource IDs claimed by a vendor.
    resource_by_ip: dict[str, str] = dataclass_field(default_factory=dict)
    resource_by_endpoint: dict[tuple[str, int, str], str] = dataclass_field(default_factory=dict)


def object_field(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name, {})
    if not isinstance(value, dict):
        raise AdapterError("mapping_error", name)
    return value


def timestamp(value: Any, ingested_at: datetime) -> tuple[datetime, str]:
    if not isinstance(value, str):
        raise AdapterError("invalid_timestamp", "timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdapterError("invalid_timestamp", "timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AdapterError("invalid_timestamp", "timestamp.timezone_required")
    parsed = parsed.astimezone(UTC)
    delta = parsed - ingested_at
    clock = "SKEWED" if delta > timedelta(minutes=5) or delta < -timedelta(hours=24) else "TRUSTED"
    return parsed, clock


def severity(value: Any, table: dict[int, int]) -> int:
    # Unknown values have explicit fallback 0; do not turn malformed levels into high risk.
    if isinstance(value, bool):
        return 0
    try:
        key = int(str(value))
    except (ValueError, TypeError):
        return 0
    return table.get(key, 0)


class Facts:
    def __init__(self) -> None:
        self.items: list[Observable] = []

    def add(self, kind: str, value: Any, role: str = "RELATED") -> None:
        if value is None or value == "":
            return
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            raise AdapterError("mapping_error", f"observable.{kind}")
        text = str(value)
        if len(text) > 4096 or "\x00" in text:
            raise AdapterError("mapping_error", "observable.too_long")
        if kind == "IP":
            try:
                text = str(ip_address(text))
            except ValueError as exc:
                raise AdapterError("invalid_ip", role.lower()) from exc
        self.items.append(Observable.model_validate({"observable_type": kind, "value": text, "role": role}))

    def meta(self, name: str, value: Any, role: str = "RELATED") -> None:
        if name == "vendor.severity" and isinstance(value, (bool, float)):
            value = str(value).lower()
        if value is not None and value != "":
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise AdapterError("mapping_error", name)
            self.add("OTHER", f"{name}={value}", role)

    def network(self, raw: dict[str, Any]) -> None:
        for field, role in (("src_ip", "SOURCE"), ("dest_ip", "TARGET")):
            self.add("IP", raw.get(field), role)
        for field, role in (("src_port", "SOURCE"), ("dest_port", "TARGET")):
            value = raw.get(field)
            if value is not None:
                try:
                    port = int(str(value))
                except ValueError as exc:
                    raise AdapterError("invalid_protocol", field) from exc
                if not 0 <= port <= 65535:
                    raise AdapterError("invalid_protocol", field)
                self.meta("port", port, role)
        proto = raw.get("proto")
        if proto is not None:
            if not isinstance(proto, str) or proto.upper() not in {
                "TCP",
                "UDP",
                "ICMP",
                "ICMPV6",
                "SCTP",
                "GRE",
                "ESP",
                "AH",
                "IPV6-ICMP",
            }:
                raise AdapterError("invalid_protocol", "proto")
            self.meta("transport", proto.upper())
        self.meta("application_protocol", raw.get("app_proto"))


def build_event(
    raw: dict[str, Any],
    ctx: AdapterContext,
    facts: Facts,
    *,
    event_type: str,
    category: str,
    action: str,
    outcome: str,
    level: int,
    mapping_version: str = MAPPING_VERSION,
) -> NormalizedEvent:
    if not all((ctx.environment_id, ctx.collector_id, ctx.source_type, ctx.provenance_root)):
        raise AdapterError("missing_required_identity", "collector_context")
    time, clock = timestamp(raw.get("timestamp"), ctx.ingested_at)
    origin = ctx.origin_event_id or raw.get("id") or ("sha256:" + canonical_hash(raw))
    if not isinstance(origin, str) or not origin.strip() or "\x00" in origin:
        raise AdapterError("missing_required_identity", "origin_event_id")
    facts.items = sorted(set_facts(facts.items), key=lambda x: (x.role, x.observable_type, x.value))
    identity = [ctx.environment_id, ctx.collector_id, ctx.source_type, origin, event_type]
    refs = {
        role: sorted(
            {
                ctx.resource_by_ip[x.value]
                for x in facts.items
                if x.role == role and x.observable_type == "IP" and x.value in ctx.resource_by_ip
            }
        )
        for role in ("SOURCE", "TARGET")
    }
    transports = [x.value.removeprefix("transport=") for x in facts.items if x.value.startswith("transport=")]
    for role in ("SOURCE", "TARGET"):
        ports = [
            int(x.value.removeprefix("port="))
            for x in facts.items
            if x.role == role and x.value.startswith("port=")
        ]
        endpoints = {
            ctx.resource_by_endpoint[(x.value, port, transport)]
            for x in facts.items
            if x.observable_type == "IP" and x.role == role
            for port in ports
            for transport in transports
            if (x.value, port, transport) in ctx.resource_by_endpoint
        }
        refs[role] = sorted(set(refs[role]) | endpoints)
    body = dict(
        event_id="evt-" + canonical_hash(identity),
        environment_id=ctx.environment_id,
        source_type=ctx.source_type,
        collector_id=ctx.collector_id,
        origin_event_id=origin,
        provenance_group=ctx.provenance_root,
        source_timestamp=time,
        ingested_at=ctx.ingested_at,
        clock_status=clock,
        event_type=event_type,
        activity_category=category,
        activity_name=action,
        outcome=outcome,
        source_resource_ids=refs["SOURCE"],
        target_resource_ids=refs["TARGET"],
        observables=facts.items,
        severity_signal=level,
        raw_ref=ctx.raw_ref,
        parser_version=PARSER_VERSION,
        mapping_version=mapping_version,
        fingerprint=canonical_hash([category, action, outcome, [x.model_dump() for x in facts.items]]),
        validation_run_id=None,
        data_origin=ctx.data_origin,
    )
    try:
        if any(isinstance(value, str) and "\x00" in value for value in body.values()):
            raise AdapterError("mapping_error", "nul_in_mapped_field")
        return NormalizedEvent.model_validate(body)
    except ValidationError as exc:
        raise AdapterError("contract_validation_error", "NormalizedEvent") from exc


def set_facts(items: list[Observable]) -> list[Observable]:
    return list({(x.observable_type, x.role, x.value): x for x in items}.values())
