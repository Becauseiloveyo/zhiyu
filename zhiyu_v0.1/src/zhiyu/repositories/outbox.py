"""Transactional outbox with expiring claims. Delivery is at least once.

Consumers must deduplicate message_id. No external action executor is provided here.
"""

from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from zhiyu.core.errors import ConflictError, LeaseLostError
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import OutboxRow
from zhiyu.domain.contracts import OutboxMessage


@dataclass(frozen=True)
class OutboxClaim:
    message: OutboxMessage
    generation: int
    worker_id: str


class OutboxRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def enqueue(
        self,
        *,
        environment_id: str,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload_ref: str,
    ) -> str:
        statement = insert(OutboxRow).values(
            message_id=str(uuid4()),
            environment_id=environment_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload_ref=payload_ref,
            created_at=func.clock_timestamp(),
            attempt_count=0,
        )
        message_id = self.db.execute(
            statement.on_conflict_do_nothing(
                constraint="uq_outbox_aggregate_event",
            ).returning(OutboxRow.message_id)
        ).scalar_one_or_none()
        if message_id is not None:
            return message_id
        row = self.db.scalars(
            select(OutboxRow).where(
                OutboxRow.environment_id == environment_id,
                OutboxRow.aggregate_type == aggregate_type,
                OutboxRow.aggregate_id == aggregate_id,
                OutboxRow.event_type == event_type,
            )
        ).one()
        if row.payload_ref != payload_ref:
            raise ConflictError("outbox identity reused with different payload")
        return row.message_id

    def claim(
        self, worker_id: str, *, limit: int = 20, lease_seconds: int = 30, max_attempts: int = 5
    ) -> list[OutboxClaim]:
        if (
            not worker_id
            or not 1 <= limit <= 1000
            or not 1 <= lease_seconds <= 300
            or not 1 <= max_attempts <= 100
        ):
            raise ValueError("invalid outbox claim bounds")
        rows = list(
            self.db.scalars(
                select(OutboxRow)
                .where(
                    OutboxRow.published_at.is_(None),
                    OutboxRow.available_at <= func.clock_timestamp(),
                    OutboxRow.attempt_count < max_attempts,
                    or_(OutboxRow.lease_until.is_(None), OutboxRow.lease_until <= func.clock_timestamp()),
                )
                .order_by(OutboxRow.created_at, OutboxRow.message_id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        now = self.db.scalar(select(func.clock_timestamp()))
        if now is None:
            raise RuntimeError("database clock unavailable")
        claims = []
        for row in rows:
            row.generation += 1
            row.attempt_count += 1
            row.lease_owner = worker_id
            row.lease_until = now + timedelta(seconds=lease_seconds)
            claims.append(OutboxClaim(contract_from(row, OutboxMessage), row.generation, worker_id))
        self.db.flush()
        return claims

    def finish(
        self,
        claim: OutboxClaim,
        *,
        published: bool,
        error_code: str | None = None,
        retry_after_seconds: int = 5,
    ) -> None:
        if not 0 <= retry_after_seconds <= 3600:
            raise ValueError("invalid retry interval")
        if error_code is not None and (len(error_code) > 80 or not error_code.replace("_", "").isalnum()):
            raise ValueError("use a classified error code, never a raw exception or payload")
        updated = self.db.execute(
            update(OutboxRow)
            .where(
                OutboxRow.message_id == claim.message.message_id,
                OutboxRow.generation == claim.generation,
                OutboxRow.lease_owner == claim.worker_id,
                OutboxRow.lease_until > func.clock_timestamp(),
                OutboxRow.published_at.is_(None),
            )
            .values(
                published_at=func.clock_timestamp() if published else None,
                lease_owner=None,
                lease_until=None,
                last_error_code=error_code,
                available_at=func.clock_timestamp() + timedelta(seconds=retry_after_seconds),
                row_version=OutboxRow.row_version + 1,
            )
            .returning(OutboxRow.message_id)
        ).scalar_one_or_none()
        if updated is None:
            raise LeaseLostError("outbox claim expired, transferred or already acknowledged")
