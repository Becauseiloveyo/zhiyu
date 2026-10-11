import hashlib
import json
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.core.incident_config import DEFAULT_INCIDENT_CONFIG, IncidentConfig
from zhiyu.db.incident_intelligence import (
    IncidentAnalysisRow,
    IncidentEventRow,
    IncidentGroupRow,
    PromotionRecordRow,
)
from zhiyu.db.infrastructure import RawDeliveryRow, RawRecordRow
from zhiyu.db.intelligence import GroupStateRow
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import EnvironmentRow, EventGroupRow, EventRow, EvidenceRow, IncidentRow
from zhiyu.domain.contracts import EventGroup, Evidence, IncidentStatus, NormalizedEvent, SecurityIncident
from zhiyu.services.event_intelligence import group_events, publish_change
from zhiyu.services.incident_policy import IncidentPromotionPolicy, IncidentRiskCalculator

ACTIVE_STATES = ("NEW", "TRIAGED", "INVESTIGATING")


def raw_for_events(
    db: Session, environment_id: str, events: list[NormalizedEvent]
) -> dict[str, RawRecordRow]:
    ids = [
        e.raw_ref.removeprefix("db://raw_records/")
        for e in events
        if e.raw_ref.startswith("db://raw_records/")
    ]
    records = (
        {
            r.raw_id: r
            for r in db.scalars(
                select(RawRecordRow).where(
                    RawRecordRow.environment_id == environment_id, RawRecordRow.raw_id.in_(ids)
                )
            )
        }
        if ids
        else {}
    )
    # Only the raw-ingest transaction can attest that this event came from these raw bytes.
    receipts = {
        (r.event_id, r.raw_id)
        for r in db.scalars(
            select(RawDeliveryRow).where(
                RawDeliveryRow.environment_id == environment_id,
                RawDeliveryRow.event_id.in_([e.event_id for e in events]),
                RawDeliveryRow.disposition.in_(["ACCEPTED", "DUPLICATE"]),
            )
        )
    }
    valid = {}
    for event in events:
        record = records.get(event.raw_ref.removeprefix("db://raw_records/"))
        if (
            record
            and (event.event_id, record.raw_id) in receipts
            and record.collector_id == event.collector_id
            and record.source_type == event.source_type
            and hashlib.sha256(record.content).hexdigest() == record.integrity_hash
        ):
            valid[event.event_id] = record
    return valid


def incident_events(db: Session, environment_id: str, incident_id: str) -> list[NormalizedEvent]:
    rows = db.scalars(
        select(EventRow)
        .join(
            IncidentEventRow,
            and_(
                IncidentEventRow.environment_id == EventRow.environment_id,
                IncidentEventRow.event_id == EventRow.event_id,
            ),
        )
        .where(IncidentEventRow.environment_id == environment_id, IncidentEventRow.incident_id == incident_id)
        .order_by(EventRow.source_timestamp, EventRow.event_id)
    )
    return [contract_from(row, NormalizedEvent) for row in rows]


