"""Bounded, read-only projections. Core services remain the only business writers."""

import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from zhiyu.db import models as m
from zhiyu.db.ai_context import DecisionContextRow
from zhiyu.db.ai_gateway import ModelRequestRow
from zhiyu.db.incident_intelligence import IncidentAnalysisRow, IncidentEventRow, IncidentGroupRow
from zhiyu.db.infrastructure import RawDeliveryRow
from zhiyu.db.verification_runtime import VerificationRuntimeRow
from zhiyu.product import snapshots
from zhiyu.product.access import Access, visible_incidents
from zhiyu.product.contracts import Health, IncidentPage, Overview, Query, Snapshot
from zhiyu.product.registry import SPECS, columns, fact, public_value

PER_KIND = 200
TOTAL_FACTS = 2000


def envelope(query: Query, access: Access, as_of: datetime, consistency: str = "LIVE_PAGE") -> dict[str, Any]:
    return dict(
        projection_version="0.9.0",
        run_mode="LIVE",
        environment_id=query.environment_id,
        scope_id=query.scope_id,
        access_policy_version=access.version,
        as_of=as_of,
        consistency=consistency,
    )


def binding(query: Query, access: Access) -> str:
    return snapshots.digest([query.model_dump(mode="json"), access.fingerprint])


def conditions(query: Query, access: Access, now: datetime) -> list[Any]:
    result = visible_incidents(access) + [
        m.IncidentRow.created_at <= now,
        m.IncidentRow.created_at >= now - timedelta(hours=query.hours),
    ]
    if query.status:
        result.append(m.IncidentRow.status == query.status)
    if query.priority:
        result.append(m.IncidentRow.priority == query.priority)
    if query.search:
        # Literal contains, not a user-controlled SQL wildcard expression.
        result.append(
            m.IncidentRow.incident_id.contains(query.search, autoescape=True)
            | m.IncidentRow.title.contains(query.search, autoescape=True)
        )
    return result


def incident_page(db: Session, query: Query, access: Access, limit: int, cursor: str | None) -> IncidentPage:
    now = datetime.now(UTC)
    bound = binding(query, access)
    filters = conditions(query, access, now)
    descending = query.sort == "created_desc"
    if cursor:
        data = snapshots.decode_cursor(cursor, bound)
        try:
            at = datetime.fromisoformat(data["at"])
            identifier = data["id"]
            if not at.tzinfo or not isinstance(identifier, str) or len(identifier) > 256:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise HTTPException(422, "invalid_or_expired_cursor") from None
        anchor = tuple_(m.IncidentRow.created_at, m.IncidentRow.incident_id)
        filters.append(anchor < (at, identifier) if descending else anchor > (at, identifier))
    order: list[Any] = [m.IncidentRow.created_at, m.IncidentRow.incident_id]
    if descending:
        order = [c.desc() for c in order]
    rows = list(
        db.execute(
            select(*columns("incident"), IncidentAnalysisRow.score.label("risk_score"))
            .outerjoin(
                IncidentAnalysisRow,
                (IncidentAnalysisRow.environment_id == m.IncidentRow.environment_id)
                & (IncidentAnalysisRow.incident_id == m.IncidentRow.incident_id),
            )
            .where(*filters)
            .order_by(*order)
            .limit(limit + 1)
        ).mappings()
    )
    next_cursor = None
    if len(rows) > limit:
        row = rows[limit - 1]
        next_cursor = snapshots.encode_cursor(
            dict(
                binding=bound,
                expires=time.time() + 300,
                at=row["created_at"].isoformat(),
                id=row["incident_id"],
            )
        )
    return IncidentPage(
        **envelope(query, access, now),
        items=[{k: public_value(v) for k, v in row.items()} for row in rows[:limit]],
        next_cursor=next_cursor,
    )


