"""Pure validation of proposals; no authorization issuance or executor access."""

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from zhiyu.ai.analysis import ClaimGroundingValidator
from zhiyu.ai.outputs import Finding, PlanProposalOutput, SituationOutput
from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import DomainError
from zhiyu.db.ai_context import DecisionContextRow
from zhiyu.db.models import CapabilityHealthRow, EnvironmentRow, IncidentRow, ResourceRow, ScopeRow
from zhiyu.domain.contracts import CapabilityManifest
from zhiyu.response.catalog import validate_input
from zhiyu.response.registry import CapabilityRegistry


class PlanAggregateRiskValidator:
    """Conservative finite read/check catalog; reject state changes even if mislabeled R0."""

    def validate(
        self, proposal: PlanProposalOutput, capabilities: dict[str, CapabilityManifest]
    ) -> dict[str, Any]:
        tasks = proposal.proposed_tasks
        targets = Counter(t.target_resource_id for t in tasks)
        active = sum(
            capabilities[t.capability_id].operation_kind == "ACTIVE_CHECK"
            for t in tasks
            if t.capability_id in capabilities
        )
        state_changes = sum(
            capabilities[t.capability_id].operation_kind == "STATE_CHANGE"
            for t in tasks
            if t.capability_id in capabilities
        )
        signatures = [
            (
                t.capability_id,
                t.target_resource_id,
                canonical_hash(t.parameters.model_dump(exclude_none=True)),
            )
            for t in tasks
        ]
        reasons = []
        if len(tasks) > 4:
            reasons.append("aggregate_action_count")
        if max(targets.values(), default=0) > 3:
            reasons.append("aggregate_same_target")
        if len(set(signatures)) != len(signatures):
            reasons.append("repeated_action_fingerprint")
        if state_changes:
            reasons.append("state_change_or_dangerous_sequence")
        if active > 1:
            reasons.append("cumulative_active_checks")
        if (
            sum(
                t.parameters.limit or 50
                for t in tasks
                if t.capability_id in capabilities
                and capabilities[t.capability_id].operation_kind == "PASSIVE_READ"
            )
            > 200
        ):
            reasons.append("cumulative_read_impact")
        risk = max([c.base_risk.value for c in capabilities.values()] or ["R0"])
        if reasons:
            risk = max(risk, "R3")
        return {
            "valid": not reasons,
            "reasons": reasons,
            "aggregate_risk": risk,
            "action_count": len(tasks),
            "same_target_max": max(targets.values(), default=0),
            "active_checks": active,
            "state_changes": state_changes,
            "policy_version": "aggregate-risk/1.0.0",
        }


