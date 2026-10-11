"""Evidence qualification precedes ai.5 verdict aggregation; never reads action success."""

from datetime import datetime, timedelta
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import EvidenceRow, ScopeRow, SensorHealthRow, VerificationResultRow, VerificationSpecRow
from zhiyu.db.verification_decisions import EffectivenessRow
from zhiyu.db.verification_runtime import VerificationObservationRow, VerificationRuntimeRow
from zhiyu.domain.contracts import Evidence, Verdict, VerificationResult, VerificationSpec, expected_verdict
from zhiyu.response.planner import emit, identity
from zhiyu.verification.policy import VerificationPolicy
from zhiyu.verification.runtime import instant, lock_environment, observation_health


class VerificationEngine:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def decide(
        self, env: str, spec_id: str, principal: ServicePrincipal, *, now: datetime | None = None
    ) -> VerificationResult:
        principal.require("verification:write", env)
        start = perf_counter()
        with Session(self.engine) as db, db.begin():
            environment = lock_environment(db, env)
            runtime = db.get(VerificationRuntimeRow, spec_id)
            if not runtime or runtime.environment_id != env:
                raise ReferenceError("verification not found in environment")
            verification_id = identity("verification", spec_id)
            prior = db.get(VerificationResultRow, verification_id)
            if prior:
                return contract_from(prior, VerificationResult)
            ts = instant(db, now)
            spec_row = db.get(VerificationSpecRow, spec_id)
            assert spec_row is not None
            spec = contract_from(spec_row, VerificationSpec)
            policy = VerificationPolicy.model_validate(runtime.policy)
            observations = {
                r.check_id: r
                for r in db.scalars(
                    select(VerificationObservationRow).where(VerificationObservationRow.spec_id == spec_id)
                )
            }
            problems: list[str] = []
            scope = db.get(ScopeRow, (runtime.scope_id, env))
            if (
                not scope
                or scope.version != runtime.binding["scope_version"]
                or environment.version != runtime.binding["environment_version"]
                or runtime.scope_id not in environment.scope_ids
                or not scope.valid_from <= ts < scope.valid_until
            ):
                problems.append("decision_scope_or_environment_changed")
            support_deadlines = [runtime.valid_until]
            if spec.objective_type == "CONTAINMENT" and not policy.start_after_seconds:
                deadline = runtime.binding.get("containment_until")
                if not deadline or datetime.fromisoformat(deadline) <= ts:
                    problems.append("containment_expired_fresh_recheck_required")
                else:
                    support_deadlines.append(datetime.fromisoformat(deadline))
            for evidence_id in runtime.binding["input_evidence_ids"]:
                input_evidence = db.get(EvidenceRow, evidence_id)
                if input_evidence:
                    support_deadlines.append(input_evidence.valid_until)
            for sensor_id in set(runtime.binding["sensor_ids"]) | set(environment.required_sensor_ids):
                sensor = db.get(SensorHealthRow, (sensor_id, env))
                if sensor:
                    support_deadlines.append(
                        sensor.last_heartbeat_at + timedelta(seconds=policy.sensor_ttl_seconds)
                    )
                    if sensor.last_event_at:
                        support_deadlines.append(
                            sensor.last_event_at + timedelta(seconds=policy.sensor_ttl_seconds)
                        )
            health = observation_health(db, runtime, environment, ts)
            if not all(health[k] for k in ("sensors_healthy", "telemetry_complete", "evidence_fresh")):
                problems.append("sensor_or_input_evidence_unqualified")
            if (
                runtime.valid_until <= ts
                or (
                    ts
                    - datetime.fromisoformat(
                        runtime.binding.get("not_before", runtime.created_at.isoformat())
                    )
                ).total_seconds()
                < policy.minimum_window_seconds
            ):
                problems.append("verification_window_incomplete_or_expired")
            if canonical_hash(spec.model_dump(mode="json")) != runtime.spec_hash:
                problems.append("spec_integrity_mismatch")
            statuses: dict[str, list[str]] = {d: [] for d in ("SECURITY", "BUSINESS", "OBSERVATION")}
            evidence_ids = []
            for check in spec.checks:
                observation = observations.get(check.check_id)
                if not observation:
                    problems.append(f"missing_required_check:{check.check_id}")
                    statuses[check.dimension].append("INCONCLUSIVE")
                    continue
                statuses[check.dimension].append(observation.assertion_status)
                evidence = db.get(EvidenceRow, observation.evidence_id)
                if evidence:
                    evidence_ids.append(evidence.evidence_id)
                    support_deadlines.append(evidence.valid_until)
                if (
                    not evidence
                    or evidence.environment_id != env
                    or evidence.incident_id != runtime.incident_id
                    or not runtime.created_at
                    <= observation.started_at
                    <= observation.checked_at
                    <= ts
                    < evidence.valid_until
                    or evidence.trust_status != "VERIFIED_ORIGIN"
                    or evidence.contradicts
                    or evidence.integrity_hash != canonical_hash(observation.samples)
                ):
                    problems.append(f"missing_stale_or_conflicting_evidence:{check.check_id}")
                if (
                    observation.execution_status != "SUCCEEDED"
                    or observation.assertion_status == "INCONCLUSIVE"
                ):
                    problems.append(f"incomplete_probe:{check.check_id}")
                if len(observation.samples) < max(check.repetitions, policy.minimum_samples):
                    problems.append(f"insufficient_samples:{check.check_id}")
                if (
                    len(
                        {
                            canonical_hash({k: v for k, v in sample.items() if k != "latency_ms"})
                            for sample in observation.samples
                        }
                    )
                    > 1
                ):
                    problems.append(f"conflicting_samples:{check.check_id}")
            raw = {
                d: "INCONCLUSIVE"
                if not values or "INCONCLUSIVE" in values
                else "FAIL"
                if "FAIL" in values
                else "PASS"
                for d, values in statuses.items()
            }
            if raw["OBSERVATION"] != "PASS":
                problems.append("observability_insufficient")
            if len(set(evidence_ids)) < policy.minimum_evidence:
                problems.append("minimum_evidence_not_met")
            qualified = {d: Verdict.INCONCLUSIVE if problems else Verdict(raw[d]) for d in raw}
            outcome = expected_verdict(qualified["SECURITY"], qualified["BUSINESS"], qualified["OBSERVATION"])
            # The absence itself is a measured observation, not evidence that an unperformed probe passed.
            diagnostic = {"health": health, "missing_or_unqualified": problems, "raw_dimensions": raw}
            diagnostic_id = identity("verification-diagnostic", spec_id)
            diagnostic_evidence = Evidence(
                evidence_id=diagnostic_id,
                environment_id=env,
                incident_id=runtime.incident_id,
                source_event_ids=[],
                provenance_group=f"verification-decision:{spec_id}",
                claim_kind="OBSERVATION",
                observed_at=ts,
                collected_at=ts,
                valid_until=(
                    min(support_deadlines + [ts + timedelta(seconds=policy.evidence_ttl_seconds)])
                    if outcome != Verdict.INCONCLUSIVE
                    else ts + timedelta(seconds=policy.evidence_ttl_seconds)
                ),
                content_ref=f"db://verification_effectiveness/{verification_id}",
                integrity_hash=canonical_hash(diagnostic),
                collector_id=principal.principal_id,
                collection_method="verification-decision/1.0.0",
                trust_status="VERIFIED_ORIGIN",
                supports=["decision-time completeness assessment"],
                contradicts=[],
                data_origin=runtime.binding["data_origin"],
            )
            db.add(EvidenceRow(**values_for(diagnostic_evidence, EvidenceRow)))
            evidence_ids.append(diagnostic_id)
            residual = ["Read-only DETECTION does not establish containment, remediation or hostile intent"]
            if spec.objective_type == "CONTAINMENT":
                residual = [
                    "Temporary Lab test-path containment only; root cause remains; no remediation or CLOSED claim; TTL requires new observations"
                ]
            next_step = (
                "Retain VERIFYING; human assessment of residual risk"
                if outcome == Verdict.PASS
                else (
                    "Bounded read-only diagnosis re-plan"
                    if outcome == Verdict.FAIL
                    else "Repair observation or collect additional evidence"
                )
            )
            result = VerificationResult(
                verification_id=verification_id,
                verification_spec_id=spec_id,
                environment_id=env,
                incident_id=runtime.incident_id,
                action_id=runtime.action_id,
                validation_run_id=runtime.run_id,
                objective_type=spec.objective_type,
                claim="Independent confirmation of temporary Lab test-path restriction, business availability and observation coverage"
                if spec.objective_type == "CONTAINMENT"
                else "Independent confirmation of read-only resource context and business availability",
                target_ids=sorted({c.target_resource_id for c in spec.checks}),
                scope_id=runtime.scope_id,
                scenario_version=spec.scenario_version,
                started_at=runtime.created_at,
                finished_at=ts,
                valid_until=diagnostic_evidence.valid_until,
                security_status=qualified["SECURITY"],
                business_status=qualified["BUSINESS"],
                observation_status=qualified["OBSERVATION"],
                status=outcome,
                evidence_ids=evidence_ids,
                expected_result="All required current independent checks qualified and PASS",
                observed_result=str(diagnostic),
                residual_risks=residual,
                recommended_next_step=next_step,
            )
            db.add(VerificationResultRow(**values_for(result, VerificationResultRow)))
            db.flush()
            db.add(
                EffectivenessRow(
                    verification_id=verification_id,
                    raw_dimensions=raw,
                    qualification_failures=problems,
                    decision={
                        "status": "VERIFIED_EFFECTIVE"
                        if outcome == Verdict.PASS
                        else "VERIFIED_INEFFECTIVE"
                        if outcome == Verdict.FAIL
                        else "INCONCLUSIVE",
                        "objective_type": spec.objective_type,
                        "security_objective_achieved": qualified["SECURITY"] == Verdict.PASS,
                        "business_impact_acceptable": qualified["BUSINESS"] == Verdict.PASS,
                        "observability_sufficient": not problems,
                        "residual_risks": residual,
                        "next_action": next_step,
                        "diagnostic_observation": diagnostic,
                    },
                    decided_at=ts,
                    decision_ms=(perf_counter() - start) * 1000,
                )
            )
            emit(
                db,
                env,
                "VerificationResult",
                verification_id,
                {
                    Verdict.PASS: "VerificationPassed",
                    Verdict.FAIL: "VerificationFailed",
                    Verdict.INCONCLUSIVE: "VerificationInconclusive",
                }[outcome],
                f"qualified={outcome.value}; raw={raw}; problems={problems}",
                principal.principal_id,
            )
            emit(
                db,
                env,
                "EffectivenessDecision",
                verification_id,
                "EffectivenessEvaluated",
                next_step,
                principal.principal_id,
            )
            return result