def overview(db: Session, query: Query, access: Access) -> Overview:
    now = datetime.now(UTC)
    visible = select(m.IncidentRow.incident_id).where(*conditions(query, access, now))
    counts: dict[str, int] = {
        str(status): int(count)
        for status, count in db.execute(
            select(m.IncidentRow.status, func.count())
            .where(m.IncidentRow.incident_id.in_(visible))
            .group_by(m.IncidentRow.status)
        ).all()
    }
    previous = (
        db.scalar(
            select(func.count())
            .select_from(m.IncidentRow)
            .where(*conditions(query, access, now - timedelta(hours=query.hours)))
        )
        or 0
    )
    events = (
        db.scalar(
            select(func.count(func.distinct(IncidentEventRow.event_id))).where(
                IncidentEventRow.environment_id == query.environment_id,
                IncidentEventRow.incident_id.in_(visible),
            )
        )
        or 0
    )
    current = sum(counts.values())
    day = func.date_trunc("day", m.IncidentRow.created_at)
    daily = db.execute(
        select(day.label("day"), func.count().label("count"))
        .where(
            *visible_incidents(access),
            m.IncidentRow.created_at >= now - timedelta(days=7),
            m.IncidentRow.created_at <= now,
        )
        .group_by(day)
        .order_by(day)
    ).mappings()
    return Overview(
        **envelope(query, access, now),
        metrics=dict(
            incidents=current,
            previous_incidents=previous,
            incident_delta_percent=round((current - previous) / previous * 100, 1) if previous else None,
            associated_events=events,
            needs_attention=sum(
                counts.get(s, 0) for s in ("NEW", "WAITING_APPROVAL", "HUMAN_REVIEW", "REOPENED")
            ),
        ),
        status_counts=counts,
        daily_incidents=[{"day": r["day"].isoformat(), "count": r["count"]} for r in daily],
        formulas={
            "incidents": "COUNT(authorized incidents created within selected window)",
            "incident_delta_percent": "(current - previous equal window) / previous * 100; null when previous=0",
            "associated_events": "COUNT(DISTINCT incident_events.event_id) for visible incidents; not all raw logs",
            "needs_attention": "status IN (NEW, WAITING_APPROVAL, HUMAN_REVIEW, REOPENED)",
            "daily_incidents": "UTC calendar buckets, last 7 days, same read grants; independent of list filters",
            "protection_score": "No approved aggregate protection-score formula",
        },
    )


def health(db: Session, query: Query, access: Access) -> Health:
    now = datetime.now(UTC)
    sensor_cols = [
        m.SensorHealthRow.sensor_id,
        m.SensorHealthRow.status,
        m.SensorHealthRow.last_heartbeat_at,
        m.SensorHealthRow.last_event_at,
        m.SensorHealthRow.lag_seconds,
        m.SensorHealthRow.lost_event_count,
        m.SensorHealthRow.coverage_validated,
        m.SensorHealthRow.config_version,
    ]
    stmt = select(*sensor_cols).where(m.SensorHealthRow.environment_id == query.environment_id)
    if not access.unrestricted:
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import JSONB

        stmt = stmt.where(
            m.SensorHealthRow.coverage_scope_ids.op("<@")(cast(sorted(access.scope_ids), JSONB)),
            func.jsonb_array_length(m.SensorHealthRow.coverage_scope_ids) > 0,
        )
    rows = list(db.execute(stmt.order_by(m.SensorHealthRow.sensor_id).limit(201)).mappings())
    sensors = []
    for row in rows[:200]:
        item = dict(row)
        age = (now - row["last_heartbeat_at"]).total_seconds()
        item["freshness"] = "CURRENT" if 0 <= age <= 120 else "STALE"
        item["effective_status"] = row["status"] if item["freshness"] == "CURRENT" else "UNKNOWN"
        sensors.append({k: public_value(v) for k, v in item.items()})
    # Environment-wide capability queues are not exposed to scoped readers.
    caps = []
    if access.unrestricted:
        caps = list(
            db.execute(
                select(
                    m.CapabilityHealthRow.capability_id,
                    m.CapabilityHealthRow.status,
                    m.CapabilityHealthRow.checked_at,
                    m.CapabilityHealthRow.queue_depth,
                    m.CapabilityHealthRow.running_count,
                )
                .where(m.CapabilityHealthRow.environment_id == query.environment_id)
                .order_by(m.CapabilityHealthRow.capability_id)
                .limit(201)
            ).mappings()
        )
    from zhiyu.core.config import settings

    policy = settings.ai_policies.get(query.environment_id)
    mode = str(policy.mode) if policy and policy.enabled else "OFF"
    required = (
        db.scalar(
            select(m.EnvironmentRow.required_sensor_ids).where(
                m.EnvironmentRow.environment_id == query.environment_id
            )
        )
        or []
    )
    sensor_ids = {s["sensor_id"] for s in sensors}
    coverage_complete = bool(required) and set(required).issubset(sensor_ids)
    return Health(
        **envelope(query, access, now),
        sensors=sensors,
        capabilities=[{k: public_value(v) for k, v in r.items()} for r in caps[:200]],
        ai_mode=mode,
        truncated=len(rows) > 200 or len(caps) > 200,
        runtime_status="UNKNOWN"
        if not coverage_complete
        or any(s["effective_status"] == "UNKNOWN" or not s["coverage_validated"] for s in sensors)
        else "DEGRADED"
        if any(s["effective_status"] != "HEALTHY" for s in sensors)
        else "HEALTHY",
    )


