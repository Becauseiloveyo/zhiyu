"""AI proposals enter only the existing persisted task graph after deterministic validation."""

import json
from datetime import datetime
from time import perf_counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.ai.gateway import ModelGateway
from zhiyu.ai.outputs import PlanProposalOutput
from zhiyu.ai.plan_validation import PlanProposalValidator
from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ConflictError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.ai_analysis import SituationAnalysisRow
from zhiyu.db.ai_context import DecisionContextRow
from zhiyu.db.ai_gateway import AIIncidentBudgetRow, ModelReceiptRow, ModelRequestRow
from zhiyu.db.ai_planning import AIProposalRow
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import IncidentRow, ModelRunRow, PlanRow, TaskRow
from zhiyu.db.response_planning import ResponsePlanRow, TaskEdgeRow, TaskRuntimeRow
from zhiyu.domain.contracts import AIPlan, Hypothesis, SecurityIncident, Task, TaskStatus
from zhiyu.response.planner import TaskGraphValidator, emit, identity
from zhiyu.verification.runtime import instant, lock_environment


class AIPlanner:
    def __init__(self, engine: Engine, gateway: ModelGateway) -> None:
        self.engine, self.gateway = engine, gateway

    def propose(
        self,
        env: str,
        analysis_id: str,
        principal: ServicePrincipal,
        *,
        parent_verification_id: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        principal.require("ai:plan", env)
        principal.require("response:plan", env)
        with Session(self.engine) as db:
            analysis = db.get(SituationAnalysisRow, analysis_id)
            if not analysis or analysis.environment_id != env:
                raise ReferenceError("analysis not found in environment")
            if analysis.status != "REFERENCE_GROUNDED":
                return {
                    "status": "FALLBACK" if analysis.status == "FALLBACK" else "REJECTED",
                    "plan_id": None,
                    "analysis_id": analysis_id,
                    "reason": "analysis_not_reference_grounded",
                }
            context_id, output = analysis.context_id, analysis.output
        receipt = self.gateway.propose_plan(env, context_id, principal, analysis=output, now=now)
        if receipt["status"] == "IN_PROGRESS":
            return receipt
        return self.record(
            env,
            analysis_id,
            receipt["request_id"],
            principal,
            parent_verification_id=parent_verification_id,
            now=now,
        )

    def record(
        self,
        env: str,
        analysis_id: str,
        request_id: str,
        principal: ServicePrincipal,
        *,
        parent_verification_id: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        principal.require("ai:plan", env)
        principal.require("response:plan", env)
        start = perf_counter()
        with Session(self.engine) as db, db.begin():
            environment = lock_environment(db, env)
            request = db.get(ModelRequestRow, request_id)
            stored = db.get(ModelReceiptRow, request_id)
            analysis = db.get(SituationAnalysisRow, analysis_id)
            if (
                not request
                or not stored
                or not analysis
                or request.environment_id != env
                or analysis.environment_id != env
                or analysis.context_id != request.context_id
                or analysis.status != "REFERENCE_GROUNDED"
                or request.task_type != "PLAN"
            ):
                raise ReferenceError(
                    "proposal requires same-context grounded analysis and durable PLAN receipt"
                )
            # Bind the exact analysis supplied to the model, even for direct record/recovery calls.
            context = db.get(DecisionContextRow, request.context_id)
            assert context is not None
            if request.configuration["policy"] != self.gateway.policy.model_dump(mode="json"):
                raise ConflictError("proposal policy differs from captured gateway policy")
            if canonical_hash(self.gateway._input(context, "PLAN", analysis.output)) != request.input_hash:
                raise ConflictError("proposal analysis differs from model request")
            proposal_id = identity("ai-proposal", request_id)
            previous = db.get(AIProposalRow, proposal_id)
            if previous:
                if (
                    previous.analysis_id != analysis_id
                    or previous.parent_verification_id != parent_verification_id
                ):
                    raise ConflictError("proposal lineage identity changed")
                return self.public(previous)
            at = instant(db, now)
            run = db.get(ModelRunRow, stored.model_run_id) if stored.model_run_id else None
            if run:
                at = max(at, run.finished_at)
            incident = db.get(IncidentRow, context.incident_id)
            assert incident is not None
            version = context.body["incident"]["state_version"]
            receipt = ModelGateway._public(request, stored)
            status = "FALLBACK"
            validation: dict[str, Any] = {
                "valid": False,
                "reasons": [receipt["error_code"]],
                "authorization": "NOT_GRANTED",
            }
            output = receipt["output"]
            plan = None
            if receipt["status"] == "COMPLETED":
                proposal = PlanProposalOutput.model_validate_json(json.dumps(output))
                validation = PlanProposalValidator().validate(db, context, proposal, at)
                if self.gateway.policy.mode == "ASSISTED" and environment.deployment_stage != "LAB":
                    validation["reasons"].append("assisted_mode_requires_lab")
                if parent_verification_id:
                    from zhiyu.ai.replan import validate_replan

                    validation["reasons"].extend(
                        validate_replan(db, context, proposal, parent_verification_id, at, principal)
                    )
                elif incident.status not in {"TRIAGED", "INVESTIGATING"}:
                    validation["reasons"].append("incident_not_ready_for_initial_plan")
                elif self.gateway.policy.mode == "ASSISTED" and db.scalar(
                    select(ResponsePlanRow.plan_id)
                    .where(
                        ResponsePlanRow.environment_id == env,
                        ResponsePlanRow.incident_id == incident.incident_id,
                    )
                    .limit(1)
                ):
                    validation["reasons"].append("existing_plan_lineage")
                validation["valid"] = not validation["reasons"]
                status = (
                    "REJECTED"
                    if not validation["valid"]
                    else "SHADOW"
                    if self.gateway.policy.mode == "SHADOW"
                    else "ACCEPTED"
                )
                if status == "ACCEPTED":
                    if parent_verification_id:
                        from zhiyu.verification.lifecycle import move

                        move(
                            db,
                            incident,
                            "INVESTIGATING",
                            at,
                            principal.principal_id,
                            "independent verification requires bounded AI replan",
                        )
                    plan = self._save_plan(
                        db, context, analysis, proposal, validation, stored, incident, principal, at
                    )
                    if parent_verification_id:
                        from zhiyu.ai.replan import accept_replan

                        accept_replan(db, plan, parent_verification_id, incident, principal, at)
            elif receipt["error_code"] in {"SCHEMA_INVALID", "UNSAFE_MODEL_OUTPUT", "TOOL_CALL_REJECTED"}:
                status = "REJECTED"
            row = AIProposalRow(
                proposal_id=proposal_id,
                environment_id=env,
                incident_id=incident.incident_id,
                incident_version=version,
                context_id=context.context_id,
                analysis_id=analysis_id,
                request_id=request_id,
                model_run_id=stored.model_run_id,
                parent_verification_id=parent_verification_id,
                plan_id=plan.plan_id if plan else None,
                mode=self.gateway.policy.mode,
                status=status,
                output=output,
                validation=validation,
                created_at=at,
                planning_ms=(perf_counter() - start) * 1000,
            )
            db.add(row)
            emit(
                db,
                env,
                "PlanProposal",
                proposal_id,
                "PlanProposalCreated",
                "AI output grants no authorization",
                principal.principal_id,
            )
            emit(
                db,
                env,
                "PlanProposal",
                proposal_id,
                "PlanProposalAccepted"
                if status == "ACCEPTED"
                else "PlanProposalRejected"
                if status == "REJECTED"
                else "PlanProposalShadow"
                if status == "SHADOW"
                else "ModelFallbackTriggered",
                status,
                principal.principal_id,
            )
            return self.public(row)

    def _save_plan(
        self,
        db: Session,
        context: DecisionContextRow,
        analysis: SituationAnalysisRow,
        proposal: PlanProposalOutput,
        validation: dict[str, Any],
        receipt: ModelReceiptRow,
        incident: IncidentRow,
        principal: ServicePrincipal,
        at: datetime,
    ) -> AIPlan:
        plan_id = identity("ai-plan", receipt.request_id)
        caps = {c["capability_id"]: c for c in context.body["allowed_capabilities"]}
        ids = {t.task_key: identity("task", [plan_id, t.task_key]) for t in proposal.proposed_tasks}
        tasks = [
            Task(
                task_id=ids[t.task_key],
                incident_id=incident.incident_id,
                environment_id=incident.environment_id,
                dependencies=[ids[d] for d in t.dependencies],
                capability_id=t.capability_id,
                capability_version=caps[t.capability_id]["version"],
                target_resource_ids=[t.target_resource_id],
                scope_id=context.scope_id,
                parameters=validation["parameters"][t.task_key],
                status=TaskStatus.QUEUED,
                priority=contract_from(incident, SecurityIncident).priority,
                timeout_seconds=5,
                max_attempts=1,
                attempt_count=0,
                expected_output="Execution receipt only; independent three-dimension verification required",
                evidence_ids=sorted(incident.evidence_ids),
                created_at=at,
                queued_at=at,
            )
            for t in proposal.proposed_tasks
        ]
        budget = db.get(AIIncidentBudgetRow, incident.incident_id)
        plan = AIPlan(
            plan_id=plan_id,
            incident_id=incident.incident_id,
            environment_id=incident.environment_id,
            context_id=context.context_id,
            model_run_id=receipt.model_run_id,
            hypotheses=[
                Hypothesis(
                    hypothesis_id=identity("model-plan-hypothesis", plan_id),
                    claim=proposal.reasoning_summary,
                    evidence_ids=proposal.evidence_refs,
                    counter_evidence_ids=[],
                    missing_evidence=["Independent security/business/observation verification"],
                    model_confidence=None,
                )
            ],
            tasks=tasks,
            stop_conditions=[
                "scope/policy stale",
                "authorization denied",
                "budget exhausted",
                "independent verification governs result",
            ],
            max_replans=2,
            total_model_calls=budget.call_count if budget else 0,
        )
        TaskGraphValidator().validate(db, plan, at)
        db.add(PlanRow(**values_for(plan, PlanRow)))
        db.flush()
        snapshot = contract_from(incident, SecurityIncident).model_dump(mode="json")
        db.add(
            ResponsePlanRow(
                plan_id=plan_id,
                environment_id=incident.environment_id,
                incident_id=incident.incident_id,
                incident_version=incident.state_version,
                planner_version="ai-proposal/1.0.0",
                policy_version=self.gateway.policy.version,
                scope_id=context.scope_id,
                snapshot_hash=canonical_hash(snapshot),
                inputs={
                    "incident": snapshot,
                    "analysis_id": analysis.analysis_id,
                    "model_request_id": receipt.request_id,
                },
                configuration=self.gateway.policy.model_dump(mode="json"),
                reasons=["Validated proposal; fresh authorization required"],
                created_by=principal.principal_id,
                created_at=at,
                generation_ms=0,
                graph_ms=0,
            )
        )
        db.flush()
        for task in tasks:
            db.add(TaskRow(**values_for(task, TaskRow)))
        db.flush()
        for task in tasks:
            db.add(
                TaskRuntimeRow(
                    task_id=task.task_id,
                    environment_id=task.environment_id,
                    plan_id=plan_id,
                    task_type="READ_ONLY_PROBE"
                    if caps[task.capability_id]["operation_kind"] == "ACTIVE_CHECK"
                    else "PASSIVE_CONTEXT",
                    ready_at=at,
                    failure_code=None,
                    result_ref=None,
                    generation=0,
                )
            )
        db.flush()
        for task in tasks:
            for dependency in task.dependencies:
                db.add(
                    TaskEdgeRow(
                        environment_id=task.environment_id,
                        plan_id=plan_id,
                        task_id=task.task_id,
                        depends_on=dependency,
                    )
                )
            emit(
                db,
                task.environment_id,
                "Task",
                task.task_id,
                "TaskCreated",
                "AI proposal validated; no authorization granted",
                principal.principal_id,
            )
        emit(
            db,
            plan.environment_id,
            "AIPlan",
            plan_id,
            "PlanCreated",
            "Existing task graph; authorization and verification mandatory",
            principal.principal_id,
        )
        return plan

    @staticmethod
    def public(row: AIProposalRow) -> dict[str, Any]:
        return {
            key: getattr(row, key)
            for key in (
                "proposal_id",
                "context_id",
                "analysis_id",
                "model_run_id",
                "plan_id",
                "parent_verification_id",
                "mode",
                "status",
                "output",
                "validation",
            )
        }
