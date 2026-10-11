from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import AccessDenied, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.infrastructure import EventReceiptRow
from zhiyu.db.models import EnvironmentRow, ResourceRow, ScopeRow, ValidationRunRow
from zhiyu.domain.contracts import NormalizedEvent
from zhiyu.repositories.audit import AuditRepository
from zhiyu.repositories.events import EventRepository
from zhiyu.repositories.outbox import OutboxRepository


@dataclass(frozen=True)
class BatchInsertResult:
    accepted: int
    duplicates: int
    trace_id: str
    event_ids: list[str]


class EventIngestService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest(
        self, events: list[NormalizedEvent], *, principal: ServicePrincipal, nested: bool = False
    ) -> BatchInsertResult:
        if not 1 <= len(events) <= 1000:
            raise ValueError("batch must contain 1..1000 events")
        checked = [NormalizedEvent.model_validate(event.model_dump()) for event in events]
        for event in checked:
            principal.require("events:write", event.environment_id)
            if (
                event.collector_id not in principal.collector_ids
                or event.source_type not in principal.source_types
            ):
                raise AccessDenied("collector/source identity not registered to principal")
        trace_id = str(uuid4())
        results: dict[int, str] = {}
        accepted = duplicates = 0
        with self.db.begin_nested() if nested else self.db.begin():
            # Bounded M1 transactions serialize per environment, including resource bindings/audit.
            environment_ids = sorted({e.environment_id for e in checked})
            for environment_id in environment_ids:
                env = self.db.scalar(
                    select(EnvironmentRow)
                    .where(
                        EnvironmentRow.environment_id == environment_id,
                    )
                    .with_for_update()
                )
                if env is None:
                    raise ReferenceError("event environment is not bootstrapped")
            repo = EventRepository(self.db)
            outbox = OutboxRepository(self.db)
            per_environment = {env: [0, 0] for env in environment_ids}
            for index, event in sorted(enumerate(checked), key=lambda item: item[1].event_id):
                self._validate_references(event)
                result = repo.insert(event)
                results[index] = result.event_id
                if result.created:
                    accepted += 1
                    per_environment[event.environment_id][0] += 1
                    outbox.enqueue(
                        environment_id=event.environment_id,
                        aggregate_type="NormalizedEvent",
                        aggregate_id=result.event_id,
                        event_type="EventIngested",
                        payload_ref=f"db://normalized_events/{result.event_id}",
                    )
                else:
                    duplicates += 1
                    per_environment[event.environment_id][1] += 1
                self.db.add(
                    EventReceiptRow(
                        receipt_id=str(uuid4()),
                        environment_id=event.environment_id,
                        event_id=result.event_id,
                        submitted_event_id=event.event_id,
                        trace_id=trace_id,
                        raw_ref=event.raw_ref,
                        received_at=datetime.now(UTC),
                        submission_hash=canonical_hash(event.model_dump(mode="json")),
                        disposition="ACCEPTED" if result.created else "DUPLICATE",
                    )
                )
            for environment_id, (new_count, duplicate_count) in per_environment.items():
                AuditRepository(self.db).append(
                    environment_id=environment_id,
                    trace_id=trace_id,
                    actor_id=principal.principal_id,
                    object_kind="EventBatch",
                    object_id=trace_id,
                    operation="INGEST",
                    reason=f"accepted={new_count};duplicates={duplicate_count};receipts_trace={trace_id}",
                )
            self.db.flush()
        return BatchInsertResult(accepted, duplicates, trace_id, [results[i] for i in range(len(checked))])

    def _validate_references(self, event: NormalizedEvent) -> None:
        refs = set(event.source_resource_ids + event.target_resource_ids)
        if event.actor_resource_id:
            refs.add(event.actor_resource_id)
        if refs:
            found = set(
                self.db.scalars(
                    select(ResourceRow.resource_id).where(
                        ResourceRow.environment_id == event.environment_id,
                        ResourceRow.resource_id.in_(refs),
                    )
                )
            )
            if found != refs:
                raise ReferenceError("event contains unknown resource references")
        if event.validation_run_id:
            run = self.db.scalar(
                select(ValidationRunRow).where(
                    ValidationRunRow.environment_id == event.environment_id,
                    ValidationRunRow.run_id == event.validation_run_id,
                )
            )
            if run is None or not run.trusted_registration:
                raise AccessDenied("unregistered validation label")
            scope = self.db.get(ScopeRow, {"environment_id": event.environment_id, "scope_id": run.scope_id})
            if (
                scope is None
                or not run.started_at <= event.source_timestamp < run.expires_at
                or not scope.valid_from <= event.source_timestamp < scope.valid_until
                or event.event_type not in run.expected_event_types
                or event.data_origin != run.data_origin
                or not event.source_resource_ids
                or not event.target_resource_ids
                or not set(event.source_resource_ids) <= set(scope.source_resource_ids)
                or not set(event.target_resource_ids) <= set(scope.target_resource_ids)
            ):
                raise AccessDenied("validation label exceeds registered run bounds")
