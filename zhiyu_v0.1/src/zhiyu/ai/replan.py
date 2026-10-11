"""Bounded AI replan admission into the same v0.4 cycle/decision/budget tables."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.ai.outputs import PlanProposalOutput
from zhiyu.core.canonical import canonical_hash
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.ai_context import DecisionContextRow
from zhiyu.db.models import IncidentRow, PlanRow, VerificationResultRow
from zhiyu.db.verification_replan import ReplanBudgetRow, ReplanDecisionRow, ResponseCycleRow
from zhiyu.db.verification_runtime import VerificationObservationRow, VerificationRuntimeRow
from zhiyu.domain.contracts import AIPlan
from zhiyu.response.catalog import validate_input
from zhiyu.response.planner import emit
from zhiyu.verification.lifecycle import move, semantic_hash
from zhiyu.verification.replan import ReplanBudget, update_state


def evidence_fingerprint(db: Session, spec_id: str) -> str:
    rows = list(
        db.scalars(
            select(VerificationObservationRow)
            .where(VerificationObservationRow.spec_id == spec_id)
            .order_by(VerificationObservationRow.check_id)
        )
    )
    return canonical_hash(
        [
            {
                "check": o.check_id,
                "data": [
                    {k: v for k, v in sample.items() if k not in {"latency_ms", "endpoint"}}
                    for sample in o.samples
                ],
            }
            for o in rows
        ]
    )


def action_fingerprint(tasks: list[dict[str, Any]]) -> str:
    return canonical_hash(
        sorted(
            [
                {
                    "capability": t["capability_id"],
                    "targets": sorted(t["target_resource_ids"]),
                    "parameters": t["parameters"],
                    "scope": t["scope_id"],
                }
                for t in tasks
            ],
            key=canonical_hash,
        )
    )


def validate_replan(
    db: Session,
    context: DecisionContextRow,
    proposal: PlanProposalOutput,
    verification_id: str,
    at: datetime,
    principal: ServicePrincipal,
) -> list[str]:
    principal.require("verification:replan", context.environment_id)
    principal.require("verification:write", context.environment_id)
    result = db.get(VerificationResultRow, verification_id)
    if (
        not result
        or result.environment_id != context.environment_id
        or result.incident_id != context.incident_id
        or verification_id not in context.manifest["verification_ids"]
    ):
        return ["verification_outside_replan_context"]
    runtime = db.get(VerificationRuntimeRow, result.verification_spec_id)
    cycle = db.get(ResponseCycleRow, runtime.plan_id) if runtime else None
    if not cycle:
        return ["missing_continuous_verification_cycle"]
    budget = db.get(ReplanBudgetRow, cycle.root_plan_id)
    assert budget is not None
    policy = ReplanBudget.model_validate(budget.configuration)
    incident = db.get(IncidentRow, context.incident_id)
    assert incident is not None
    reasons = []
    if incident.status != "VERIFYING" or incident.state_version != cycle.expected_version:
        reasons.append("stale_verification_cycle")
    if result.status == "PASS" or result.valid_until <= at:
        reasons.append("verification_requires_no_replan_or_expired")
    if db.get(ReplanDecisionRow, verification_id):
        reasons.append("verification_already_replanned")
    if (
        budget.current_replan_count >= policy.max_replans
        or budget.reserved_actions + len(proposal.proposed_tasks) > policy.max_total_actions
        or (at - budget.started_at).total_seconds() >= policy.max_elapsed_time
    ):
        reasons.append("root_replan_budget_exhausted")
    allowed = {c["capability_id"]: c for c in context.body["allowed_capabilities"]}
    if any(
        t.capability_id in allowed and allowed[t.capability_id]["risk"] > policy.risk_ceiling
        for t in proposal.proposed_tasks
    ):
        reasons.append("replan_risk_escalation")
    observations = list(
        db.scalars(
            select(VerificationObservationRow).where(
                VerificationObservationRow.spec_id == result.verification_spec_id
            )
        )
    )
    if not observations or not any(o.samples for o in observations):
        reasons.append("no_independent_observation")
    fingerprint = evidence_fingerprint(db, result.verification_spec_id)
    if db.scalar(
        select(ReplanDecisionRow.verification_id)
        .where(
            ReplanDecisionRow.root_plan_id == cycle.root_plan_id,
            ReplanDecisionRow.evidence_fingerprint == fingerprint,
            ReplanDecisionRow.status == "CREATED",
        )
        .limit(1)
    ):
        reasons.append("no_new_semantic_evidence")
    try:
        candidate = action_fingerprint(
            [
                {
                    "capability_id": t.capability_id,
                    "target_resource_ids": [t.target_resource_id],
                    "parameters": validate_input(t.capability_id, t.parameters.model_dump(exclude_none=True)),
                    "scope_id": context.scope_id,
                }
                for t in proposal.proposed_tasks
            ]
        )
        if any(
            action_fingerprint(plan.tasks) == candidate
            for plan in db.scalars(
                select(PlanRow).where(
                    PlanRow.environment_id == context.environment_id,
                    PlanRow.incident_id == context.incident_id,
                )
            )
        ):
            reasons.append("repeated_plan_or_action_fingerprint")
    except ValueError:
        reasons.append("invalid_replan_parameters")
    return reasons


def accept_replan(
    db: Session,
    plan: AIPlan,
    verification_id: str,
    incident: IncidentRow,
    principal: ServicePrincipal,
    at: datetime,
) -> None:
    result = db.get(VerificationResultRow, verification_id)
    assert result is not None
    runtime = db.get(VerificationRuntimeRow, result.verification_spec_id)
    assert runtime is not None
    cycle = db.get(ResponseCycleRow, runtime.plan_id)
    assert cycle is not None
    budget = db.get(ReplanBudgetRow, cycle.root_plan_id)
    assert budget is not None
    update_state(db, result, runtime, at, principal.principal_id)
    incident.residual_risks = result.residual_risks
    budget.current_replan_count += 1
    budget.reserved_actions += len(plan.tasks)
    move(
        db,
        incident,
        "PLANNED",
        at,
        principal.principal_id,
        "validated bounded AI proposal; fresh authorization required",
    )
    db.add(
        ResponseCycleRow(
            plan_id=plan.plan_id,
            environment_id=plan.environment_id,
            incident_id=plan.incident_id,
            expected_version=incident.state_version,
            semantic_hash=semantic_hash(incident),
            root_plan_id=cycle.root_plan_id,
            parent_plan_id=cycle.plan_id,
            created_at=at,
        )
    )
    fp = action_fingerprint([t.model_dump(mode="json") for t in plan.tasks])
    db.add(
        ReplanDecisionRow(
            verification_id=verification_id,
            root_plan_id=cycle.root_plan_id,
            parent_plan_id=cycle.plan_id,
            new_plan_id=plan.plan_id,
            status="CREATED",
            reason="Validated AI proposal; independent verification governs result",
            replan_count=budget.current_replan_count,
            policy_version=budget.configuration["policy_version"],
            plan_fingerprint=canonical_hash([fp, result.status]),
            action_fingerprint=fp,
            evidence_fingerprint=evidence_fingerprint(db, result.verification_spec_id),
            created_at=at,
            latency_ms=0,
        )
    )
    emit(
        db,
        plan.environment_id,
        "Replan",
        verification_id,
        "ReplanCreated",
        "Bounded AI proposal; no risk escalation",
        principal.principal_id,
    )
