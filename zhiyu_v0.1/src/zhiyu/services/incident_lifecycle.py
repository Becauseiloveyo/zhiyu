from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.core.errors import ConflictError, ReferenceError, StaleVersionError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import EnvironmentRow, EvidenceRow, IncidentRow, ScopeRow
from zhiyu.domain.contracts import SecurityIncident
from zhiyu.services.event_intelligence import publish_change
from zhiyu.services.incident_engine import incident_events, raw_for_events


def transition(
    db: Session,
    *,
    environment_id: str,
    incident_id: str,
    target: str,
    expected_version: int,
    principal: ServicePrincipal,
    now: datetime | None = None,
) -> SecurityIncident:
    principal.require("incidents:write", environment_id)
    with db.begin():
        environment = db.scalar(
            select(EnvironmentRow).where(EnvironmentRow.environment_id == environment_id).with_for_update()
        )
        incident = db.scalar(
            select(IncidentRow)
            .where(IncidentRow.environment_id == environment_id, IncidentRow.incident_id == incident_id)
            .with_for_update()
        )
        if environment is None or incident is None:
            raise ReferenceError("incident not found in environment")
        if target not in {"TRIAGED", "INVESTIGATING"}:
            raise ConflictError("transition not implemented")
        if incident.status == target and incident.state_version == expected_version + 1:
            return contract_from(incident, SecurityIncident)
        if incident.state_version != expected_version:
            raise StaleVersionError("incident state changed")
        if (incident.status, target) not in {("NEW", "TRIAGED"), ("TRIAGED", "INVESTIGATING")}:
            raise ConflictError("illegal incident transition")
        instant = now or db.scalar(select(func.clock_timestamp()))
        assert instant is not None
        events = incident_events(db, environment_id, incident_id)
        records = raw_for_events(db, environment_id, events)
        evidence = list(
            db.scalars(
                select(EvidenceRow).where(
                    EvidenceRow.environment_id == environment_id, EvidenceRow.incident_id == incident_id
                )
            )
        )
        if not events or len(records) != len(events) or len(evidence) != len(events):
            raise ConflictError("schema and origin guard failed")
        for item in evidence:
            record = records.get(item.source_event_ids[0]) if len(item.source_event_ids) == 1 else None
            if (
                item.trust_status != "VERIFIED_ORIGIN"
                or record is None
                or item.integrity_hash != record.integrity_hash
                or item.valid_until <= instant
            ):
                raise ConflictError("evidence origin or freshness guard failed")
        if target == "INVESTIGATING":
            scopes = db.scalars(
                select(ScopeRow).where(
                    ScopeRow.environment_id == environment_id, ScopeRow.scope_id.in_(environment.scope_ids)
                )
            )
            allowed = {resource for scope in scopes for resource in scope.target_resource_ids}
            # Passive evidence lookup only: this is not an active-operation TTL authorization.
            if not incident.affected_asset_ids or not set(incident.affected_asset_ids) <= allowed:
                raise ConflictError("scope-bound evidence lookup guard failed")
            incident.investigation_started_at = instant
        else:
            incident.triaged_at = instant
        incident.status, incident.updated_at = target, instant
        incident.state_version += 1
        checked = contract_from(incident, SecurityIncident)
        publish_change(
            db,
            environment_id=environment_id,
            kind="SecurityIncident",
            object_id=f"{incident_id}:v{incident.state_version}",
            event_type="IncidentUpdated",
            reference=f"db://incidents/{incident_id}",
            reason=f"lifecycle={target};schema/origin/evidence guards passed",
            actor=principal.principal_id,
            trace=f"{incident_id}:v{incident.state_version}",
        )
        return checked
