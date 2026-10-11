from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from zhiyu.api.security import require_principal
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.session import get_db
from zhiyu.services.event_intelligence import EventIntelligenceEngine
from zhiyu.services.incident_engine import IncidentEngine
from zhiyu.services.intelligence_metrics import metrics

router = APIRouter(prefix="/v1/intelligence", tags=["intelligence"])


class ProcessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment_id: str = Field(min_length=1)
    limit: int = Field(default=1000, ge=1, le=1000)


@router.post("/process")
def process_events(
    request: ProcessRequest,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    correlation = EventIntelligenceEngine(db).process(
        request.environment_id, principal=principal, limit=request.limit
    )
    incidents = IncidentEngine(db).promote(request.environment_id, principal=principal, limit=request.limit)
    return {"correlation": correlation, "incidents": incidents}


@router.get("/metrics")
def read_metrics(
    environment_id: str = Query(min_length=1),
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return metrics(db, environment_id, principal)
