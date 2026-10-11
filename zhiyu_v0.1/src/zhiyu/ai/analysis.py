"""Situation analysis uses only captured context; validator checks referenced records."""

import json
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.ai.gateway import ModelGateway, context_current
from zhiyu.ai.outputs import SituationOutput
from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.ai_analysis import SituationAnalysisRow
from zhiyu.db.ai_context import DecisionContextRow
from zhiyu.db.mapping import values_for
from zhiyu.db.models import EvidenceRow, ModelRunRow, ResourceRow, StateEntityRow
from zhiyu.domain.contracts import StateEntity
from zhiyu.response.planner import emit, identity
from zhiyu.verification.runtime import instant, lock_environment


class ClaimGroundingValidator:
    """Citation integrity and temporal compatibility, not unrestricted semantic truth."""

    def validate(
        self, db: Session, context: DecisionContextRow, output: SituationOutput, now: datetime
    ) -> dict[str, Any]:
        env = lock_environment(db, context.environment_id)
        reasons: list[str] = []
        if not context_current(db, context, env, now):
            reasons.append("stale_context")
        allowed_facts = {f["evidence_id"]: f for f in context.body["trusted_facts"]}
        allowed_resources = set(context.manifest["resource_ids"])
        refs = {e for f in output.supported_findings for e in f.evidence_refs} | {
            e for h in output.hypotheses for e in h.evidence_refs
        }
        checked: dict[str, EvidenceRow] = {}
        for ref in sorted(refs):
            evidence = db.get(EvidenceRow, ref)
            if not evidence or ref not in allowed_facts:
                reasons.append("hallucinated_or_out_of_context_evidence")
                continue
            fact = allowed_facts[ref]
            if (
                evidence.environment_id != context.environment_id
                or evidence.incident_id != context.incident_id
            ):
                reasons.append("cross_environment_or_incident_evidence")
                continue
            if evidence.claim_kind not in {"OBSERVATION", "SOURCE_ASSERTION"}:
                reasons.append("inference_is_not_observed_evidence")
            if evidence.trust_status != "VERIFIED_ORIGIN" or evidence.contradicts:
                reasons.append("conflicting_or_untrusted_evidence")
            until = min(evidence.valid_until, datetime.fromisoformat(fact["valid_until"]))
            if not evidence.observed_at <= now < until:
                reasons.append("stale_or_future_evidence")
            if (
                evidence.observed_at.isoformat() != fact["observed_at"]
                or evidence.collector_id != fact["source"]
                or canonical_hash(
                    {
                        "integrity_hash": evidence.integrity_hash,
                        "supports": evidence.supports,
                        "source_event_ids": evidence.source_event_ids,
                        "collected_at": evidence.collected_at.isoformat(),
                    }
                )
                != fact.get("source_hash")
            ):
                reasons.append("evidence_provenance_changed")
            checked[ref] = evidence
        resources = set(output.affected_resources) | {
            r for f in output.supported_findings for r in f.resource_ids
        }
        for resource_id in sorted(resources):
            if (
                resource_id not in allowed_resources
                or db.get(ResourceRow, (resource_id, context.environment_id)) is None
            ):
                reasons.append("hallucinated_or_out_of_scope_resource")
        for finding in output.supported_findings:
            support = [checked[r] for r in finding.evidence_refs if r in checked]
            if len(support) != len(set(finding.evidence_refs)) or not support:
                reasons.append("unsupported_finding")
            elif not min(e.observed_at for e in support) <= finding.observed_at <= context.created_at:
                reasons.append("incompatible_claim_timestamp")
        return {
            "valid": not reasons,
            "reasons": sorted(set(reasons)),
            "validated_evidence_ids": sorted(checked),
            "validated_resource_ids": sorted(resources & allowed_resources),
            "supported_finding_count": len(output.supported_findings),
            "hypothesis_count": len(output.hypotheses),
            "semantics": "REFERENCE_INTEGRITY_ONLY_NOT_NATURAL_LANGUAGE_TRUTH",
            "confidence_semantics": "MODEL_SELF_REPORTED_UNCALIBRATED",
            "validator_version": "claim-grounding/1.0.0",
        }


