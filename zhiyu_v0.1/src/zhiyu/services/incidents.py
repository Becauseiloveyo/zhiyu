from sqlalchemy.orm import Session

from zhiyu.core.errors import AccessDenied
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from
from zhiyu.domain.contracts import SecurityIncident
from zhiyu.repositories.incidents import IncidentRepository


def read_incident(db: Session, incident_id: str, principal: ServicePrincipal) -> SecurityIncident | None:
    if "incidents:read" not in principal.permissions:
        raise AccessDenied("incident read permission required")
    row = IncidentRepository(db).get(incident_id, principal.environment_ids)
    return contract_from(row, SecurityIncident) if row else None
