from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from zhiyu.core.errors import AccessDenied, ConflictError, ReferenceError
from zhiyu.db.infrastructure import EventReceiptRow
from zhiyu.db.models import AuditEntryRow, EnvironmentRow, EventRow, OutboxRow
from zhiyu.repositories.audit import AuditRepository
from zhiyu.repositories.events import EventRepository
from zhiyu.repositories.outbox import OutboxRepository
from zhiyu.services.event_ingest import EventIngestService

pytestmark = pytest.mark.postgres


def count(db, row):
    return db.scalar(select(func.count()).select_from(row))


def test_duplicate_preserves_receipts_and_single_intent(bootstrapped, event, principal):
    retry = event.model_copy(
        update={
            "event_id": "retry-id",
            "raw_ref": "fixture://retry",
            "ingested_at": event.ingested_at + timedelta(seconds=3),
        }
    )
    with Session(bootstrapped) as db:
        result = EventIngestService(db).ingest([event, retry], principal=principal)
        assert (result.accepted, result.duplicates) == (1, 1)
        assert result.event_ids == [event.event_id, event.event_id]
        assert count(db, EventRow) == count(db, OutboxRow) == 1
        assert count(db, EventReceiptRow) == 2
        assert set(db.scalars(select(EventReceiptRow.raw_ref))) == {event.raw_ref, retry.raw_ref}
        assert AuditRepository(db).verify_chain(event.environment_id)


def test_forwarded_provenance_is_preserved(bootstrapped, event, principal):
    forwarded = event.model_copy(
        update={
            "event_id": "forwarded",
            "collector_id": "sensor-wazuh",
            "source_type": "wazuh_forwarded_suricata",
        }
    )
    independent = event.model_copy(
        update={
            "event_id": "independent",
            "origin_event_id": "app-1",
            "collector_id": "sensor-wazuh",
            "source_type": "wazuh_application_log",
            "provenance_group": "application-1",
        }
    )
    with Session(bootstrapped) as db:
        result = EventIngestService(db).ingest([event, forwarded, independent], principal=principal)
        assert result.accepted == 3 and result.duplicates == 0
        assert count(db, EventRow) == 3


@pytest.mark.parametrize(
    "mutation",
    [
        {"severity_signal": 8},
        {"source_timestamp": "shift"},
        {"origin_event_id": "changed"},
    ],
)
def test_identity_mutation_rejects_whole_batch(bootstrapped, event, principal, mutation):
    if mutation.get("source_timestamp") == "shift":
        mutation = {"source_timestamp": event.source_timestamp + timedelta(seconds=1)}
    changed = event.model_copy(update=mutation)
    with Session(bootstrapped) as db:
        with pytest.raises(ConflictError):
            EventIngestService(db).ingest([event, changed], principal=principal)
        assert count(db, EventRow) == count(db, OutboxRow) == count(db, EventReceiptRow) == 0


def test_repository_fk_violation_is_not_duplicate(pg_engine, event):
    with Session(pg_engine) as db, pytest.raises(IntegrityError):
        with db.begin():
            EventRepository(db).insert(event)


@pytest.mark.parametrize(
    "mutation,error",
    [
        ({"environment_id": "outside"}, AccessDenied),
        ({"collector_id": "spoofed"}, AccessDenied),
        ({"source_type": "spoofed"}, AccessDenied),
        ({"target_resource_ids": ["unknown"]}, ReferenceError),
        ({"validation_run_id": "forged-true-is-not-authority"}, AccessDenied),
    ],
)
def test_ingest_fail_closed(bootstrapped, event, principal, mutation, error):
    with Session(bootstrapped) as db:
        with pytest.raises(error):
            EventIngestService(db).ingest([event, event.model_copy(update=mutation)], principal=principal)
        assert count(db, EventRow) == count(db, OutboxRow) == 0


@pytest.mark.parametrize("component", ["audit", "outbox"])
def test_durable_component_failure_rolls_back_everything(
    bootstrapped, event, principal, monkeypatch, component
):
    def fail(*args, **kwargs):
        raise RuntimeError("injected durable storage failure")

    target, method = (AuditRepository, "append") if component == "audit" else (OutboxRepository, "enqueue")
    monkeypatch.setattr(target, method, fail)
    with Session(bootstrapped) as db:
        before = count(db, AuditEntryRow)
        db.rollback()
        with pytest.raises(RuntimeError):
            EventIngestService(db).ingest([event], principal=principal)
        assert count(db, EventRow) == count(db, OutboxRow) == count(db, EventReceiptRow) == 0
        assert count(db, AuditEntryRow) == before


def test_concurrent_duplicate_has_one_canonical_event(bootstrapped, event, principal):
    barrier = Barrier(4)

    def ingest():
        with Session(bootstrapped) as db:
            barrier.wait(timeout=10)
            return EventIngestService(db).ingest([event], principal=principal)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(ingest) for _ in range(4)]
        results = [future.result(timeout=20) for future in futures]
    assert sum(r.accepted for r in results) == 1
    assert sum(r.duplicates for r in results) == 3
    with Session(bootstrapped) as db:
        assert count(db, EventRow) == count(db, OutboxRow) == 1
        assert count(db, EventReceiptRow) == 4
        assert AuditRepository(db).verify_chain(event.environment_id)


def test_connection_crash_discards_uncommitted_event_and_replay_recovers(bootstrapped, event, principal):
    with Session(bootstrapped) as db:
        EventRepository(db).insert(event)
        # Invalidation physically closes the connection without committing its transaction.
        db.invalidate()
    with Session(bootstrapped) as db:
        result = EventIngestService(db).ingest([event], principal=principal)
        assert result.accepted == 1
        assert count(db, EventRow) == count(db, OutboxRow) == 1


def test_lock_timeout_leaves_no_partial_acceptance(bootstrapped, event, principal):
    with Session(bootstrapped) as blocker:
        blocker.execute(
            select(EnvironmentRow)
            .where(EnvironmentRow.environment_id == event.environment_id)
            .with_for_update()
        )
        with bootstrapped.connect() as connection:
            connection.execute(text("SET lock_timeout = '100ms'"))
            connection.commit()
            with Session(connection) as db, pytest.raises(OperationalError):
                EventIngestService(db).ingest([event], principal=principal)
        blocker.rollback()
    with Session(bootstrapped) as db:
        assert count(db, EventRow) == count(db, OutboxRow) == 0
