"""Bounded evidence-grounded context read model; no raw-log or URL dereferencing."""

from datetime import datetime, timedelta
from time import perf_counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.ai.context_policy import (
    BUILDER_VERSION,
    PROMPT_VERSION,
    ContextPolicy,
    ContextRedactor,
    messages,
    serialized,
)
from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ConflictError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.ai_context import AIStateSnapshotRow, DecisionContextRow
from zhiyu.db.mapping import values_for
from zhiyu.db.models import (
    ActionRow,
    CapabilityHealthRow,
    CapabilityRow,
    ContextRow,
    CorrelationDecisionRow,
    EnvironmentRow,
    EventGroupRow,
    EventRow,
    EvidenceRow,
    IncidentRow,
    PlanRow,
    ResourceRow,
    ScopeRow,
    SensorHealthRow,
    StateEntityRow,
    VerificationResultRow,
)
from zhiyu.db.response_authority import CapabilityConfigRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.domain.contracts import ContextBundle
from zhiyu.response.catalog import INPUTS
from zhiyu.response.planner import emit, identity
from zhiyu.verification.runtime import instant, lock_environment


def freshness(observed: datetime | None, until: datetime | None, at: datetime) -> str:
    if observed is None or until is None:
        return "UNKNOWN"
    if observed > at:
        return "FUTURE"
    return "FRESH" if at < until else "STALE"


