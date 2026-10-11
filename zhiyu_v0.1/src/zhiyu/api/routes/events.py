from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from zhiyu.api.security import require_principal
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.session import get_db
from zhiyu.domain.contracts import NormalizedEvent
from zhiyu.services.event_ingest import BatchInsertResult, EventIngestService
from zhiyu.services.raw_ingest import RawIngestService, RawInput

router = APIRouter(prefix="/v1/events", tags=["events"])


class EventBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[NormalizedEvent] = Field(min_length=1, max_length=1000)


@router.post("/batches", status_code=status.HTTP_202_ACCEPTED)
def ingest_batch(
    batch: EventBatch, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> BatchInsertResult:
    return EventIngestService(db).ingest(batch.events, principal=principal)


class RawRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record: str = Field(max_length=262144)
    origin_event_id: str | None = Field(default=None, min_length=1, max_length=1024)


class RawBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment_id: str = Field(min_length=1)
    collector_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    data_origin: Literal["SYNTHETIC", "OBSERVED"] = "OBSERVED"
    records: list[RawRecord] = Field(min_length=1, max_length=1000)


@router.post("/raw-batches", status_code=status.HTTP_202_ACCEPTED)
def ingest_raw_batch(
    batch: RawBatch, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> dict:
    return RawIngestService(db).ingest(
        [RawInput(**x.model_dump()) for x in batch.records],
        environment_id=batch.environment_id,
        collector_id=batch.collector_id,
        source_type=batch.source_type,
        data_origin=batch.data_origin,
        principal=principal,
    )
