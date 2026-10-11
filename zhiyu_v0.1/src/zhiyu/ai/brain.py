"""Single decision coordinator; execution stays in the unchanged response worker."""

from dataclasses import asdict
from datetime import datetime
from time import perf_counter
from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.ai.analysis import AISituationAnalyzer
from zhiyu.ai.gateway import ModelGateway
from zhiyu.ai.planner import AIPlanner
from zhiyu.core.errors import ConflictError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.ai_context import DecisionContextRow
from zhiyu.db.ai_decisions import AIDecisionRow
from zhiyu.db.models import EnvironmentRow, PlanRow
from zhiyu.db.response_planning import ResponsePlanRow
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy, emit, identity
from zhiyu.verification.replan import DeterministicReplanner, ReplanBudget, activate
from zhiyu.verification.runtime import instant, lock_environment


class DecisionBrain:
    def __init__(self, engine: Engine, gateway: ModelGateway) -> None:
        self.engine, self.gateway = engine, gateway

    def decide(
        self, env: str, context_id: str, principal: ServicePrincipal, *, now: datetime | None = None
    ) -> dict[str, Any]:
        for permission in ("ai:analyze", "ai:plan", "response:plan", "verification:write", "incidents:write"):
            principal.require(permission, env)
        started = perf_counter()
        with Session(self.engine) as db:
            context = db.get(DecisionContextRow, context_id)
            if not context or context.environment_id != env:
                raise ReferenceError("context not found in environment")
            previous = db.get(AIDecisionRow, context_id)
            if previous:
                return previous.receipt
            incident_id, scope_id = context.incident_id, context.scope_id
            version = context.body["incident"]["state_version"]
            if context.body["incident"]["status"] not in {"TRIAGED", "INVESTIGATING"}:
                raise ConflictError("use bounded replan for an existing response cycle")
        analysis = AISituationAnalyzer(self.engine, self.gateway).analyze(env, context_id, principal, now=now)
        if analysis["status"] == "IN_PROGRESS":
            return analysis
        proposal = AIPlanner(self.engine, self.gateway).propose(
            env, analysis["analysis_id"], principal, now=now
        )
        if proposal["status"] == "IN_PROGRESS":
            return proposal
        fallback_start = perf_counter()
        plan_id = proposal.get("plan_id")
        status = "AI_ASSISTED" if plan_id else "REJECTED"
        fallback_ms = 0.0
        if proposal["status"] in {"FALLBACK", "SHADOW"}:
            status = "SHADOW" if proposal["status"] == "SHADOW" else "DETERMINISTIC_FALLBACK"
            policy = PlannerPolicy(max_replans=2)
            plan_id = identity(
                "plan", [env, incident_id, version, policy.planner_version, policy.policy_version]
            )
            with Session(self.engine) as db:
                existing = self._existing_fallback(db, plan_id, env, incident_id, version, scope_id, policy)
            if not existing:
                try:
                    with Session(self.engine) as db:
                        DeterministicResponsePlanner(db, policy).create(
                            env,
                            incident_id,
                            expected_version=version,
                            scope_id=scope_id,
                            principal=principal,
                            now=now,
                        )
                except ConflictError:
                    # A concurrent identical deterministic request may have activated the committed plan.
                    with Session(self.engine) as db:
                        if not self._existing_fallback(
                            db, plan_id, env, incident_id, version, scope_id, policy
                        ):
                            raise
            fallback_ms = (perf_counter() - fallback_start) * 1000
        if plan_id:
            with Session(self.engine) as db:
                profile = db.get(EnvironmentRow, env)
                assert profile is not None
                ceiling = min(profile.max_auto_risk, "R2")
            activate(self.engine, env, plan_id, principal, ReplanBudget(risk_ceiling=ceiling), now=now)
        receipt = {
            "context_id": context_id,
            "analysis_id": analysis["analysis_id"],
            "proposal_id": proposal.get("proposal_id"),
            "plan_id": plan_id,
            "status": status,
            "execution": "AWAIT_EXISTING_AUTHORIZATION_AND_WORKER",
            "verification": "INDEPENDENT_REQUIRED",
        }
        with Session(self.engine) as db, db.begin():
            lock_environment(db, env)
            previous = db.get(AIDecisionRow, context_id)
            if previous:
                return previous.receipt
            db.add(
                AIDecisionRow(
                    context_id=context_id,
                    environment_id=env,
                    incident_id=incident_id,
                    status=status,
                    plan_id=plan_id,
                    receipt=receipt,
                    created_at=instant(db, now),
                    decision_ms=(perf_counter() - started) * 1000,
                    fallback_ms=fallback_ms,
                )
            )
            emit(
                db,
                env,
                "AIDecision",
                context_id,
                "ModelFallbackTriggered" if status == "DETERMINISTIC_FALLBACK" else "AIDecisionCompleted",
                status,
                principal.principal_id,
            )
        return receipt

    @staticmethod
    def _existing_fallback(
        db: Session,
        plan_id: str,
        env: str,
        incident_id: str,
        version: int,
        scope_id: str,
        policy: PlannerPolicy,
    ) -> bool:
        if not db.get(PlanRow, plan_id):
            return False
        metadata = db.get(ResponsePlanRow, plan_id)
        if (
            metadata is None
            or metadata.environment_id != env
            or metadata.incident_id != incident_id
            or metadata.incident_version != version
            or metadata.scope_id != scope_id
            or metadata.configuration != asdict(policy)
        ):
            raise ConflictError("fallback identity reused with different inputs")
        return True

    def replan(
        self,
        env: str,
        context_id: str,
        verification_id: str,
        principal: ServicePrincipal,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        principal.require("verification:replan", env)
        analysis = AISituationAnalyzer(self.engine, self.gateway).analyze(env, context_id, principal, now=now)
        if analysis["status"] == "IN_PROGRESS":
            return analysis
        proposal = AIPlanner(self.engine, self.gateway).propose(
            env, analysis["analysis_id"], principal, parent_verification_id=verification_id, now=now
        )
        if proposal["status"] in {"FALLBACK", "SHADOW"}:
            fallback = DeterministicReplanner(self.engine).handle(env, verification_id, principal, now=now)
            return {"proposal": proposal, "deterministic_replan": fallback}
        return {"proposal": proposal}
