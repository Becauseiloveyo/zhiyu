import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from conftest import migration_config
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_adapters import raw

from zhiyu.core.errors import AccessDenied
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.infrastructure import RawDeliveryRow, RawRecordRow
from zhiyu.db.models import AuditEntryRow, EventRow, OutboxRow
from zhiyu.repositories.audit import AuditRepository
from zhiyu.services.event_ingest import EventIngestService
from zhiyu.services.raw_ingest import RawIngestService, RawInput

pytestmark = pytest.mark.postgres


def sensor_principal():
    return ServicePrincipal(
        principal_id="sensor-tests",
        environment_ids={"lab-zhiyu-01"},
        collector_ids={"sensor-suricata", "sensor-wazuh"},
        source_types={"suricata", "wazuh"},
        permissions={
            "events:write",
            "events:synthetic",
            "incidents:read",
            "intelligence:write",
            "incidents:write",
        },
    )


def ingest(engine, inputs, source="suricata", principal=None):
    with Session(engine) as db:
        return RawIngestService(db).ingest(
            [RawInput(x) for x in inputs],
            environment_id="lab-zhiyu-01",
            collector_id="sensor-" + source,
            source_type=source,
            data_origin="SYNTHETIC",
            principal=principal or sensor_principal(),
        )


def test_mixed_records_raw_integrity_and_atomic_audit(bootstrapped):
    good = json.dumps(raw())
    records = [good, "{bad", good, "nul\x00byte", json.dumps({**raw(), "proto": "bad"})]
    result = ingest(bootstrapped, records)
    assert (result["accepted"], result["duplicates"], result["errors"]) == (1, 1, 3)
    assert [x["error_code"] for x in result["results"]] == [
        None,
        "malformed_json",
        None,
        "malformed_json",
        "invalid_protocol",
    ]
    with Session(bootstrapped) as db:
        assert db.scalar(select(func.count()).select_from(RawDeliveryRow)) == 5
        assert db.scalar(select(func.count()).select_from(EventRow)) == 1
        assert db.scalar(select(func.count()).select_from(OutboxRow)) == 1
        for row in db.scalars(select(RawRecordRow)):
            assert hashlib.sha256(row.content).hexdigest() == row.integrity_hash
            assert row.content.decode("utf-8") in records
        assert AuditRepository(db).verify_chain("lab-zhiyu-01")
        assert db.scalar(
            select(AuditEntryRow).where(AuditEntryRow.object_kind == "RawBatch")
        ).reason.endswith("errors=3")
        txids = {
            db.scalar(text("SELECT xmin::text FROM " + table + " LIMIT 1"))
            for table in ("raw_records", "raw_deliveries", "normalized_events", "outbox")
        }
        # Raw result and event live in one outer transaction; savepoint xmin may differ.
        assert None not in txids


def test_identity_conflict_is_one_record_error(bootstrapped):
    first = raw("wazuh", "ssh")
    changed = {**first, "timestamp": "2026-09-13T10:00:02Z"}
    result = ingest(
        bootstrapped, [json.dumps(first), json.dumps(changed), json.dumps(raw("wazuh", "generic"))], "wazuh"
    )
    assert (result["accepted"], result["errors"]) == (2, 1)
    assert result["results"][1]["error_field"] == "identity_conflict"


def test_raw_storage_rolls_back_on_infrastructure_failure(bootstrapped, monkeypatch):
    original = AuditRepository.append

    def fail_batch(self, **kwargs):
        if kwargs["object_kind"] == "RawBatch":
            raise RuntimeError("synthetic crash before commit")
        return original(self, **kwargs)

    monkeypatch.setattr(AuditRepository, "append", fail_batch)
    with pytest.raises(RuntimeError, match="synthetic crash"):
        ingest(bootstrapped, [json.dumps(raw())])
    with Session(bootstrapped) as db:
        for row in (RawRecordRow, RawDeliveryRow, EventRow, OutboxRow):
            assert db.scalar(select(func.count()).select_from(row)) == 0
    monkeypatch.setattr(AuditRepository, "append", original)
    assert ingest(bootstrapped, [json.dumps(raw())])["accepted"] == 1


def test_raw_authorization_and_concurrent_replay(bootstrapped):
    denied = sensor_principal().model_copy(update={"environment_ids": frozenset({"other"})})
    with pytest.raises(AccessDenied):
        ingest(bootstrapped, [json.dumps(raw())], principal=denied)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: ingest(bootstrapped, [json.dumps(raw())]), range(2)))
    assert sum(x["accepted"] for x in results) == 1
    assert sum(x["duplicates"] for x in results) == 1


def test_m1_data_survives_upgrade_and_delivery_clock_change(pg_engine, bundle, event, principal):
    from zhiyu.services.bootstrap import BootstrapService

    with pg_engine.begin() as connection:
        command.downgrade(migration_config(connection), "0001_m1_1")
    with Session(pg_engine) as db:
        BootstrapService(db).apply(bundle, actor_id="legacy-bootstrap")
        EventIngestService(db).ingest([event], principal=principal)
    with pg_engine.begin() as connection:
        before = connection.scalar(text("SELECT row_to_json(e)::text FROM normalized_events e"))
        command.upgrade(migration_config(connection), "head")
        assert connection.scalar(text("SELECT row_to_json(e)::text FROM normalized_events e")) == before
    with Session(pg_engine) as db:
        replay = event.model_copy(update={"clock_status": "SKEWED"})
        assert EventIngestService(db).ingest([replay], principal=principal).duplicates == 1