class IncidentEngine:
    def __init__(self, db: Session, config: IncidentConfig = DEFAULT_INCIDENT_CONFIG) -> None:
        self.db, self.config = db, config
        self.policy, self.risk = IncidentPromotionPolicy(config), IncidentRiskCalculator(config)
        self.policy_hash = canonical_hash(config.model_dump())

    def promote(
        self,
        environment_id: str,
        *,
        principal: ServicePrincipal,
        now: datetime | None = None,
        limit: int = 1000,
    ) -> dict[str, Any]:
        principal.require("intelligence:write", environment_id)
        if not 1 <= limit <= 1000:
            raise ReferenceError("promotion limit outside bound")
        trace = str(uuid4())
        outcomes = []
        with self.db.begin():
            environment = self.db.scalar(
                select(EnvironmentRow)
                .where(EnvironmentRow.environment_id == environment_id)
                .with_for_update()
            )
            if environment is None:
                raise ReferenceError("environment not bootstrapped")
            instant = now or self.db.scalar(select(func.clock_timestamp()))
            assert instant is not None
            checked = exists(
                select(PromotionRecordRow.group_id).where(
                    PromotionRecordRow.environment_id == GroupStateRow.environment_id,
                    PromotionRecordRow.group_id == GroupStateRow.group_id,
                    PromotionRecordRow.group_version == GroupStateRow.version,
                    PromotionRecordRow.policy_hash == self.policy_hash,
                )
            )
            states = list(
                self.db.scalars(
                    select(GroupStateRow)
                    .where(GroupStateRow.environment_id == environment_id, ~checked)
                    .order_by(GroupStateRow.window_start, GroupStateRow.group_id)
                    .limit(limit)
                )
            )
            for state in states:
                start = perf_counter()
                row = self.db.get(EventGroupRow, state.group_id)
                assert row is not None
                group = contract_from(row, EventGroup)
                events = group_events(self.db, environment_id, state.group_id)
                records = raw_for_events(self.db, environment_id, events)
                risk = self.risk.calculate(
                    events, verified_count=len(records), validation=any(e.validation_run_id for e in events)
                )
                promote, reasons = self.policy.evaluate(group, state, events, risk, environment, instant)
                link = self.db.get(
                    IncidentGroupRow, {"environment_id": environment_id, "group_id": state.group_id}
                )
                incident = self.db.get(IncidentRow, link.incident_id) if link else None
                merge_reason = "new incident: no eligible active incident within bounded merge horizon"
                outcome = "NOT_PROMOTED"
                incident_id = None
                if incident is not None and incident.status not in ACTIVE_STATES:
                    promote, reasons = False, ["existing_incident_state_disallows_update"]
                elif incident is not None:
                    current_analysis = self.db.get(
                        IncidentAnalysisRow,
                        {"environment_id": environment_id, "incident_id": incident.incident_id},
                    )
                    if current_analysis is None or current_analysis.policy_hash != self.policy_hash:
                        promote, reasons = False, ["existing_incident_policy_version_differs"]
                    else:
                        promote, merge_reason = True, "new members of an already linked active group"
                elif promote:
                    incident = self._merge_candidate(group, environment_id)
                    if incident is not None:
                        merge_reason = "same environment, actor, target, service, activity, outcome, policy and bounded first-observation horizon; active state"
                if promote:
                    existing = (
                        incident_events(self.db, environment_id, incident.incident_id) if incident else []
                    )
                    events = sorted(
                        {e.event_id: e for e in existing + events}.values(),
                        key=lambda e: (e.source_timestamp, e.event_id),
                    )
                    records = raw_for_events(self.db, environment_id, events)
                    risk = self.risk.calculate(
                        events,
                        verified_count=len(records),
                        validation=any(e.validation_run_id for e in events),
                    )
                    analysis: IncidentAnalysisRow | None
                    if incident is None:
                        incident_id = "inc-" + canonical_hash(
                            [environment_id, state.group_id, self.policy_hash]
                        )
                        contract = SecurityIncident(
                            incident_id=incident_id,
                            environment_id=environment_id,
                            title=f"{group.grouping_keys['activity']}: {group.grouping_keys['target']}",
                            status=IncidentStatus.NEW,
                            priority=risk.priority,
                            affected_asset_ids=[],
                            related_event_ids=[],
                            event_group_ids=[],
                            evidence_ids=[],
                            state_version=1,
                            first_observed_at=events[0].source_timestamp,
                            created_at=instant,
                            updated_at=instant,
                            open_action_ids=[],
                            residual_risks=[],
                        )
                        incident = IncidentRow(**values_for(contract, IncidentRow))
                        self.db.add(incident)
                        self.db.flush()
                        analysis = IncidentAnalysisRow(
                            environment_id=environment_id,
                            incident_id=incident_id,
                            merge_key=self.policy.merge_key(group),
                            policy_hash=self.policy_hash,
                            score=risk.score,
                            factors=risk.factors,
                            config=self.config.model_dump(),
                            last_observed_at=events[-1].source_timestamp,
                        )
                        self.db.add(analysis)
                        outcome = "CREATED"
                    else:
                        incident_id = incident.incident_id
                        analysis = self.db.get(
                            IncidentAnalysisRow,
                            {"environment_id": environment_id, "incident_id": incident_id},
                        )
                        assert analysis is not None
                        incident.state_version += 1
                        outcome = "UPDATED" if link else "MERGED"
                    if link is None:
                        self.db.add(
                            IncidentGroupRow(
                                environment_id=environment_id,
                                group_id=group.group_id,
                                incident_id=incident_id,
                                group_version=state.version,
                            )
                        )
                    else:
                        link.group_version = state.version
                    previous_ids = {e.event_id for e in existing}
                    evidence_ids = list(incident.evidence_ids)
                    for event in events:
                        if event.event_id in previous_ids:
                            continue
                        evidence_id = "evd-" + canonical_hash([incident_id, event.event_id])
                        record = records.get(event.event_id)
                        evidence = Evidence(
                            evidence_id=evidence_id,
                            environment_id=environment_id,
                            incident_id=incident_id,
                            source_event_ids=[event.event_id],
                            provenance_group=event.provenance_group,
                            claim_kind="SOURCE_ASSERTION",
                            observed_at=event.source_timestamp,
                            collected_at=event.ingested_at,
                            valid_until=event.source_timestamp
                            + timedelta(seconds=self.config.evidence_ttl_seconds),
                            content_ref=event.raw_ref
                            if record
                            else f"db://normalized_events/{event.event_id}",
                            integrity_hash=record.integrity_hash
                            if record
                            else canonical_hash(event.model_dump(mode="json")),
                            collector_id=event.collector_id,
                            collection_method="authenticated_sensor_ingest"
                            if record
                            else "normalized_event_reference",
                            trust_status="VERIFIED_ORIGIN" if record else "UNVERIFIED_ORIGIN",
                            supports=[incident_id],
                            contradicts=[],
                            data_origin=event.data_origin,
                        )
                        self.db.add(EvidenceRow(**values_for(evidence, EvidenceRow)))
                        self.db.flush()
                        self.db.add(
                            IncidentEventRow(
                                environment_id=environment_id,
                                incident_id=incident_id,
                                event_id=event.event_id,
                                evidence_id=evidence_id,
                            )
                        )
                        evidence_ids.append(evidence_id)
                    incident.related_event_ids = [e.event_id for e in events]
                    incident.affected_asset_ids = sorted(
                        {asset for e in events for asset in e.target_resource_ids}
                    )
                    incident.evidence_ids = sorted(evidence_ids)
                    incident.event_group_ids = sorted(set(incident.event_group_ids) | {group.group_id})
                    incident.first_observed_at = events[0].source_timestamp
                    incident.updated_at, incident.priority = instant, risk.priority
                    analysis.score, analysis.factors, analysis.last_observed_at = (
                        risk.score,
                        risk.factors,
                        events[-1].source_timestamp,
                    )
                    contract_from(incident, SecurityIncident)
                    publish_change(
                        self.db,
                        environment_id=environment_id,
                        kind="SecurityIncident",
                        object_id=incident_id
                        if outcome == "CREATED"
                        else f"{incident_id}:v{incident.state_version}",
                        event_type="IncidentCreated" if outcome == "CREATED" else "IncidentUpdated",
                        reference=f"db://incidents/{incident_id}",
                        reason=json.dumps(
                            {
                                "policy_reasons": reasons,
                                "merge_reason": merge_reason,
                                "risk_score": risk.score,
                                "factors": risk.factors,
                            },
                            sort_keys=True,
                        ),
                        actor=principal.principal_id,
                        trace=trace,
                    )
                explanation = {
                    "policy_version": self.config.promotion_version,
                    "reasons": reasons,
                    "merge_reason": merge_reason,
                    "score": risk.score,
                    "priority": risk.priority,
                    "factors": risk.factors,
                }
                duration = (perf_counter() - start) * 1000
                self.db.add(
                    PromotionRecordRow(
                        environment_id=environment_id,
                        group_id=group.group_id,
                        group_version=state.version,
                        policy_hash=self.policy_hash,
                        incident_id=incident_id,
                        outcome=outcome,
                        explanation=explanation,
                        promotion_ms=duration,
                        created_at=instant,
                    )
                )
                outcomes.append(
                    {
                        "group_id": group.group_id,
                        "incident_id": incident_id,
                        "outcome": outcome,
                        "explanation": explanation,
                        "promotion_ms": duration,
                    }
                )
            self.db.flush()
        return {
            "evaluated": len(outcomes),
            "created": sum(x["outcome"] == "CREATED" for x in outcomes),
            "updated": sum(x["outcome"] in {"UPDATED", "MERGED"} for x in outcomes),
            "results": outcomes,
        }

    def _merge_candidate(self, group: EventGroup, environment_id: str) -> IncidentRow | None:
        horizon = timedelta(seconds=self.config.merge_horizon_seconds)
        return self.db.scalar(
            select(IncidentRow)
            .join(
                IncidentAnalysisRow,
                and_(
                    IncidentAnalysisRow.environment_id == IncidentRow.environment_id,
                    IncidentAnalysisRow.incident_id == IncidentRow.incident_id,
                ),
            )
            .where(
                IncidentRow.environment_id == environment_id,
                IncidentRow.status.in_(ACTIVE_STATES),
                IncidentAnalysisRow.merge_key == self.policy.merge_key(group),
                IncidentAnalysisRow.policy_hash == self.policy_hash,
                IncidentRow.first_observed_at >= group.last_seen_at - horizon,
                IncidentRow.first_observed_at <= group.first_seen_at,
                IncidentAnalysisRow.last_observed_at <= group.first_seen_at + horizon,
            )
            .order_by(IncidentRow.created_at, IncidentRow.incident_id)
            .limit(1)
        )
