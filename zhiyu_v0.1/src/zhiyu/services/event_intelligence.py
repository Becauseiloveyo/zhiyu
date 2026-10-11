"""Durable deterministic correlation, serialized per environment.

Membership is the processing checkpoint. A crash rolls back groups, decisions,
memberships, audit and outbox together. Reopening the service needs no memory.
"""

import json
from dataclasses import replace
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.core.intelligence_config import DEFAULT_INTELLIGENCE_CONFIG, IntelligenceConfig
from zhiyu.db.intelligence import DecisionInputRow, GroupMemberRow, GroupStateRow, IntelligenceRunRow
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import CorrelationDecisionRow, EnvironmentRow, EventGroupRow, EventRow
from zhiyu.domain.contracts import CorrelationDecision, EventGroup, NormalizedEvent
from zhiyu.repositories.audit import AuditRepository
from zhiyu.repositories.outbox import OutboxRepository
from zhiyu.services.correlation_keys import CorrelationKey, CorrelationKeyBuilder


def ungrouped() -> Any:
    return ~exists(
        select(GroupMemberRow.event_id).where(
            GroupMemberRow.environment_id == EventRow.environment_id,
            GroupMemberRow.event_id == EventRow.event_id,
        )
    )


def group_events(db: Session, environment_id: str, group_id: str) -> list[NormalizedEvent]:
    rows = db.scalars(
        select(EventRow)
        .join(
            GroupMemberRow,
            and_(
                GroupMemberRow.environment_id == EventRow.environment_id,
                GroupMemberRow.event_id == EventRow.event_id,
            ),
        )
        .where(GroupMemberRow.environment_id == environment_id, GroupMemberRow.group_id == group_id)
        .order_by(EventRow.source_timestamp, EventRow.event_id)
    )
    return [contract_from(row, NormalizedEvent) for row in rows]


def publish_change(
    db: Session,
    *,
    environment_id: str,
    kind: str,
    object_id: str,
    event_type: str,
    reference: str,
    reason: str,
    actor: str,
    trace: str,
) -> None:
    AuditRepository(db).append(
        environment_id=environment_id,
        trace_id=trace,
        actor_id=actor,
        object_kind=kind,
        object_id=object_id,
        operation=event_type,
        reason=reason,
    )
    OutboxRepository(db).enqueue(
        environment_id=environment_id,
        aggregate_type=kind,
        aggregate_id=object_id,
        event_type=event_type,
        payload_ref=reference,
    )


