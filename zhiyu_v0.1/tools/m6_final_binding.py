"""Recorded acceptance procedure using installed RC source and a disposable PG schema."""

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.models import EventRow
from zhiyu.db.session import get_engine
from zhiyu.repositories.audit import AuditRepository
from zhiyu.services.bootstrap import BootstrapBundle, BootstrapService
from zhiyu.services.raw_ingest import RawIngestService, RawInput

base = get_engine()
schema = "m6_a02_" + uuid4().hex
with base.begin() as connection:
    connection.execute(CreateSchema(schema))
engine = create_engine(base.url, connect_args={"options": "-c search_path=" + schema + " -c timezone=UTC"})
report = {"status": "RUNNING", "schema": schema, "data_origin": "SYNTHETIC"}
try:
    with engine.begin() as connection:
        cfg = Config("/app/alembic.ini")
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    bundle = BootstrapBundle.model_validate_json(Path("/app/config/bootstrap.lab.json").read_text())
    with Session(engine) as db:
        BootstrapService(db).apply(bundle, actor_id="gate-e-a02")
    principal = ServicePrincipal(
        principal_id="gate-e-a02",
        environment_ids={"lab-zhiyu-01"},
        collector_ids={"sensor-suricata"},
        source_types={"suricata"},
        permissions={"events:write", "events:synthetic"},
    )
    original = json.loads(Path("/app/tests/fixtures/golden_chain_m2.json").read_text())["records"][0]["raw"]
    now = datetime.now(UTC)
    results = []

    def ingest(address, offset):
        raw = copy.deepcopy(original)
        raw.update(dest_ip=address, timestamp=(now + timedelta(seconds=offset)).isoformat())
        with Session(engine) as db:
            receipt = RawIngestService(db).ingest(
                [RawInput(json.dumps(raw), "a02-" + str(offset))],
                environment_id="lab-zhiyu-01",
                collector_id="sensor-suricata",
                source_type="suricata",
                principal=principal,
                data_origin="SYNTHETIC",
                received_at=now + timedelta(seconds=offset + 1),
            )
            assert receipt["accepted"] == 1 and receipt["errors"] == 0
        with Session(engine) as db:
            event = db.get(EventRow, receipt["results"][0]["event_id"])
            row = {
                "event_id": event.event_id,
                "address": address,
                "target_resource_ids": event.target_resource_ids,
                "source_timestamp": event.source_timestamp.isoformat(),
            }
            results.append(row)
            return row

    before = ingest("10.77.20.10", 0)
    assert before["target_resource_ids"] == ["target-a"]
    changed = bundle.resources[0].model_copy(deep=True)
    changed.locator["address"] = "10.77.20.11"
    changed.binding_version = 2
    with Session(engine) as db:
        BootstrapService(db).rebind_resource(changed, expected_version=1, actor_id="gate-e-a02")
    assert ingest("10.77.20.10", 2)["target_resource_ids"] == []
    assert ingest("10.77.20.11", 4)["target_resource_ids"] == ["target-a"]
    with Session(engine) as db:
        assert db.get(EventRow, before["event_id"]).target_resource_ids == ["target-a"]
        assert AuditRepository(db).verify_chain("lab-zhiyu-01")
        assert len(list(db.scalars(select(EventRow)))) == 3
    report.update(
        status="PASS",
        binding_versions=[1, 2],
        events=results,
        historical_event_preserved=True,
        audit_valid=True,
        external_actions=0,
        limitation="Current endpoint rebinding only; no DHCP history reconstruction or historical IP reuse claim.",
    )
finally:
    engine.dispose()
    with base.begin() as connection:
        connection.execute(DropSchema(schema, cascade=True))
    report["schema_removed"] = True
    Path("/safety-output/a02-binding-result.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
