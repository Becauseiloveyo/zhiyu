from dataclasses import dataclass

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash, utc
from zhiyu.core.errors import ConflictError
from zhiyu.db.infrastructure import EventResourceRow
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import EventRow
from zhiyu.domain.contracts import NormalizedEvent


def event_content_hash(event: NormalizedEvent) -> str:
    # Delivery metadata is retained in receipts, separately from stable origin identity.
    body = event.model_dump(mode="json", exclude={"event_id", "ingested_at", "raw_ref", "clock_status"})
    body["source_timestamp"] = utc(event.source_timestamp).isoformat()
    return canonical_hash(body)


@dataclass(frozen=True)
class EventInsertResult:
    event_id: str
    created: bool


class EventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def insert(self, event: NormalizedEvent) -> EventInsertResult:
        values = values_for(event, EventRow)
        values["content_hash"] = event_content_hash(event)
        event_id = self.db.execute(
            insert(EventRow).values(**values).on_conflict_do_nothing().returning(EventRow.event_id)
        ).scalar_one_or_none()
        if event_id is not None:
            for role, refs in (("SOURCE", event.source_resource_ids), ("TARGET", event.target_resource_ids)):
                for resource_id in sorted(set(refs)):
                    self.db.add(
                        EventResourceRow(
                            environment_id=event.environment_id,
                            event_id=event_id,
                            resource_id=resource_id,
                            role=role,
                        )
                    )
            self.db.flush()
            return EventInsertResult(event_id, True)
        # Only unique conflicts reach here. NOT NULL, CHECK and FK violations propagate.
        rows = list(
            self.db.scalars(
                select(EventRow).where(
                    or_(
                        EventRow.event_id == event.event_id,
                        and_(
                            EventRow.environment_id == event.environment_id,
                            EventRow.collector_id == event.collector_id,
                            EventRow.source_type == event.source_type,
                            EventRow.origin_event_id == event.origin_event_id,
                            EventRow.event_type == event.event_type,
                        ),
                    )
                )
            )
        )
        if (
            len(rows) != 1
            or rows[0].environment_id != event.environment_id
            or event_content_hash(contract_from(rows[0], NormalizedEvent)) != values["content_hash"]
        ):
            raise ConflictError("event identity reused with different content")
        return EventInsertResult(rows[0].event_id, False)
