from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from zhiyu.core.errors import ConflictError
from zhiyu.db.base import Base
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.domain.contracts import Contract

R = TypeVar("R", bound=Base)
C = TypeVar("C", bound=Contract)


class BootstrapRepository(Generic[R, C]):
    """Create or compare exactly. Caller owns the transaction and audit.

    No silent upserts of policy or resource bindings; no commit inside repositories.
    """

    row_type: type[R]
    contract_type: type[C]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, identity: str | tuple[str, ...]) -> C | None:
        if isinstance(identity, tuple):
            # Repository API uses environment first, irrespective of ORM column declaration order.
            keys = sorted(
                (col.name for col in self.row_type.__table__.primary_key),
                key=lambda name: name != "environment_id",
            )
            if len(keys) != len(identity):
                raise ValueError("incorrect composite identity length")
            row = self.db.get(self.row_type, dict(zip(keys, identity, strict=True)))
        else:
            row = self.db.get(self.row_type, identity)
        return contract_from(row, self.contract_type) if row else None

    def create(self, contract: C) -> bool:
        values = values_for(contract, self.row_type)
        table = self.row_type.__table__
        keys: Sequence[str] = [col.name for col in table.primary_key]
        created = self.db.execute(
            insert(self.row_type)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=list(keys),
            )
            .returning(*[table.c[key] for key in keys])
        ).first()
        if created:
            return True
        row = self.db.scalar(select(self.row_type).where(*[table.c[key] == values[key] for key in keys]))
        if row is None or contract_from(row, self.contract_type) != self.contract_type.model_validate(
            contract.model_dump()
        ):
            raise ConflictError("existing bootstrap identity has different configuration")
        return False