class ContextManager:
    def __init__(
        self,
        engine: Engine,
        policy: ContextPolicy = ContextPolicy(),
        *,
        redactor: ContextRedactor | None = None,
    ) -> None:
        self.engine, self.policy = engine, policy
        self.redactor = redactor or ContextRedactor()

    def build(
        self,
        env: str,
        incident_id: str,
        scope_id: str,
        principal: ServicePrincipal,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        principal.require("ai:context", env)
        start = perf_counter()
        with Session(self.engine) as db, db.begin():
            profile = lock_environment(db, env)
            at = instant(db, now)
            incident = db.get(IncidentRow, incident_id)
            scope = db.get(ScopeRow, (scope_id, env))
            if not incident or incident.environment_id != env:
                raise ReferenceError("incident not found in environment")
            if (
                not scope
                or scope_id not in profile.scope_ids
                or not scope.valid_from <= at < scope.valid_until
            ):
                raise ConflictError("context requires active environment scope")
            budget = self.policy.budget
            bucket = int(at.timestamp()) // budget.context_ttl_seconds
            valid_until = min(scope.valid_until, at + timedelta(seconds=budget.context_ttl_seconds))
            targets = sorted(set(incident.affected_asset_ids) & set(scope.target_resource_ids))
            if not targets or len(targets) > 16:
                raise ConflictError("context target set outside bounded scope")
            resources = list(
                db.scalars(
                    select(ResourceRow)
                    .where(ResourceRow.environment_id == env, ResourceRow.resource_id.in_(targets))
                    .order_by(ResourceRow.resource_id)
                )
            )
            evidence = list(
                db.scalars(
                    select(EvidenceRow)
                    .where(EvidenceRow.environment_id == env, EvidenceRow.incident_id == incident_id)
                    .order_by(EvidenceRow.observed_at.desc(), EvidenceRow.evidence_id)
                    .limit(budget.max_evidence)
                )
            )
            excluded: dict[str, str] = {}
            facts: list[dict[str, Any]] = []
            for row in evidence:
                until = min(row.valid_until, row.observed_at + timedelta(seconds=budget.max_age_seconds))
                reason = freshness(row.observed_at, until, at)
                if reason == "FRESH" and (row.trust_status != "VERIFIED_ORIGIN" or row.contradicts):
                    reason = "UNVERIFIED_OR_CONFLICTED"
                if reason == "FRESH" and row.claim_kind not in {"OBSERVATION", "SOURCE_ASSERTION"}:
                    reason = "INFERENCE_NOT_FACT"
                if reason != "FRESH":
                    excluded[row.evidence_id] = reason
                    continue
                valid_until = min(valid_until, until)
                facts.append(
                    {
                        "evidence_id": row.evidence_id,
                        "source_hash": canonical_hash(
                            {
                                "integrity_hash": row.integrity_hash,
                                "supports": row.supports,
                                "source_event_ids": row.source_event_ids,
                                "collected_at": row.collected_at.isoformat(),
                            }
                        ),
                        "kind": row.claim_kind,
                        "summary": self.redactor.clean(row.supports[:4]),
                        "source": row.collector_id,
                        "source_event_ids": row.source_event_ids[: budget.max_events],
                        "observed_at": row.observed_at.isoformat(),
                        "ingested_at": row.collected_at.isoformat(),
                        "valid_until": until.isoformat(),
                        "freshness": "FRESH",
                        "quality": row.trust_status,
                        "confidence_semantics": "verified origin does not prove source assertion true",
                    }
                )
            state = self._state(db, profile, incident, resources, scope_id, at)
            caps = self._capabilities(db, profile, scope, at)
            events = list(
                db.scalars(
                    select(EventRow)
                    .where(EventRow.environment_id == env, EventRow.event_id.in_(incident.related_event_ids))
                    .order_by(EventRow.source_timestamp.desc(), EventRow.event_id)
                    .limit(budget.max_events)
                )
            )
            groups = list(
                db.scalars(
                    select(EventGroupRow)
                    .where(
                        EventGroupRow.environment_id == env,
                        EventGroupRow.group_id.in_(incident.event_group_ids),
                    )
                    .order_by(EventGroupRow.last_seen_at.desc(), EventGroupRow.group_id)
                    .limit(budget.max_timeline_entries)
                )
            )
            decisions = list(
                db.scalars(
                    select(CorrelationDecisionRow)
                    .where(
                        CorrelationDecisionRow.environment_id == env,
                        CorrelationDecisionRow.output_group_id.in_([g.group_id for g in groups]),
                    )
                    .order_by(CorrelationDecisionRow.created_at.desc(), CorrelationDecisionRow.decision_id)
                    .limit(budget.max_timeline_entries)
                )
            )
            plans = list(
                db.scalars(
                    select(PlanRow)
                    .where(PlanRow.environment_id == env, PlanRow.incident_id == incident_id)
                    .order_by(PlanRow.plan_id)
                    .limit(budget.max_prior_plans)
                )
            )
            results = list(
                db.execute(
                    select(
                        ActionRow.action_id,
                        ActionRow.capability_id,
                        ActionResultRow.execution_outcome,
                        ActionResultRow.completed_at,
                    )
                    .select_from(ActionRow)
                    .join(ActionDispatchRow, ActionDispatchRow.action_id == ActionRow.action_id)
                    .join(ActionResultRow, ActionResultRow.attempt_id == ActionDispatchRow.attempt_id)
                    .where(ActionRow.environment_id == env, ActionRow.incident_id == incident_id)
                    .order_by(ActionResultRow.completed_at.desc(), ActionResultRow.attempt_id)
                    .limit(budget.max_timeline_entries)
                )
            )
            verifications = list(
                db.scalars(
                    select(VerificationResultRow)
                    .where(
                        VerificationResultRow.environment_id == env,
                        VerificationResultRow.incident_id == incident_id,
                    )
                    .order_by(VerificationResultRow.finished_at.desc(), VerificationResultRow.verification_id)
                    .limit(budget.max_verification_history)
                )
            )
            body: dict[str, Any] = {
                "objective": "Explain evidence-supported findings and propose bounded read-only next steps",
                "incident": {
                    "incident_id": incident_id,
                    "environment_id": env,
                    "state_version": incident.state_version,
                    "status": incident.status,
                    "priority": incident.priority,
                    "title": self.redactor.text(incident.title),
                    "affected_resources": targets,
                    "observed_at": incident.updated_at.isoformat(),
                    "freshness": freshness(
                        incident.updated_at,
                        incident.updated_at + timedelta(seconds=budget.max_age_seconds),
                        at,
                    ),
                },
                "trusted_facts": facts,
                "state": state,
                "event_groups": [
                    {
                        "group_id": g.group_id,
                        "event_count": len(g.member_event_ids),
                        "last_seen_at": g.last_seen_at.isoformat(),
                        "rule_version": g.rule_version,
                    }
                    for g in groups
                ],
                "correlations": [
                    {
                        "decision_id": d.decision_id,
                        "group_id": d.output_group_id,
                        "rules": self.redactor.clean(d.rules_fired),
                        "reason": self.redactor.text(d.merge_reason),
                    }
                    for d in decisions
                ],
                "events": [
                    {
                        "event_id": e.event_id,
                        "category": e.activity_category,
                        "activity": self.redactor.text(e.activity_name),
                        "outcome": e.outcome,
                        "observed_at": e.source_timestamp.isoformat(),
                        "source": e.collector_id,
                        "freshness": freshness(
                            e.source_timestamp,
                            e.source_timestamp + timedelta(seconds=budget.max_age_seconds),
                            at,
                        ),
                    }
                    for e in events
                ],
                "prior_plans": [
                    {
                        "plan_id": p.plan_id,
                        "model_assisted": p.model_run_id is not None,
                        "tasks": [
                            {
                                "capability_id": t["capability_id"],
                                "target_resource_ids": t["target_resource_ids"],
                            }
                            for t in p.tasks[:8]
                        ],
                    }
                    for p in plans
                ],
                "previous_actions": [
                    {
                        "action_id": a,
                        "capability_id": c,
                        "execution_outcome": o,
                        "completed_at": ts.isoformat(),
                        "semantics": "execution receipt is not security success",
                    }
                    for a, c, o, ts in results
                ],
                "verification_history": [
                    {
                        "verification_id": v.verification_id,
                        "status": v.status,
                        "security": v.security_status,
                        "business": v.business_status,
                        "observation": v.observation_status,
                        "finished_at": v.finished_at.isoformat(),
                        "valid_until": v.valid_until.isoformat(),
                    }
                    for v in verifications
                ],
                "allowed_capabilities": caps,
                "constraints": {
                    "environment_version": profile.version,
                    "policy_version": profile.policy_version,
                    "scope_id": scope_id,
                    "scope_version": scope.version,
                    "scope_valid_until": scope.valid_until.isoformat(),
                    "autonomy_mode": profile.autonomy_mode,
                    "deployment_stage": profile.deployment_stage,
                    "max_auto_risk": profile.max_auto_risk,
                    "model_policy": profile.model_policy,
                    "connectivity": profile.connectivity,
                    "data_egress_policy": profile.data_egress_policy,
                    "classification": self.policy.classification,
                    "model_fact_writes": False,
                    "proposal_is_authorization": False,
                    "max_proposed_tasks": 8,
                },
            }
            # No secret-bearing identifiers or other unredacted scalar can enter a persisted prompt.
            self._check_scalars(body)
            self._compress(body)
            for item in body["state"]:
                if item.get("freshness") == "FRESH" and item.get("valid_until"):
                    valid_until = min(valid_until, datetime.fromisoformat(item["valid_until"]))
            for cap in caps:
                valid_until = min(
                    valid_until,
                    datetime.fromisoformat(cap["health_checked_at"])
                    + timedelta(seconds=budget.health_ttl_seconds),
                )
            used_evidence = sorted(
                {f["evidence_id"] for f in body["trusted_facts"]}
                | {e for s in body["state"] for e in s.get("evidence_ids", [])}
            )
            used_state = [s["state_entity_id"] for s in body["state"] if "state_entity_id" in s]
            used_capabilities = [
                {
                    "capability_id": c["capability_id"],
                    "version": c["version"],
                    "definition_hash": c["definition_hash"],
                }
                for c in body["allowed_capabilities"]
            ]
            doc_hash = canonical_hash(body)
            context_id = identity(
                "decision-context",
                [env, incident_id, incident.state_version, doc_hash, self.policy.model_dump(), bucket],
            )
            prior = db.get(DecisionContextRow, context_id)
            if prior:
                return self._receipt(prior)
            snapshot_body = {"environment_id": env, "incident_id": incident_id, "state": body["state"]}
            snapshot_id = identity("state-snapshot", [context_id, canonical_hash(snapshot_body)])
            manifest = {
                "incident_ids": [incident_id],
                "state_entity_ids": used_state,
                "evidence_ids": used_evidence,
                "event_ids": [e["event_id"] for e in body["events"]],
                "event_group_ids": [g["group_id"] for g in body["event_groups"]],
                "correlation_ids": [d["decision_id"] for d in body["correlations"]],
                "verification_ids": [v["verification_id"] for v in body["verification_history"]],
                "plan_ids": [p["plan_id"] for p in body["prior_plans"]],
                "action_ids": [a["action_id"] for a in body["previous_actions"]],
                "capabilities": used_capabilities,
                "resource_ids": targets,
                "scope_id": scope_id,
                "policy_version": profile.policy_version,
                "context_policy_version": self.policy.version,
                "builder_version": BUILDER_VERSION,
                "prompt_version": PROMPT_VERSION,
                "context_hash": doc_hash,
                "message_hash": canonical_hash(messages(body)),
                "chars": len(serialized(body)),
                "input_token_upper_bound": len(serialized(messages(body)).encode()),
                "excluded_evidence": excluded,
                "raw_evidence_included": False,
                "selection": "bounded latest evidence/events/verification; structured summaries; no raw fetch",
            }
            context = ContextBundle(
                context_id=context_id,
                environment_id=env,
                incident_id=incident_id,
                state_version=incident.state_version,
                evidence_ids=used_evidence,
                excluded_evidence_reasons=excluded,
                unresolved_conflicts=[v for v in excluded.values() if "CONFLICT" in v],
                sensor_health_ids=[s["sensor_id"] for s in body["state"] if "sensor_id" in s],
                capability_ids=[c["capability_id"] for c in caps],
                policy_version=profile.policy_version,
                token_budget=budget.max_tokens,
                data_classification=self.policy.classification,
                egress_allowed=profile.connectivity == "CONNECTED"
                and profile.model_policy != "LOCAL_ONLY"
                and profile.data_egress_policy != "DENY",
                summary_version=BUILDER_VERSION,
                prompt_version=PROMPT_VERSION,
                created_at=at,
            )
            db.add(ContextRow(**values_for(context, ContextRow)))
            db.add(
                AIStateSnapshotRow(
                    snapshot_id=snapshot_id,
                    environment_id=env,
                    incident_id=incident_id,
                    incident_version=incident.state_version,
                    body=snapshot_body,
                    body_hash=canonical_hash(snapshot_body),
                    created_at=at,
                    valid_until=valid_until,
                )
            )
            db.flush()
            metadata = DecisionContextRow(
                context_id=context_id,
                environment_id=env,
                incident_id=incident_id,
                snapshot_id=snapshot_id,
                scope_id=scope_id,
                body=body,
                manifest=manifest,
                context_hash=doc_hash,
                policy=self.policy.model_dump(mode="json"),
                created_at=at,
                valid_until=valid_until,
                build_ms=(perf_counter() - start) * 1000,
            )
            db.add(metadata)
            emit(
                db,
                env,
                "ContextBundle",
                context_id,
                "ContextBuilt",
                "bounded redacted evidence context; not authorization",
                principal.principal_id,
            )
            return self._receipt(metadata)

    def read(self, env: str, context_id: str, principal: ServicePrincipal) -> dict[str, Any]:
        principal.require("ai:read", env)
        with Session(self.engine) as db:
            row = db.get(DecisionContextRow, context_id)
            if not row or row.environment_id != env:
                raise ReferenceError("context not found in environment")
            return self._receipt(row)

    @staticmethod
    def _receipt(row: DecisionContextRow) -> dict[str, Any]:
        return {
            "context_id": row.context_id,
            "snapshot_id": row.snapshot_id,
            "context_hash": row.context_hash,
            "body": row.body,
            "manifest": row.manifest,
            "created_at": row.created_at.isoformat(),
            "valid_until": row.valid_until.isoformat(),
        }

    def _check_scalars(self, value: Any) -> None:
        if isinstance(value, str):
            # Long text was already bounded in projections. Identifiers cannot be silently rewritten.
            if self.redactor.text(value) != value:
                raise ConflictError("context contains an unsafe or oversized identifier")
        elif isinstance(value, list):
            for v in value:
                self._check_scalars(v)
        elif isinstance(value, dict):
            for k, v in value.items():
                self._check_scalars(k)
                self._check_scalars(v)

    def _compress(self, body: dict[str, Any]) -> None:
        b = self.policy.budget
        # Mandatory objective/constraints/capabilities/incident are never truncated into invalid JSON.
        discard_order = (
            "events",
            "previous_actions",
            "prior_plans",
            "correlations",
            "event_groups",
            "verification_history",
            "state",
            "trusted_facts",
        )
        while len(serialized(body)) > b.max_chars or len(serialized(messages(body)).encode()) > b.max_tokens:
            for key in discard_order:
                if body[key]:
                    body[key].pop()
                    break
            else:
                raise ConflictError("mandatory context exceeds configured budget")

    def _capabilities(
        self, db: Session, env: EnvironmentRow, scope: ScopeRow, at: datetime
    ) -> list[dict[str, Any]]:
        allowed = set(env.capability_allowlist) & set(scope.allowed_capabilities) & set(INPUTS)
        out = []
        for cap in db.scalars(
            select(CapabilityRow)
            .where(CapabilityRow.capability_id.in_(allowed))
            .order_by(CapabilityRow.capability_id, CapabilityRow.version)
        ):
            config = db.get(CapabilityConfigRow, (cap.capability_id, cap.version))
            health = db.get(
                CapabilityHealthRow, (cap.capability_id, cap.version, env.environment_id, "response")
            )
            if (
                not config
                or not config.active
                or not health
                or health.status != "HEALTHY"
                or not health.checked_at
                <= at
                < health.checked_at + timedelta(seconds=self.policy.budget.health_ttl_seconds)
                or cap.operation_kind == "STATE_CHANGE"
                or int(cap.base_risk[1:])
                > min(int(env.max_auto_risk[1:]), 2 if env.deployment_stage == "LAB" else 1)
            ):
                continue
            definition_hash = canonical_hash(
                {
                    "capability_id": cap.capability_id,
                    "version": cap.version,
                    "input_schema": cap.input_schema,
                    "risk": cap.base_risk,
                    "operation": cap.operation_kind,
                }
            )
            out.append(
                {
                    "capability_id": cap.capability_id,
                    "version": cap.version,
                    "risk": cap.base_risk,
                    "operation_kind": cap.operation_kind,
                    "purpose": cap.capability_id.replace("_", " "),
                    "target_classes": config.supported_resource_types,
                    "input_schema": INPUTS[cap.capability_id].model_json_schema(),
                    "definition_hash": definition_hash,
                    "health_checked_at": health.checked_at.isoformat(),
                    "execution_requires_fresh_authorization": True,
                }
            )
        return out

    def _state(
        self,
        db: Session,
        env: EnvironmentRow,
        incident: IncidentRow,
        resources: list[ResourceRow],
        scope_id: str,
        at: datetime,
    ) -> list[dict[str, Any]]:
        b = self.policy.budget
        items: list[dict[str, Any]] = []
        for r in resources:
            # Registration/configuration is not a measured fact or a newly refreshed observation.
            items.append(
                {
                    "kind": "CONFIGURATION",
                    "resource_id": r.resource_id,
                    "resource_type": r.resource_type,
                    "binding_version": r.binding_version,
                    "display_name": self.redactor.clean(r.display_name),
                    "source": "registered-resource",
                    "environment_id": env.environment_id,
                    "evidence_ids": [],
                    "observed_at": None,
                    "ingested_at": None,
                    "freshness": "UNKNOWN",
                    "quality": "operator registration; runtime state unverified",
                    "confidence_semantics": "not measured",
                    "service_availability": "UNKNOWN",
                    "business_criticality": "UNKNOWN",
                    "known_vulnerabilities": [],
                }
            )
        for sensor in db.scalars(
            select(SensorHealthRow)
            .where(
                SensorHealthRow.environment_id == env.environment_id,
                SensorHealthRow.sensor_id.in_(env.required_sensor_ids),
            )
            .order_by(SensorHealthRow.sensor_id)
            .limit(16)
        ):
            items.append(
                {
                    "kind": "OPERATIONAL_TELEMETRY",
                    "sensor_id": sensor.sensor_id,
                    "resource_type": "SENSOR",
                    "source": "sensor-health-registry",
                    "environment_id": env.environment_id,
                    "evidence_ids": [],
                    "status": sensor.status,
                    "observed_at": sensor.last_heartbeat_at.isoformat(),
                    "valid_until": (
                        sensor.last_heartbeat_at + timedelta(seconds=b.health_ttl_seconds)
                    ).isoformat(),
                    "ingested_at": None,
                    "freshness": freshness(
                        sensor.last_heartbeat_at,
                        sensor.last_heartbeat_at + timedelta(seconds=b.health_ttl_seconds),
                        at,
                    ),
                    "quality": "coverage validated"
                    if sensor.coverage_validated and scope_id in sensor.coverage_scope_ids
                    else "coverage unknown",
                    "confidence_semantics": "health report; not proof of security",
                    "lost_events": sensor.lost_event_count,
                }
            )
        candidates = db.scalars(
            select(StateEntityRow)
            .where(
                StateEntityRow.environment_id == env.environment_id,
                select(EvidenceRow.evidence_id)
                .where(
                    EvidenceRow.environment_id == env.environment_id,
                    EvidenceRow.incident_id == incident.incident_id,
                    StateEntityRow.evidence_ids.op("@>")(func.jsonb_build_array(EvidenceRow.evidence_id)),
                )
                .exists(),
            )
            .order_by(StateEntityRow.observed_at.desc(), StateEntityRow.entity_id)
            .limit(b.max_state_items * 4)
        )
        for state in candidates:
            refs = list(
                db.scalars(
                    select(EvidenceRow).where(
                        EvidenceRow.environment_id == env.environment_id,
                        EvidenceRow.incident_id == incident.incident_id,
                        EvidenceRow.evidence_id.in_(state.evidence_ids),
                    )
                )
            )
            if not refs or len(refs) != len(set(state.evidence_ids)):
                continue
            until = min(
                [state.valid_until, state.observed_at + timedelta(seconds=b.max_age_seconds)]
                + [e.valid_until for e in refs]
            )
            quality = (
                "VERIFIED_ORIGIN"
                if all(e.trust_status == "VERIFIED_ORIGIN" and not e.contradicts for e in refs)
                else "UNVERIFIED_OR_CONFLICTED"
            )
            model = (
                state.claim_kind == "INFERENCE" and state.attributes.get("source_type") == "MODEL_INFERENCE"
            )
            kind = "MODEL_HYPOTHESIS" if model else state.claim_kind
            items.append(
                {
                    "state_entity_id": state.entity_id,
                    "kind": kind,
                    "entity_type": state.entity_type,
                    "state_version": state.state_version,
                    "source": "MODEL_INFERENCE" if model else "state-entity",
                    "environment_id": env.environment_id,
                    "evidence_ids": sorted(state.evidence_ids),
                    "observed_at": state.observed_at.isoformat(),
                    "ingested_at": max(e.collected_at for e in refs).isoformat(),
                    "valid_until": until.isoformat(),
                    "freshness": freshness(state.observed_at, until, at),
                    "quality": quality,
                    "confidence_semantics": "model self-report, uncalibrated"
                    if model
                    else "source/evidence quality, not probability",
                    "attributes": self.redactor.clean(state.attributes),
                }
            )
        return items[: b.max_state_items]