def create_snapshot(db: Session, query: Query, access: Access, incident_id: str) -> Snapshot:
    now = datetime.now(UTC)
    root = (
        db.execute(
            select(*columns("incident")).where(
                *visible_incidents(access), m.IncidentRow.incident_id == incident_id
            )
        )
        .mappings()
        .first()
    )
    if root is None:
        raise HTTPException(404, "incident_not_found")
    facts = [fact("incident", root, query.environment_id, now)]
    truncated = False
    env = query.environment_id

    def collect(kind: str, *filters: Any) -> list[dict[str, Any]]:
        nonlocal truncated
        model, identifier, _ = SPECS[kind]
        remaining = min(PER_KIND, TOTAL_FACTS - len(facts))
        stmt = select(*columns(kind)).where(*filters)
        if hasattr(model, "environment_id"):
            stmt = stmt.where(model.environment_id == env)
        rows = list(db.execute(stmt.order_by(getattr(model, identifier)).limit(remaining + 1)).mappings())
        if len(rows) > remaining:
            truncated = True
        result = [dict(row) for row in rows[:remaining]]
        facts.extend(fact(kind, row, env, now) for row in result)
        return result

    event_ids = select(IncidentEventRow.event_id).where(
        IncidentEventRow.environment_id == env, IncidentEventRow.incident_id == incident_id
    )
    events = collect(
        "event",
        m.EventRow.event_id.in_(event_ids),
        m.EventRow.ingested_at >= now - timedelta(hours=query.hours),
        m.EventRow.ingested_at <= now,
    )
    event_ids_list = [r["event_id"] for r in events]
    resource_ids = set(root["affected_asset_ids"])
    for event in events:
        resource_ids.update(event["source_resource_ids"])
        resource_ids.update(event["target_resource_ids"])
        if event.get("actor_resource_id"):
            resource_ids.add(event["actor_resource_id"])
    # visible_incidents has already required every bound event resource to be in the grant.
    collect("resource", m.ResourceRow.resource_id.in_(resource_ids))
    collect("event_resource", SPECS["event_resource"][0].event_id.in_(event_ids_list))
    deliveries = collect("normalization", RawDeliveryRow.event_id.in_(event_ids_list))
    collect("raw", SPECS["raw"][0].raw_id.in_([r["raw_id"] for r in deliveries]))
    groups = collect(
        "group",
        m.EventGroupRow.group_id.in_(
            select(IncidentGroupRow.group_id).where(
                IncidentGroupRow.environment_id == env, IncidentGroupRow.incident_id == incident_id
            )
        ),
    )
    collect("group_member", SPECS["group_member"][0].event_id.in_(event_ids_list))
    collect("correlation", m.CorrelationDecisionRow.output_group_id.in_([r["group_id"] for r in groups]))
    evidences = collect("evidence", m.EvidenceRow.incident_id == incident_id)
    evidence_ids = [r["evidence_id"] for r in evidences]
    collect("context", m.ContextRow.incident_id == incident_id)
    context_filter = [DecisionContextRow.incident_id == incident_id]
    if not access.unrestricted:
        context_filter.append(DecisionContextRow.scope_id.in_(access.scope_ids))
    contexts = collect("ai_context", *context_filter)
    context_ids = [r["context_id"] for r in contexts]
    requests = collect(
        "model_request",
        ModelRequestRow.incident_id == incident_id,
        ModelRequestRow.context_id.in_(context_ids),
    )
    collect("model_receipt", SPECS["model_receipt"][0].request_id.in_([r["request_id"] for r in requests]))
    collect("model_run", m.ModelRunRow.incident_id == incident_id, m.ModelRunRow.context_id.in_(context_ids))
    for kind in ("analysis", "proposal", "decision"):
        model = SPECS[kind][0]
        collect(kind, model.incident_id == incident_id, model.context_id.in_(context_ids))
    collect("plan", SPECS["plan"][0].incident_id == incident_id)
    collect("task", m.TaskRow.incident_id == incident_id)
    actions = collect("action", m.ActionRow.incident_id == incident_id)
    action_ids = [r["action_id"] for r in actions]
    for kind in ("authorization_context", "authorization", "risk", "approval"):
        collect(kind, SPECS[kind][0].action_id.in_(action_ids))
    attempts = collect("attempt", m.ActionAttemptRow.action_id.in_(action_ids))
    collect("result", SPECS["result"][0].attempt_id.in_([r["attempt_id"] for r in attempts]))
    specs = collect("verification_spec", VerificationRuntimeRow.incident_id == incident_id)
    spec_ids = [r["spec_id"] for r in specs]
    collect("check", SPECS["check"][0].spec_id.in_(spec_ids))
    collect("observation", SPECS["observation"][0].spec_id.in_(spec_ids))
    verifications = collect("verification", m.VerificationResultRow.incident_id == incident_id)
    verification_ids = [r["verification_id"] for r in verifications]
    updates = collect("state_update", SPECS["state_update"][0].verification_id.in_(verification_ids))
    state_ids = [v for r in updates for v in r["entity_ids"]]
    state_ids += [
        f.fields["state_entity_id"] for f in facts if f.kind == "analysis" and f.fields.get("state_entity_id")
    ]
    collect("state", m.StateEntityRow.entity_id.in_(state_ids))
    collect(
        "state_relation",
        m.StateRelationRow.source_entity_id.in_(state_ids),
        m.StateRelationRow.destination_entity_id.in_(state_ids),
    )
    collect("replan", SPECS["replan"][0].verification_id.in_(verification_ids))
    collect(
        "audit", m.AuditEntryRow.object_id == incident_id, m.AuditEntryRow.object_kind == "SecurityIncident"
    )
    # Reference lists can include mixed groups or unresolved historic records. Do not leak their IDs.
    permitted_lists = {
        "member_event_ids": set(event_ids_list),
        "outlier_event_ids": set(event_ids_list),
        "input_event_ids": set(event_ids_list),
        "excluded_event_ids": set(event_ids_list),
        "source_event_ids": set(event_ids_list),
        "evidence_ids": set(evidence_ids),
        "entity_ids": set(state_ids),
    }
    for item in facts:
        for field, allowed in permitted_lists.items():
            if field in item.fields:
                original = item.fields[field]
                item.fields[field] = [v for v in original if v in allowed]
                if len(original) != len(item.fields[field]):
                    item.fields["reference_completeness"] = "PARTIAL"
    snapshot = Snapshot(
        **envelope(query, access, now, "IMMUTABLE_SNAPSHOT"),
        snapshot_id=uuid4().hex,
        expires_at=now + timedelta(seconds=snapshots.TTL),
        content_sha256=snapshots.digest([f.model_dump(mode="json") for f in facts]),
        incident_id=incident_id,
        facts=facts,
        truncated=truncated,
        omitted_count=None if truncated else 0,
        limits={
            "facts": TOTAL_FACTS,
            "per_kind": PER_KIND,
            "response_bytes": snapshots.MAX_BYTES,
            "window_hours": query.hours,
        },
    )
    snapshots.put(snapshot, binding(query, access))
    return snapshot