class EventIntelligenceEngine:
    def __init__(self, db: Session, config: IntelligenceConfig = DEFAULT_INTELLIGENCE_CONFIG) -> None:
        self.db, self.config = db, config
        self.keys = CorrelationKeyBuilder(config)

    def process(
        self,
        environment_id: str,
        *,
        principal: ServicePrincipal,
        now: datetime | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        principal.require("intelligence:write", environment_id)
        bound = self.config.batch_limit if limit is None else limit
        if not 1 <= bound <= self.config.batch_limit:
            raise ReferenceError("processing limit outside configured bound")
        trace, started = str(uuid4()), perf_counter()
        with self.db.begin():
            env = self.db.scalar(
                select(EnvironmentRow)
                .where(EnvironmentRow.environment_id == environment_id)
                .with_for_update()
            )
            if env is None:
                raise ReferenceError("environment not bootstrapped")
            instant = now or self.db.scalar(select(func.clock_timestamp()))
            assert instant is not None
            rows = list(
                self.db.scalars(
                    select(EventRow)
                    .where(EventRow.environment_id == environment_id, ungrouped())
                    .order_by(EventRow.source_timestamp, EventRow.event_id)
                    .limit(bound)
                )
            )
            events = [contract_from(row, NormalizedEvent) for row in rows]
            candidates: dict[str, tuple[CorrelationKey, list[NormalizedEvent]]] = {}
            for event in events:
                key = self.keys.build(event)
                state = self.db.scalar(
                    select(GroupStateRow).where(
                        GroupStateRow.environment_id == environment_id, GroupStateRow.key_hash == key.digest
                    )
                )
                if state is not None and state.status == "CLOSED":
                    # Closed windows are immutable. A late singleton can never reopen their incidents.
                    dims = {
                        **key.dimensions,
                        "disposition": "LATE",
                        "isolation_event": event.event_id,
                        "closed_window_group": state.group_id,
                    }
                    key = replace(key, digest=canonical_hash(dims), dimensions=dims, disposition="LATE")
                candidates.setdefault(key.digest, (key, []))[1].append(event)
            group_ids, decision_ids = [], []
            new_groups = 0
            for digest, (key, incoming) in sorted(candidates.items()):
                group_id = "grp-" + digest
                state = self.db.get(GroupStateRow, {"environment_id": environment_id, "group_id": group_id})
                previous = group_events(self.db, environment_id, group_id) if state else []
                combined = sorted(
                    previous + incoming, key=lambda event: (event.source_timestamp, event.event_id)
                )
                roots = sorted({event.provenance_group for event in combined})
                source_types = sorted({event.source_type for event in combined})
                reasons = ["exact_identity_dimensions", "fixed_utc_window", "provenance_preserved"]
                if len(source_types) > 1:
                    reasons.append("cross_source_authentication")
                if key.disposition != "TIMELY":
                    reasons.append("isolated_" + key.disposition.lower())
                group = EventGroup(
                    group_id=group_id,
                    environment_id=environment_id,
                    first_seen_at=combined[0].source_timestamp,
                    last_seen_at=combined[-1].source_timestamp,
                    member_event_ids=[event.event_id for event in combined],
                    grouping_keys=key.dimensions,
                    correlation_reasons=reasons,
                    outlier_event_ids=[],
                    correlation_confidence=key.confidence,
                    rule_version=self.config.rule_version,
                    algorithm_version=self.config.algorithm_version,
                )
                summary = {
                    "event_count": len(combined),
                    "severity_max": max(e.severity_signal for e in combined),
                    "severity_mean": sum(e.severity_signal for e in combined) / len(combined),
                    "source_types": source_types,
                    "provenance_roots": roots,
                    "independent_sources": len(roots),
                    "confidence_semantics": "source/target/user/activity dimension coverage, not probability",
                }
                if state is None:
                    self.db.add(EventGroupRow(**values_for(group, EventGroupRow)))
                    self.db.flush()
                    state = GroupStateRow(
                        environment_id=environment_id,
                        group_id=group_id,
                        key_hash=digest,
                        window_start=key.window_start,
                        window_end=key.window_end,
                        status="OPEN",
                        disposition=key.disposition,
                        version=1,
                        summary=summary,
                        config=self.config.model_dump(),
                        created_at=instant,
                        updated_at=instant,
                    )
                    self.db.add(state)
                    new_groups += 1
                    publish_change(
                        self.db,
                        environment_id=environment_id,
                        kind="EventGroup",
                        object_id=group_id,
                        event_type="EventGroupCreated",
                        reference=f"db://event_groups/{group_id}",
                        reason=json.dumps({"dimensions": key.dimensions, "rules": reasons}, sort_keys=True),
                        actor=principal.principal_id,
                        trace=trace,
                    )
                else:
                    row = self.db.get(EventGroupRow, group_id)
                    assert row is not None
                    for name, value in values_for(group, EventGroupRow).items():
                        setattr(row, name, value)
                    state.version += 1
                    state.summary, state.updated_at = summary, instant
                    publish_change(
                        self.db,
                        environment_id=environment_id,
                        kind="EventGroup",
                        object_id=f"{group_id}:v{state.version}",
                        event_type="EventGroupUpdated",
                        reference=f"db://event_groups/{group_id}",
                        reason=f"new_members={len(incoming)}",
                        actor=principal.principal_id,
                        trace=trace,
                    )
                self.db.flush()
                for event in incoming:
                    self.db.add(
                        GroupMemberRow(
                            environment_id=environment_id,
                            event_id=event.event_id,
                            group_id=group_id,
                            added_at=instant,
                        )
                    )
                excluded = self._excluded(environment_id, key, {e.event_id for e in combined})
                decision_id = "corr-" + canonical_hash([group_id, sorted(e.event_id for e in incoming)])
                decision = CorrelationDecision(
                    decision_id=decision_id,
                    environment_id=environment_id,
                    input_event_ids=[e.event_id for e in incoming],
                    output_group_id=group_id,
                    rules_fired=reasons,
                    merge_reason=json.dumps(
                        {
                            "dimensions": key.dimensions,
                            "summary": summary,
                            "algorithm_version": self.config.algorithm_version,
                            "rule_version": self.config.rule_version,
                            "config_version": self.config.version,
                            "group_version": state.version,
                            "excluded": excluded,
                            "candidate_policy": f"earliest {self.config.candidate_limit} same-window mismatches; bounded sample",
                        },
                        sort_keys=True,
                    ),
                    excluded_event_ids=list(excluded),
                    decision_version=self.config.rule_version,
                    created_at=instant,
                )
                self.db.add(CorrelationDecisionRow(**values_for(decision, CorrelationDecisionRow)))
                self.db.flush()
                for event in incoming:
                    self.db.add(
                        DecisionInputRow(
                            environment_id=environment_id,
                            decision_id=decision_id,
                            event_id=event.event_id,
                            role="INPUT",
                            reason="matched exact grouping dimensions",
                        )
                    )
                for event_id, reason in excluded.items():
                    self.db.add(
                        DecisionInputRow(
                            environment_id=environment_id,
                            decision_id=decision_id,
                            event_id=event_id,
                            role="EXCLUDED",
                            reason=reason,
                        )
                    )
                publish_change(
                    self.db,
                    environment_id=environment_id,
                    kind="CorrelationDecision",
                    object_id=decision_id,
                    event_type="CorrelationDecisionCreated",
                    reference=f"db://correlation_decisions/{decision_id}",
                    reason=decision.merge_reason,
                    actor=principal.principal_id,
                    trace=trace,
                )
                group_ids.append(group_id)
                decision_ids.append(decision_id)
            self.db.flush()
            pending = (
                self.db.scalar(
                    select(func.count())
                    .select_from(EventRow)
                    .where(EventRow.environment_id == environment_id, ungrouped())
                )
                or 0
            )
            # Never split an already-arrived backlog just because it needs multiple worker batches.
            if pending == 0:
                for state in self.db.scalars(
                    select(GroupStateRow).where(
                        GroupStateRow.environment_id == environment_id, GroupStateRow.status == "OPEN"
                    )
                ):
                    grace = state.config["allowed_lateness_seconds"]
                    if instant >= state.window_end + timedelta(seconds=grace):
                        state.status, state.updated_at = "CLOSED", instant
            duration = (perf_counter() - started) * 1000
            self.db.add(
                IntelligenceRunRow(
                    run_id=trace,
                    environment_id=environment_id,
                    processed=len(events),
                    groups_created=new_groups,
                    decisions_created=len(decision_ids),
                    correlation_ms=duration,
                    created_at=instant,
                )
            )
        return {
            "run_id": trace,
            "processed": len(events),
            "groups_created": new_groups,
            "group_ids": group_ids,
            "decision_ids": decision_ids,
            "pending": pending,
            "correlation_ms": duration,
        }

    def _excluded(self, environment_id: str, key: CorrelationKey, members: set[str]) -> dict[str, str]:
        rows = self.db.scalars(
            select(EventRow)
            .where(
                EventRow.environment_id == environment_id,
                EventRow.source_timestamp >= key.window_start,
                EventRow.source_timestamp < key.window_end,
                EventRow.event_id.not_in(members),
            )
            .order_by(EventRow.source_timestamp, EventRow.event_id)
            .limit(self.config.candidate_limit)
        )
        excluded = {}
        for row in rows:
            other = self.keys.build(contract_from(row, NormalizedEvent))
            mismatch = sorted(
                name
                for name in set(key.dimensions) | set(other.dimensions)
                if key.dimensions.get(name) != other.dimensions.get(name)
            )
            # A same-key event waiting in another bounded batch is not a rejected candidate.
            if mismatch:
                excluded[row.event_id] = "dimension_mismatch:" + ",".join(mismatch)
        return excluded
