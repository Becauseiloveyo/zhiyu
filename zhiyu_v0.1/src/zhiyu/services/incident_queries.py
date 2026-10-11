import base64
import json
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from zhiyu.core.errors import AccessDenied, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.incident_intelligence import IncidentAnalysisRow, IncidentEventRow, IncidentGroupRow
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import CorrelationDecisionRow, EventRow, EvidenceRow, IncidentRow
from zhiyu.domain.contracts import CorrelationDecision, Evidence, NormalizedEvent, SecurityIncident
from zhiyu.repositories.incidents import IncidentRepository


def scoped_incident(db: Session, incident_id: str, principal: ServicePrincipal) -> IncidentRow | None:
    if "incidents:read" not in principal.permissions:
        raise AccessDenied("incident read required")
    return IncidentRepository(db).get(incident_id, principal.environment_ids)


def cursor_filter(cursor: str | None, environment_id: str, timestamp: Any, identity: Any) -> Any:
    if cursor is None:
        return True
    try:
        if len(cursor) > 2048:
            raise ValueError("cursor too long")
        env, time, identifier = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        parsed = datetime.fromisoformat(time)
        if (
            env != environment_id
            or not isinstance(identifier, str)
            or len(identifier) > 256
            or parsed.tzinfo is None
        ):
            raise ValueError("invalid cursor")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ReferenceError("invalid page cursor") from exc
    return or_(timestamp > parsed, and_(timestamp == parsed, identity > identifier))


def page(
    db: Session,
    query: Any,
    *,
    environment_id: str,
    row_type: Any,
    contract_type: Any,
    time_field: str,
    id_field: str,
    limit: int,
    cursor: str | None,
) -> dict[str, Any]:
    timestamp, identity = getattr(row_type, time_field), getattr(row_type, id_field)
    rows = list(
        db.scalars(
            query.where(cursor_filter(cursor, environment_id, timestamp, identity))
            .order_by(timestamp, identity)
            .limit(limit + 1)
        )
    )
    next_cursor = None
    if len(rows) > limit:
        row = rows[limit - 1]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(
                [environment_id, getattr(row, time_field).isoformat(), getattr(row, id_field)]
            ).encode()
        ).decode()
    return {
        "items": [contract_from(row, contract_type).model_dump(mode="json") for row in rows[:limit]],
        "next_cursor": next_cursor,
    }


def list_incidents(
    db: Session,
    environment_id: str,
    principal: ServicePrincipal,
    *,
    limit: int = 50,
    cursor: str | None = None,
    status: str | None = None,
    min_risk: int | None = None,
    max_risk: int | None = None,
) -> dict[str, Any]:
    principal.require("incidents:read", environment_id)
    query = select(IncidentRow).outerjoin(
        IncidentAnalysisRow,
        and_(
            IncidentAnalysisRow.environment_id == IncidentRow.environment_id,
            IncidentAnalysisRow.incident_id == IncidentRow.incident_id,
        ),
    )
    query = query.where(IncidentRow.environment_id == environment_id)
    if status is not None:
        query = query.where(IncidentRow.status == status)
    if min_risk is not None:
        query = query.where(IncidentAnalysisRow.score >= min_risk)
    if max_risk is not None:
        query = query.where(IncidentAnalysisRow.score <= max_risk)
    return page(
        db,
        query,
        environment_id=environment_id,
        row_type=IncidentRow,
        contract_type=SecurityIncident,
        time_field="created_at",
        id_field="incident_id",
        limit=limit,
        cursor=cursor,
    )


def lineage_page(
    db: Session, incident: IncidentRow, kind: str, *, limit: int, cursor: str | None
) -> dict[str, Any]:
    env, identifier = incident.environment_id, incident.incident_id
    row_type: Any
    contract: Any
    query: Any
    if kind == "events":
        query = (
            select(EventRow)
            .join(
                IncidentEventRow,
                and_(
                    IncidentEventRow.environment_id == EventRow.environment_id,
                    IncidentEventRow.event_id == EventRow.event_id,
                ),
            )
            .where(IncidentEventRow.environment_id == env, IncidentEventRow.incident_id == identifier)
        )
        row_type, contract, time_field, id_field = EventRow, NormalizedEvent, "source_timestamp", "event_id"
    elif kind == "correlations":
        query = select(CorrelationDecisionRow).join(
            IncidentGroupRow,
            and_(
                IncidentGroupRow.environment_id == CorrelationDecisionRow.environment_id,
                IncidentGroupRow.group_id == CorrelationDecisionRow.output_group_id,
            ),
        )
        query = query.where(
            IncidentGroupRow.environment_id == env, IncidentGroupRow.incident_id == identifier
        )
        row_type, contract, time_field, id_field = (
            CorrelationDecisionRow,
            CorrelationDecision,
            "created_at",
            "decision_id",
        )
    else:
        query = select(EvidenceRow).where(
            EvidenceRow.environment_id == env, EvidenceRow.incident_id == identifier
        )
        row_type, contract, time_field, id_field = EvidenceRow, Evidence, "observed_at", "evidence_id"
    return page(
        db,
        query,
        environment_id=env,
        row_type=row_type,
        contract_type=contract,
        time_field=time_field,
        id_field=id_field,
        limit=limit,
        cursor=cursor,
    )