class PlanProposalValidator:
    def validate(
        self, db: Session, context: DecisionContextRow, proposal: PlanProposalOutput, now: datetime
    ) -> dict[str, Any]:
        env = db.get(EnvironmentRow, context.environment_id)
        incident = db.get(IncidentRow, context.incident_id)
        scope = db.get(ScopeRow, (context.scope_id, context.environment_id))
        assert env is not None and incident is not None
        # A cited proposal is still a hypothesis, not a fact. Check only reference integrity.
        grounding = ClaimGroundingValidator().validate(
            db,
            context,
            SituationOutput(
                incident_summary=proposal.objective,
                supported_findings=[
                    Finding(
                        claim=proposal.reasoning_summary,
                        evidence_refs=proposal.evidence_refs,
                        resource_ids=sorted({t.target_resource_id for t in proposal.proposed_tasks}),
                        observed_at=context.created_at,
                    )
                ],
                hypotheses=[],
                evidence_gaps=[],
                affected_resources=[],
                recommended_next_steps=[],
                risk_observations=[],
                uncertainty="Proposal only; independent verification required",
                confidence_semantics="MODEL_SELF_REPORTED_UNCALIBRATED",
            ),
            now,
        )
        reasons = list(grounding["reasons"])
        if (
            not scope
            or scope.scope_id not in env.scope_ids
            or not scope.valid_from <= now < scope.valid_until
        ):
            reasons.append("inactive_scope")
        allowed = {c["capability_id"]: c for c in context.body["allowed_capabilities"]}
        capabilities: dict[str, CapabilityManifest] = {}
        parameters: dict[str, Any] = {}
        keys = {t.task_key for t in proposal.proposed_tasks}
        if len(keys) != len(proposal.proposed_tasks):
            reasons.append("duplicate_task_key")
        dependencies = {t.task_key: t.dependencies for t in proposal.proposed_tasks}
        visited: set[str] = set()
        active: set[str] = set()

        def visit(key: str) -> None:
            if key not in keys or key in active:
                raise ValueError("invalid DAG")
            if key in visited:
                return
            active.add(key)
            for dep in dependencies[key]:
                visit(dep)
            active.remove(key)
            visited.add(key)

        try:
            for key in keys:
                visit(key)
        except ValueError:
            reasons.append("cyclic_or_missing_dependency")
        for task in proposal.proposed_tasks:
            if len(task.dependencies) != len(set(task.dependencies)):
                reasons.append("duplicate_dependency")
            captured = allowed.get(task.capability_id)
            if not captured:
                reasons.append("hallucinated_or_out_of_context_capability")
                continue
            try:
                cap, config = CapabilityRegistry(db).resolve(task.capability_id, captured["version"])
                capabilities[task.capability_id] = cap
                parameters[task.task_key] = validate_input(
                    task.capability_id, task.parameters.model_dump(exclude_none=True)
                )
            except (DomainError, ValueError):
                reasons.append("capability_definition_or_parameters_invalid")
                continue
            current_hash = canonical_hash(
                {
                    "capability_id": cap.capability_id,
                    "version": cap.version,
                    "input_schema": cap.input_schema,
                    "risk": cap.base_risk.value,
                    "operation": cap.operation_kind,
                }
            )
            if current_hash != captured["definition_hash"]:
                reasons.append("capability_changed_since_context")
            resource = db.get(ResourceRow, (task.target_resource_id, env.environment_id))
            if (
                not resource
                or task.target_resource_id not in context.manifest["resource_ids"]
                or task.target_resource_id not in incident.affected_asset_ids
                or not scope
                or task.target_resource_id not in scope.target_resource_ids
            ):
                reasons.append("invalid_target_or_environment")
            elif resource.resource_type not in config.supported_resource_types:
                reasons.append("unsupported_target_class")
            if (
                not scope
                or task.capability_id not in scope.allowed_capabilities
                or task.capability_id not in env.capability_allowlist
            ):
                reasons.append("capability_outside_current_scope")
            ceiling = min(env.max_auto_risk, "R2" if env.deployment_stage == "LAB" else "R1")
            if cap.base_risk.value > ceiling or cap.base_risk.value >= "R3":
                reasons.append("risk_ceiling_require_approval_or_deny")
            if config.business_impact in {"HIGH", "CRITICAL"}:
                reasons.append("business_impact_require_approval")
            if env.deployment_stage not in config.supported_profiles:
                reasons.append("unsupported_environment_profile")
            if cap.operation_kind == "ACTIVE_CHECK" and (
                env.autonomy_mode not in {"CONTROLLED_AUTONOMY", "VALIDATION"}
                or env.active_validation == "DISABLED"
            ):
                reasons.append("autonomy_require_approval_or_deny")
            health = db.get(
                CapabilityHealthRow, (cap.capability_id, cap.version, env.environment_id, "response")
            )
            if (
                not health
                or health.status != "HEALTHY"
                or not health.checked_at <= now < health.checked_at + timedelta(seconds=120)
            ):
                reasons.append("capability_health_unavailable")
        aggregate = PlanAggregateRiskValidator().validate(proposal, capabilities)
        reasons.extend(aggregate["reasons"])
        return {
            "valid": not reasons,
            "reasons": sorted(set(reasons)),
            "grounding": grounding,
            "aggregate": aggregate,
            "parameters": parameters,
            "validator_version": "plan-proposal/1.0.0",
            "authorization": "NOT_GRANTED",
        }
