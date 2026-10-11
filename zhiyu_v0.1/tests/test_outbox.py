from datetime import timedelta

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from zhiyu.core.errors import LeaseLostError
from zhiyu.db.models import OutboxRow
from zhiyu.repositories.outbox import OutboxRepository
from zhiyu.services.event_ingest import EventIngestService

pytestmark = pytest.mark.postgres


def test_claim_transfer_rejects_old_worker_after_crash(bootstrapped, event, principal):
    with Session(bootstrapped) as db:
        EventIngestService(db).ingest([event], principal=principal)
        with db.begin():
            old = OutboxRepository(db).claim("old-worker", limit=1)[0]
    # Simulate time passing without a wall-clock sleep; old worker lost its ACK.
    with bootstrapped.begin() as connection:
        connection.execute(
            update(OutboxRow).values(lease_until=func.clock_timestamp() - timedelta(seconds=1))
        )
    with Session(bootstrapped) as db, db.begin():
        new = OutboxRepository(db).claim("replacement", limit=1)[0]
        assert new.message.message_id == old.message.message_id
        assert new.generation == old.generation + 1
    with Session(bootstrapped) as db, pytest.raises(LeaseLostError), db.begin():
        OutboxRepository(db).finish(old, published=True)
    with Session(bootstrapped) as db, db.begin():
        OutboxRepository(db).finish(new, published=True)
    with Session(bootstrapped) as db, db.begin():
        assert OutboxRepository(db).claim("third") == []
        row = db.scalars(select(OutboxRow)).one()
        assert row.published_at is not None and row.attempt_count == 2


def test_skip_locked_and_retry_budget(bootstrapped, event, principal):
    other = event.model_copy(update={"event_id": "evt-other", "origin_event_id": "origin-other"})
    with Session(bootstrapped) as db:
        EventIngestService(db).ingest([event, other], principal=principal)
    with Session(bootstrapped) as first, first.begin():
        claim_a = OutboxRepository(first).claim("worker-a", limit=1)[0]
        with Session(bootstrapped) as second, second.begin():
            claim_b = OutboxRepository(second).claim("worker-b", limit=1)[0]
            assert claim_a.message.message_id != claim_b.message.message_id
            OutboxRepository(second).finish(
                claim_b, published=False, error_code="BROKER_TIMEOUT", retry_after_seconds=0
            )
        OutboxRepository(first).finish(claim_a, published=True)
    with Session(bootstrapped) as db, db.begin():
        assert OutboxRepository(db).claim("over-budget", max_attempts=1) == []
        retry = OutboxRepository(db).claim("retry", max_attempts=2)[0]
        OutboxRepository(db).finish(retry, published=True)


def test_expired_claim_cannot_ack_even_before_replacement(bootstrapped, event, principal):
    with Session(bootstrapped) as db:
        EventIngestService(db).ingest([event], principal=principal)
        with db.begin():
            claim = OutboxRepository(db).claim("worker")[0]
    with bootstrapped.begin() as connection:
        connection.execute(
            update(OutboxRow).values(lease_until=func.clock_timestamp() - timedelta(seconds=1))
        )
    with Session(bootstrapped) as db, pytest.raises(LeaseLostError), db.begin():
        OutboxRepository(db).finish(claim, published=True)
