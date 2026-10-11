from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from zhiyu.api.security import require_principal
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.incident_intelligence import IncidentAnalysisRow
from zhiyu.db.session import get_db
from zhiyu.domain.contracts import IncidentStatus, SecurityIncident
from zhiyu.services.incident_lifecycle import transition
from zhiyu.services.incident_queries import lineage_page, list_incidents, scoped_incident
from zhiyu.services.incidents import read_incident

router = APIRouter(prefix="/v1/incidents", tags=["incidents"])


@router.get("")
def list_all(
    environment_id: str = Query(min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    status: IncidentStatus | None = None,
    min_risk: int | None = Query(default=None, ge=0, le=100),
    max_risk: int | None = Query(default=None, ge=0, le=100),
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return list_incidents(
        db,
        environment_id,
        principal,
        limit=limit,
        cursor=cursor,
        status=status.value if status else None,
        min_risk=min_risk,
        max_risk=max_risk,
    )


@router.get("/{incident_id}")
def get_incident(
    incident_id: str, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> SecurityIncident:
    incident = read_incident(db, incident_id, principal)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return incident


@router.get("/{incident_id}/assessment")
def get_assessment(
    incident_id: str, principal: ServicePrincipal = Depends(require_principal), db: Session = Depends(get_db)
) -> dict[str, Any]:
    incident = scoped_incident(db, incident_id, principal)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    assessment = db.get(
        IncidentAnalysisRow, {"environment_id": incident.environment_id, "incident_id": incident_id}
    )
    return {
        "incident_id": incident_id,
        "risk": None
        if assessment is None
        else {
            "score": assessment.score,
            "priority": incident.priority,
            "factors": assessment.factors,
            "configuration": assessment.config,
            "policy_hash": assessment.policy_hash,
        },
    }


@router.get("/{incident_id}/{kind}")
def get_lineage(
    incident_id: str,
    kind: Literal["events", "correlations", "evidence"],
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    incident = scoped_incident(db, incident_id, principal)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return lineage_page(db, incident, kind, limit=limit, cursor=cursor)


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment_id: str = Field(min_length=1)
    target: Literal["TRIAGED", "INVESTIGATING"]
    expected_version: int = Field(ge=1)


@router.post("/{incident_id}/transitions")
def change_state(
    incident_id: str,
    request: TransitionRequest,
    principal: ServicePrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> SecurityIncident:
    return transition(
        db,
        environment_id=request.environment_id,
        incident_id=incident_id,
        target=request.target,
        expected_version=request.expected_version,
        principal=principal,
    )