class AISituationAnalyzer:
    def __init__(self, engine: Engine, gateway: ModelGateway) -> None:
        self.engine, self.gateway = engine, gateway

    def analyze(
        self, env: str, context_id: str, principal: ServicePrincipal, *, now: datetime | None = None
    ) -> dict[str, Any]:
        principal.require("ai:analyze", env)
        receipt = self.gateway.analyze(env, context_id, principal, now=now)
        if receipt["status"] == "IN_PROGRESS":
            return receipt
        return self.record(env, receipt, principal, now=now)

    def record(
        self, env: str, receipt: dict[str, Any], principal: ServicePrincipal, *, now: datetime | None = None
    ) -> dict[str, Any]:
        principal.require("ai:analyze", env)
        with Session(self.engine) as db, db.begin():
            lock_environment(db, env)
            context = db.get(DecisionContextRow, receipt["context_id"])
            if not context or context.environment_id != env:
                raise ReferenceError("analysis context not found in environment")
            # Only the durable gateway receipt is authoritative, never a caller-supplied output.
            from zhiyu.db.ai_gateway import ModelReceiptRow, ModelRequestRow

            request = db.get(ModelRequestRow, receipt["request_id"])
            stored = db.get(ModelReceiptRow, receipt["request_id"])
            if (
                not request
                or not stored
                or request.environment_id != env
                or request.context_id != context.context_id
                or request.task_type != "ANALYSIS"
            ):
                raise ReferenceError("analysis requires persisted ANALYSIS receipt")
            receipt = ModelGateway._public(request, stored)
            analysis_id = identity("situation-analysis", request.request_id)
            old = db.get(SituationAnalysisRow, analysis_id)
            if old:
                return self._public(old)
            at = instant(db, now)
            run = db.get(ModelRunRow, stored.model_run_id) if stored.model_run_id else None
            if run:
                at = max(at, run.finished_at)
            start = perf_counter()
            output = receipt["output"]
            grounding: dict[str, Any] = {
                "valid": False,
                "reasons": [receipt["error_code"] or "model_unavailable"],
                "semantics": "REFERENCE_INTEGRITY_ONLY_NOT_NATURAL_LANGUAGE_TRUTH",
            }
            status = "FALLBACK"
            if receipt["status"] == "COMPLETED":
                data = SituationOutput.model_validate_json(json.dumps(output))
                grounding = ClaimGroundingValidator().validate(db, context, data, at)
                status = "REFERENCE_GROUNDED" if grounding["valid"] else "REJECTED"
            state_id = None
            if status == "REFERENCE_GROUNDED":
                state_id = identity("model-inference-state", analysis_id)
                state = StateEntity(
                    entity_id=state_id,
                    environment_id=env,
                    entity_type="AI_SITUATION_ANALYSIS",
                    state_version=1,
                    claim_kind="INFERENCE",
                    attributes={
                        "source_type": "MODEL_INFERENCE",
                        "analysis_id": analysis_id,
                        "model_run_id": stored.model_run_id,
                        "incident_id": context.incident_id,
                        "analysis": output,
                        "grounding_semantics": grounding["semantics"],
                        "confidence_semantics": "MODEL_SELF_REPORTED_UNCALIBRATED",
                        "evidence_link_semantics": "context inputs; not proof of model conclusions",
                    },
                    evidence_ids=context.manifest["evidence_ids"],
                    observed_at=at,
                    valid_until=min(context.valid_until, at + timedelta(seconds=120)),
                )
                db.add(StateEntityRow(**values_for(state, StateEntityRow)))
                db.flush()
            row = SituationAnalysisRow(
                analysis_id=analysis_id,
                environment_id=env,
                incident_id=context.incident_id,
                context_id=context.context_id,
                request_id=request.request_id,
                model_run_id=stored.model_run_id,
                state_entity_id=state_id,
                status=status,
                output=output,
                grounding=grounding,
                created_at=at,
                grounding_ms=(perf_counter() - start) * 1000,
            )
            db.add(row)
            emit(
                db,
                env,
                "SituationAnalysis",
                analysis_id,
                "SituationAnalysisCreated",
                status + "; MODEL_INFERENCE only",
                principal.principal_id,
            )
            if status == "REJECTED":
                emit(
                    db,
                    env,
                    "SituationAnalysis",
                    analysis_id,
                    "SituationAnalysisRejected",
                    ";".join(grounding["reasons"]),
                    principal.principal_id,
                )
            return self._public(row)

    @staticmethod
    def _public(row: SituationAnalysisRow) -> dict[str, Any]:
        return {
            "analysis_id": row.analysis_id,
            "context_id": row.context_id,
            "model_run_id": row.model_run_id,
            "status": row.status,
            "output": row.output,
            "grounding": row.grounding,
            "state_entity_id": row.state_entity_id,
        }
