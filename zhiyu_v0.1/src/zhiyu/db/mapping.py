"""Conversion boundary: validate contracts, store typed scalars and JSONB collections."""

from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from sqlalchemy.dialects.postgresql import JSONB

from zhiyu.core.canonical import utc
from zhiyu.db.base import Base
from zhiyu.domain.contracts import Contract

C = TypeVar("C", bound=Contract)


def values_for(contract: Contract, row_type: type[Base]) -> dict[str, Any]:
    # model_copy(update=...) bypasses Pydantic validation; always revalidate here.
    checked = type(contract).model_validate(contract.model_dump())
    native = checked.model_dump()
    portable = checked.model_dump(mode="json")
    result: dict[str, Any] = {}
    for name, value in native.items():
        if name == "object_type":
            continue
        column = row_type.__table__.c[name]
        if isinstance(column.type, JSONB):
            result[name] = portable[name]
        elif isinstance(value, datetime):
            result[name] = utc(value)
        elif isinstance(value, Enum):
            result[name] = value.value
        else:
            result[name] = value
    return result


def contract_from(row: Base, contract_type: type[C]) -> C:
    return contract_type.model_validate(
        {name: getattr(row, name) for name in contract_type.model_fields if name != "object_type"}
    )
