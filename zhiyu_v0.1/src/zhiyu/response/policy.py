"""Pure deterministic scope and risk decisions. No executor is reachable here."""

from datetime import datetime
from typing import Any, Literal

from zhiyu.domain.contracts import (
    ActionRequest,
    AuthorizationContext,
    AuthorizationDecision,
    CapabilityManifest,
    EnvironmentProfile,
    ResourceRef,
    ScopeDefinition,
)
from zhiyu.response.catalog import validate_input
from zhiyu.response.config import ResponsePolicy


class ScopeEvaluator:
    def evaluate(
        self,
        action: ActionRequest,
        environment: EnvironmentProfile,
        scope: ScopeDefinition,
        target: ResourceRef,
        source: ResourceRef | None,
        capability: CapabilityManifest,
        supported_types: list,
        now: datetime,
    ) -> list[str]:
        reasons = []
        if any(
            value != action.environment_id
            for value in [environment.environment_id, scope.environment_id, target.environment_id]
        ):
            reasons.append("environment_mismatch")
        if action.scope_id != scope.scope_id or scope.scope_id not in environment.scope_ids:
            reasons.append("scope_mismatch")
        if not scope.valid_from <= now < scope.valid_until:
            reasons.append("scope_expired")
        if action.scope_version != scope.version or action.environment_profile_version != environment.version:
            reasons.append("scope_or_profile_version_mismatch")
        if target != action.target or target.resource_id not in scope.target_resource_ids:
            reasons.append("target_not_authorized")
        if target.resource_type not in supported_types:
            reasons.append("resource_type_unsupported")
        if (
            capability.capability_id not in scope.allowed_capabilities
            or capability.capability_id not in environment.capability_allowlist
        ):
            reasons.append("capability_outside_scope")
        if (
            action.capability_id != capability.capability_id
            or action.capability_version != capability.version
        ):
            reasons.append("capability_version_mismatch")
        try:
            validate_input(capability.capability_id, action.parameters)
        except ValueError:
            reasons.append("invalid_structured_parameters")
        if capability.operation_kind != "PASSIVE_READ":
            if source is None or action.source != source or source.environment_id != action.environment_id:
                reasons.append("source_identity_mismatch")
            elif source.resource_id not in scope.capability_source_ids.get(capability.capability_id, []):
                reasons.append("source_not_authorized")
            elif not any(
                source.resource_id in rule.source_resource_ids
                and target.resource_id in rule.target_resource_ids
                and target.locator.get("port") in rule.destination_ports
                and target.locator.get("protocol") in rule.protocols
                for rule in scope.network_constraints
            ):
                reasons.append("network_path_not_authorized")
        return reasons


class RiskPolicyGate:
    def decide(
        self,
        context: AuthorizationContext,
        facts: dict[str, Any],
        policy: ResponsePolicy,
        *,
        decision_id: str,
        valid_until: datetime,
    ) -> AuthorizationDecision:
        denied = list(facts.get("denied_dimensions", []))
        required = False
        risk = int(context.requested_risk.value[1:])
        if facts["capability_health"] != "HEALTHY":
            denied.append("capability_unavailable")
        if context.sensor_health_status != "HEALTHY":
            denied.append("sensor_health_below_threshold")
        if context.evidence_quality != "HIGH":
            denied.append("evidence_quality_insufficient")
        if context.business_impact in {"HIGH", "CRITICAL"} or context.asset_criticality == "CRITICAL":
            denied.append("business_impact_too_high")
            required = True
        if risk >= 3:
            denied.append("high_risk_autonomous_action_denied")
            required = risk == 5 or required
        active = facts["operation_kind"] != "PASSIVE_READ"
        if active and context.autonomy_mode == "OBSERVE_ONLY":
            denied.append("insufficient_autonomy")
        if active and context.autonomy_mode == "ASSISTED":
            required = True
        if active and facts["active_validation"] == "DISABLED":
            denied.append("active_validation_disabled")
        if risk == 2 and facts["deployment_stage"] != "LAB":
            required = True
        if risk == 2 and facts["deployment_stage"] == "LAB" and not policy.allow_lab_r2:
            denied.append("lab_r2_not_enabled")
        if risk > int(facts["max_auto_risk"][1:]):
            required = True
        if active and facts["asset_domain"] in {"OT", "MIXED"}:
            denied.append("active_ot_not_supported")
        reasons = sorted(set(denied))
        outcome: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"] = (
            "DENY" if reasons else "REQUIRE_APPROVAL" if required else "ALLOW"
        )
        if not reasons:
            reasons = (
                ["explicit_approval_required_no_execution"]
                if required
                else ["scoped_low_risk_execution_allowed"]
            )
        return AuthorizationDecision(
            authorization_id=decision_id,
            authorization_context_id=context.authorization_context_id,
            action_id=context.action_id,
            action_digest=context.action_digest,
            outcome=outcome,
            assessed_risk=context.requested_risk,
            business_impact=context.business_impact,
            human_approval_required=required,
            approval_id=None,
            policy_version=context.policy_version,
            valid_until=valid_until,
            reasons=reasons,
        )
