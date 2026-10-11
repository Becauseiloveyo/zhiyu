from typing import Literal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.db.infrastructure import AuditHeadRow
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import AuditEntryRow
from zhiyu.domain.contracts import AuditEntry


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def append(
        self,
        *,
        environment_id: str,
        trace_id: str,
        actor_id: str,
        object_kind: str,
        object_id: str,
        operation: str,
        reason: str,
        actor_type: Literal["HUMAN", "SERVICE", "MODEL", "WORKER"] = "SERVICE",
    ) -> AuditEntry:
        self.db.execute(
            insert(AuditHeadRow)
            .values(environment_id=environment_id)
            .on_conflict_do_nothing(index_elements=["environment_id"])
        )
        head = self.db.scalars(
            select(AuditHeadRow)
            .where(
                AuditHeadRow.environment_id == environment_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one()
        entry = AuditEntry(
            audit_id=str(uuid4()),
            trace_id=trace_id,
            environment_id=environment_id,
            actor_type=actor_type,
            actor_id=actor_id,
            object_kind=object_kind,
            object_id=object_id,
            operation=operation,
            reason=reason,
            timestamp=self.db.execute(select(func.clock_timestamp())).scalar_one(),
            previous_entry_hash=head.integrity_hash,
            integrity_hash="0" * 64,
        )
        entry.integrity_hash = canonical_hash(entry.model_dump(mode="json", exclude={"integrity_hash"}))
        head.sequence += 1
        head.integrity_hash = entry.integrity_hash
        self.db.add(AuditEntryRow(**values_for(entry, AuditEntryRow), sequence=head.sequence))
        self.db.flush()
        return entry

    def verify_chain(self, environment_id: str) -> bool:
        # Lock the head to obtain a consistent end of chain while other writers wait.
        head = self.db.scalar(
            select(AuditHeadRow)
            .where(
                AuditHeadRow.environment_id == environment_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        previous = None
        count = 0
        for row in self.db.scalars(
            select(AuditEntryRow)
            .where(
                AuditEntryRow.environment_id == environment_id,
            )
            .order_by(AuditEntryRow.sequence)
        ):
            count += 1
            entry = contract_from(row, AuditEntry)
            digest = canonical_hash(entry.model_dump(mode="json", exclude={"integrity_hash"}))
            if (
                row.sequence != count
                or entry.previous_entry_hash != previous
                or entry.integrity_hash != digest
            ):
                return False
            previous = digest
        return head is not None and head.sequence == count and head.integrity_hash == previous
