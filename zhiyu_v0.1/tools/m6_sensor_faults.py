"""Clearly SYNTHETIC copies of real raw shapes for clock/reorder/dedup fault cases."""

import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from m6_sensor_ingest import source_lines
from response_fixture import prepare
from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.core.config import settings
from zhiyu.db.intelligence import GroupStateRow
from zhiyu.db.models import EventGroupRow, EventRow
from zhiyu.db.session import get_engine
from zhiyu.repositories.audit import AuditRepository
from zhiyu.services.event_intelligence import EventIntelligenceEngine
from zhiyu.services.raw_ingest import RawIngestService, RawInput


def main():
    engine, env = get_engine(), "m3-m6-sensor-faults"
    principal = next(p for p in settings.service_tokens.values() if p.principal_id == "compose-smoke")
    root = Path("/fault-control/sensor-faults")
    root.mkdir(exist_ok=False)
    capture = Path("docs/m6-runtime/sensor-008")
    originals = {
        name: hashlib.sha256((capture / name).read_bytes()).hexdigest()
        for name in ["eve.json", "alerts.json"]
    }
    prepare(engine, env, principal, target=sys.argv[1], source=sys.argv[2], port=8081, seed=False)
    now = datetime.now(UTC)
    base = now.replace(second=0, microsecond=0) - timedelta(seconds=5)
    records = {}
    for source, lines in source_lines(capture).items():
        selected = []
        for _, payload in lines:
            value = json.loads(payload)
            if source == "suricata" and (
                value.get("event_type") != "http" or value["http"].get("status") != 401
            ):
                continue
            if source == "wazuh" and str(value["rule"]["id"]) != "110001":
                continue
            value["timestamp"] = (base + timedelta(milliseconds=100 * len(selected))).isoformat()
            selected.append(value)
        assert len(selected) == 4
        records[source] = selected
    inputs, receipts = [], []

    def ingest(source, values, prefix):
        rows = [
            RawInput(json.dumps(value), "m6-synthetic-" + prefix + "-" + source + "-" + str(index))
            for index, value in enumerate(values)
        ]
        inputs.append(
            {
                "source": source,
                "data_origin": "SYNTHETIC",
                "prefix": prefix,
                "records": [r.__dict__ for r in rows],
            }
        )
        with Session(engine) as db:
            receipt = RawIngestService(db).ingest(
                list(reversed(rows)),
                environment_id=env,
                collector_id="sensor-" + source,
                source_type=source,
                principal=principal,
                data_origin="SYNTHETIC",
            )
        receipts.append(receipt)
        assert receipt["errors"] == 0
        return receipt

    try:
        for source, values in records.items():
            assert ingest(source, values, "reorder")["accepted"] == 4
            with Session(engine) as db:
                EventIntelligenceEngine(db).process(env, principal=principal)
        with Session(engine) as db:
            group = db.scalars(select(EventGroupRow).where(EventGroupRow.environment_id == env)).one()
            assert len(group.member_event_ids) == 8
            assert group.first_seen_at == base
            group_id = group.group_id
        for source, values in records.items():
            replay = ingest(source, values, "reorder")
            assert replay["accepted"] == 0 and replay["duplicates"] == 4
        for name, offset in [("future", timedelta(hours=1)), ("expired", -timedelta(days=2))]:
            value = {**records["suricata"][0], "timestamp": (now + offset).isoformat()}
            assert ingest("suricata", [value], name)["accepted"] == 1
        with Session(engine) as db:
            EventIntelligenceEngine(db).process(env, principal=principal)
        with Session(engine) as db:
            states = list(db.scalars(select(GroupStateRow).where(GroupStateRow.environment_id == env)))
            assert {s.disposition for s in states} == {"TIMELY", "FUTURE", "EXPIRED"}
            assert len(db.get(EventGroupRow, group_id).member_event_ids) == 8
            assert all(
                len(db.get(EventGroupRow, s.group_id).member_event_ids) == 1
                for s in states
                if s.disposition != "TIMELY"
            )
            events = list(db.scalars(select(EventRow).where(EventRow.environment_id == env)))
            assert len(events) == 10 and all(e.data_origin == "SYNTHETIC" for e in events)
            assert AuditRepository(db).verify_chain(env)
            result = {
                "status": "PASS",
                "data_origin": "SYNTHETIC_MUTATED_COPIES_NOT_REAL_SENSOR_ACTIVITY",
                "original_raw_sha256": originals,
                "reverse_order_cross_source_members": 8,
                "duplicate_deliveries": 8,
                "groups": [
                    {"id": s.group_id, "disposition": s.disposition, "summary": s.summary} for s in states
                ],
                "originals_unchanged": all(
                    hashlib.sha256((capture / name).read_bytes()).hexdigest() == digest
                    for name, digest in originals.items()
                ),
                "missing_batch_evidence": "docs/m6-runtime/gate-a-002/agent-delivery-delayed",
                "audit_valid": True,
            }
        assert result["originals_unchanged"]
        (root / "result.json").write_text(json.dumps(result, default=str, indent=2))
        print(json.dumps(result, default=str))
    finally:
        (root / "synthetic-inputs.json").write_text(json.dumps(inputs, indent=2))
        (root / "receipts.json").write_text(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    main()
