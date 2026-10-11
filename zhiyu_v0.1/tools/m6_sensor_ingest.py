"""Real Lab ingest and byte-level lineage evidence; no fabricated sensor records."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from m6_jsonl import complete_records
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.infrastructure import RawRecordRow
from zhiyu.db.models import EventRow
from zhiyu.db.session import get_engine
from zhiyu.repositories.audit import AuditRepository
from zhiyu.response.catalog import INPUTS
from zhiyu.services.bootstrap import BootstrapBundle, BootstrapService
from zhiyu.services.event_intelligence import EventIntelligenceEngine
from zhiyu.services.incident_engine import IncidentEngine
from zhiyu.services.raw_ingest import RawIngestService, RawInput

ROOT = Path(__file__).resolve().parents[1]


def principal(environment, manifest):
    return ServicePrincipal(
        principal_id="m6-real-sensor-collector",
        environment_ids={environment},
        collector_ids={"sensor-suricata", "sensor-wazuh"},
        source_types={"suricata", "wazuh"},
        permissions={"events:write", "intelligence:write", "incidents:read"},
        provenance_roots={
            "sensor-suricata/suricata": "suricata/" + manifest["containers"]["suricata"]["id"],
            "sensor-wazuh/wazuh": "wazuh-agent/" + manifest["containers"]["wazuh-agent"]["id"],
        },
    )


def prepare(engine, environment):
    now = datetime.now(UTC)
    bundle = BootstrapBundle.model_validate_json((ROOT / "config/bootstrap.lab.json").read_text())
    bundle.environment.environment_id = environment
    bundle.environment.owner_id = "CONTROLLED-REAL-SENSOR-LAB"
    bundle.environment.capability_allowlist = list(INPUTS)
    for resource in bundle.resources:
        resource.environment_id = environment
        if resource.resource_id == "target-a":
            resource.locator = {"address": "10.89.60.10", "port": 8080, "protocol": "TCP"}
            resource.display_name = "Real controlled Lab login service"
        elif resource.resource_id == "validation-a":
            resource.locator = {"address": "10.89.60.30", "os": "Linux"}
        else:
            resource.locator = {"address": "10.89.60.40", "os": "Linux"}
    for scope in bundle.scopes:
        scope.environment_id = environment
        scope.allowed_capabilities = list(INPUTS)
        scope.capability_source_ids = {capability: ["validation-a"] for capability in INPUTS}
        scope.valid_from = now - timedelta(minutes=1)
        scope.valid_until = now + timedelta(hours=8)
    with Session(engine) as db:
        return BootstrapService(db).apply(bundle, actor_id="m6-real-lab-bootstrap")


def source_lines(directory):
    result = {}
    manifest = json.loads((directory / "manifest.json").read_text())
    for source, name in [("suricata", "eve.json"), ("wazuh", "alerts.json")]:
        selected = []
        for index, raw, value in complete_records((directory / name).read_bytes())[0]:
            if source == "suricata" and value.get("event_type") not in {
                "alert",
                "http",
                "dns",
                "tls",
                "flow",
            }:
                continue
            if source == "wazuh" and str(value.get("rule", {}).get("id")) not in {"110001", "110002"}:
                continue
            if (
                source == "wazuh"
                and manifest.get("request_ids")
                and value.get("data", {}).get("request_id") not in manifest["request_ids"]
            ):
                continue
            selected.append((index, raw))
        result[source] = selected
    assert all(result.values()), "Both live sensor outputs are required"
    return result


def snapshot(engine, environment):
    names = [
        "raw_records",
        "normalized_events",
        "event_groups",
        "correlation_decisions",
        "incidents",
        "evidence",
        "audit_entries",
        "outbox",
    ]
    with engine.connect() as connection:
        rows = {
            name: connection.scalars(
                text(
                    "SELECT row_to_json(r) FROM " + name + " r WHERE environment_id=:env "
                    "ORDER BY row_to_json(r)::text"
                ),
                {"env": environment},
            ).all()
            for name in names
        }
    with Session(engine) as db:
        audit_valid = AuditRepository(db).verify_chain(environment)
    return {
        "counts": {name: len(value) for name, value in rows.items()},
        "rows": rows,
        "audit_chain_valid": audit_valid,
    }


def ingest(engine, environment, directory, *, replay=False):
    manifest = json.loads((directory / "manifest.json").read_text())
    actor = principal(environment, manifest)
    if not replay:
        prepare(engine, environment)
    lines = source_lines(directory)
    expected = {}
    deliveries = {}
    for source, records in lines.items():
        with Session(engine) as db:
            result = RawIngestService(db).ingest(
                [RawInput(raw.decode("utf-8")) for _, raw in records],
                environment_id=environment,
                collector_id="sensor-" + source,
                source_type=source,
                principal=actor,
                data_origin="OBSERVED",
            )
        deliveries[source] = result
        for (line, raw), delivery in zip(records, result["results"], strict=True):
            assert delivery["error_code"] is None, delivery
            expected[delivery["event_id"]] = (source, line, raw, delivery["raw_ref"])
    with Session(engine) as db:
        grouped = EventIntelligenceEngine(db).process(environment, principal=actor)
    with Session(engine) as db:
        promoted = IncidentEngine(db).promote(environment, principal=actor)
    lineage = []
    with Session(engine) as db:
        for event in db.scalars(select(EventRow).where(EventRow.environment_id == environment)):
            source, line, raw, raw_ref = expected[event.event_id]
            stored = db.get(RawRecordRow, raw_ref.rsplit("/", 1)[1])
            assert stored.content == raw
            assert stored.integrity_hash == hashlib.sha256(raw).hexdigest()
            assert event.raw_ref == raw_ref and event.data_origin == "OBSERVED"
            assert event.provenance_group == actor.provenance_roots[f"sensor-{source}/{source}"]
            assert event.source_timestamp == datetime.fromisoformat(json.loads(raw)["timestamp"])
            lineage.append(
                {
                    "event_id": event.event_id,
                    "source": source,
                    "raw_line": line,
                    "raw_ref": raw_ref,
                    "sha256": stored.integrity_hash,
                    "origin_event_id": event.origin_event_id,
                    "provenance_group": event.provenance_group,
                    "collector_id": event.collector_id,
                    "source_timestamp": event.source_timestamp.isoformat(),
                    "ingested_at": event.ingested_at.isoformat(),
                    "parser_version": event.parser_version,
                    "mapping_version": event.mapping_version,
                }
            )
    data = snapshot(engine, environment)
    by_id = {event["event_id"]: event for event in data["rows"]["normalized_events"]}
    cross = [
        group
        for group in data["rows"]["event_groups"]
        if len({by_id[key]["source_type"] for key in group["member_event_ids"]}) > 1
    ]
    return {
        "environment_id": environment,
        "scenario": "SCN-LAB-AUTH-REAL-01",
        "data_origin": "OBSERVED",
        "replay": replay,
        "deliveries": deliveries,
        "grouped": grouped,
        "promoted": promoted,
        "lineage": lineage,
        "snapshot": data,
        "observed_event_types": dict(
            Counter(event["event_type"] for event in data["rows"]["normalized_events"])
        ),
        "cross_source_groups": cross,
        "status": "PASS"
        if cross and data["counts"]["incidents"] > 0 and data["audit_chain_valid"]
        else "FAIL",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    assert args.environment.startswith("m6-real-"), "isolated acceptance namespace only"
    print(json.dumps(ingest(get_engine(), args.environment, args.directory, replay=args.replay), default=str))


if __name__ == "__main__":
    main()
