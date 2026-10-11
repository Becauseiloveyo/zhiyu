"""Response byte budgets apply after allowlisting and before returning data."""

import json
from typing import TypeVar

from fastapi import HTTPException
from pydantic import BaseModel

T = TypeVar("T")


def response_budget(value: T, maximum: int = 1024 * 1024) -> T:
    body = (
        value.model_dump_json()
        if isinstance(value, BaseModel)
        else json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    )
    if len(body.encode("utf-8")) > maximum:
        raise HTTPException(413, "projection_budget_exceeded_narrow_query")
    return value
