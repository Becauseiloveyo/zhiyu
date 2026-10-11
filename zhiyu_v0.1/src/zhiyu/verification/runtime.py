"""Database-fenced independent observations, durable receipts and bounded retries."""

from datetime import datetime, timedelta
from time import perf_counter
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ConflictError, LeaseLostError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import (
    ActionRow,
    EnvironmentRow,
    EvidenceRow,
    ResourceRow,
    ScopeRow,
    SensorHealthRow,
    ValidationRunRow,
    ValidationScenarioRow,
    VerificationSpecRow,
)
from zhiyu.db.response_authority import ResponseControlRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.response_planning import TaskRuntimeRow
from zhiyu.db.verification_runtime import (
    VerificationCheckRow,
    VerificationObservationRow,
    VerificationRuntimeRow,
)
from zhiyu.domain.contracts import (
    ActionRequest,
    AssertionSpec,
    Evidence,
    ResourceRef,
    ValidationRun,
    ValidationScenario,
    VerificationCheckSpec,
    VerificationSpec,
)
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.executors import SafeHttpProbeExecutor
from zhiyu.response.lab_protocol import CAPABILITY
from zhiyu.response.planner import emit, identity
from zhiyu.verification.policy import VerificationPolicy, assert_value, validate_spec


def instant(db: Session, now: datetime | None) -> datetime:
    value = now or db.scalar(select(func.clock_timestamp()))
    assert value is not None
    return value


def lock_environment(db: Session, env: str) -> EnvironmentRow:
    row = db.scalar(select(EnvironmentRow).where(EnvironmentRow.environment_id == env).with_for_update())
    if row is None:
        raise ReferenceError("environment missing")
    return row


def default_spec(action: ActionRequest, sensor_ids: list[str], version: str = "1") -> VerificationSpec:
    key = identity("verification-spec", [action.environment_id, action.action_id, version])
    return VerificationSpec(
        verification_spec_id=key,
        scenario_id=identity("scenario", key),
        scenario_version=version,
        objective_type="DETECTION",
        checks=[
            VerificationCheckSpec(
                check_id="security-context",
                dimension="SECURITY",
                capability_id="state_snapshot_check",
                target_resource_id=action.target.resource_id,
                timeout_seconds=1,
                repetitions=1,
                assertions=[
                    AssertionSpec(
                        field="binding_version", operator="EQUALS", expected=action.target.binding_version
                    )
                ],
            ),
            VerificationCheckSpec(
                check_id="business-health",
                dimension="BUSINESS",
                capability_id="safe_http_probe",
                source_resource_id=action.source.resource_id if action.source else None,
                target_resource_id=action.target.resource_id,
                timeout_seconds=1,
                repetitions=1,
                assertions=[
                    AssertionSpec(field="status_code", operator="EQUALS", expected=200),
                    AssertionSpec(field="latency_ms", operator="LTE", expected=1000),
                ],
            ),
            VerificationCheckSpec(
                check_id="observation-health",
                dimension="OBSERVATION",
                capability_id="sensor_health_check",
                target_resource_id=action.target.resource_id,
                timeout_seconds=1,
                repetitions=1,
                required_sensor_ids=sensor_ids,
                assertions=[
                    AssertionSpec(field=f, operator="EQUALS", expected=True)
                    for f in ("sensors_healthy", "evidence_fresh", "telemetry_complete")
                ],
            ),
        ],
    )


def containment_spec(action: ActionRequest, sensor_ids: list[str], version: str = "1") -> VerificationSpec:
    spec = default_spec(action, sensor_ids, version)
    spec.objective_type = "CONTAINMENT"
    spec.checks[0].capability_id = "lab_containment_probe"
    spec.checks[0].source_resource_id = action.source.resource_id if action.source else None
    spec.checks[0].assertions = [
        AssertionSpec(field="status_code", operator="EQUALS", expected=403),
        AssertionSpec(field="reachable", operator="EQUALS", expected=True),
    ]
    spec.checks[1].assertions.append(AssertionSpec(field="reachable", operator="EQUALS", expected=True))
    return spec


class VerificationService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def cancel(self, env: str, spec_id: str, check_id: str, principal: ServicePrincipal) -> bool:
        principal.require("verification:write", env)
        with Session(self.engine) as db, db.begin():
            lock_environment(db, env)
            job = db.get(VerificationCheckRow, (spec_id, check_id))
            if not job or job.environment_id != env:
                raise ReferenceError("verification check not found in environment")
            if job.status not in {"PENDING", "RUNNING"}:
                return False
            job.status, job.worker_id, job.lease_until = "CANCELLED", None, None
            emit(
                db,
                env,
                "VerificationCheck",
                f"{spec_id}:{check_id}",
                "CheckCompleted",
                "cancelled by operator; no observation or security claim",
                principal.principal_id,
            )
            return True

    def create(
        self,
        env: str,
        result_id: str,
        spec: VerificationSpec,
        principal: ServicePrincipal,
        policy: VerificationPolicy = VerificationPolicy(),
        *,
        now: datetime | None = None,
    ) -> str:
        principal.require("verification:write", env)
        validate_spec(spec)
        start = perf_counter()
        with Session(self.engine) as db, db.begin():
            environment = lock_environment(db, env)
            ts = instant(db, now)
            dispatch = db.get(ActionDispatchRow, result_id)
            result = db.get(ActionResultRow, result_id)
            if not dispatch or dispatch.environment_id != env or not result or result.completed_at > ts:
                raise ReferenceError("resolved action receipt missing in environment")
            action_row = db.get(ActionRow, dispatch.action_id)
            assert action_row is not None
            action = contract_from(action_row, ActionRequest)
            if spec.objective_type == "CONTAINMENT" and (
                action.capability_id != CAPABILITY
                or action.parameters.get("operation", "contain") != "contain"
                or environment.deployment_stage != "LAB"
                or policy.minimum_window_seconds < 1
            ):
                raise ConflictError(
                    "containment requires a bounded Lab action and a complete observation window"
                )
            task = db.get(TaskRuntimeRow, action.task_id)
            assert task is not None
            prior = db.get(VerificationRuntimeRow, spec.verification_spec_id)
            if prior:
                if (
                    prior.environment_id != env
                    or prior.action_result_id != result_id
                    or prior.spec_hash != canonical_hash(spec.model_dump(mode="json"))
                    or prior.policy != policy.model_dump(mode="json")
                ):
                    raise ConflictError("verification identity reused with different inputs")
                return prior.spec_id
            from zhiyu.db.verification_replan import ResponseCycleRow
            from zhiyu.verification.lifecycle import ready_for_verification

            cycle = db.get(ResponseCycleRow, task.plan_id)
            if cycle:
                ready_for_verification(db, cycle, ts, principal.principal_id)
            scope = db.get(ScopeRow, (action.scope_id, env))
            if (
                not scope
                or action.scope_id not in environment.scope_ids
                or not scope.valid_from <= ts < scope.valid_until
            ):
                raise ConflictError("verification scope expired")
            for check in spec.checks:
                if (
                    check.target_resource_id != action.target.resource_id
                    or check.target_resource_id not in scope.target_resource_ids
                ):
                    raise ConflictError("check target outside original action scope")
                if not set(check.required_sensor_ids) <= set(environment.required_sensor_ids):
                    raise ConflictError("unregistered check sensor")
                if check.source_resource_id and check.source_resource_id not in scope.source_resource_ids:
                    raise ConflictError("check source outside scope")
                if check.timeout_seconds * check.repetitions >= policy.lease_seconds:
                    raise ConflictError("check exceeds lease execution budget")
            expiry = min(
                ts + timedelta(seconds=policy.validity_seconds + policy.start_after_seconds),
                scope.valid_until,
            )
            run_id = identity("verification-run", spec.verification_spec_id)
            target_receipt = result.output.get("observed", {}).get("receipt") or result.output
            containment_until = (
                target_receipt.get("after", {}).get("expires_at")
                if spec.objective_type == "CONTAINMENT"
                else None
            )
            scenario = ValidationScenario(
                scenario_id=spec.scenario_id,
                version=spec.scenario_version,
                implementation_status="DESIGN_ONLY",
                objective="Independent temporary Lab containment verification"
                if spec.objective_type == "CONTAINMENT"
                else "Read-only resource context confirmation; no containment claim",
                environment_id=env,
                scope_id=action.scope_id,
                preconditions=["Resolved action receipt", "Fresh independent observations"],
                trigger_steps=["Independent checks"],
                expected_events=[],
                verification_spec_id=spec.verification_spec_id,
                cleanup_steps=["Read-only; no side effects"],
                stop_conditions=["Scope expiry", "Bounded check budget"],
            )
            run = ValidationRun(
                run_id=run_id,
                scenario_id=spec.scenario_id,
                scenario_version=spec.scenario_version,
                environment_id=env,
                scope_id=action.scope_id,
                registered_by=principal.principal_id,
                trusted_registration=True,
                started_at=ts,
                expires_at=expiry,
                expected_event_types=[],
                allowed_side_effects=[],
                cleanup_policy_id="read-only-none",
                data_origin="SYNTHETIC" if environment.owner_id.startswith("SYNTHETIC") else "OBSERVED",
            )
            db.add(VerificationSpecRow(**values_for(spec, VerificationSpecRow)))
            db.add(ValidationScenarioRow(**values_for(scenario, ValidationScenarioRow)))
            db.flush()
            db.add(ValidationRunRow(**values_for(run, ValidationRunRow)))
            db.flush()
            db.add(
                VerificationRuntimeRow(
                    spec_id=spec.verification_spec_id,
                    environment_id=env,
                    incident_id=action.incident_id,
                    plan_id=task.plan_id,
                    task_id=action.task_id,
                    action_id=action.action_id,
                    action_result_id=result_id,
                    scope_id=action.scope_id,
                    run_id=run_id,
                    policy=policy.model_dump(mode="json"),
                    binding={
                        "environment_version": environment.version,
                        "scope_version": scope.version,
                        "sensor_ids": environment.required_sensor_ids,
                        "input_evidence_ids": action.evidence_ids,
                        "action_completed_at": result.completed_at.isoformat(),
                        "data_origin": run.data_origin,
                        "objective_type": spec.objective_type,
                        "containment_until": containment_until,
                        "not_before": (ts + timedelta(seconds=policy.start_after_seconds)).isoformat(),
                    },
                    spec_hash=canonical_hash(spec.model_dump(mode="json")),
                    created_at=ts,
                    valid_until=expiry,
                    generation_ms=(perf_counter() - start) * 1000,
                )
            )
            db.flush()
            for check in spec.checks:
                db.add(
                    VerificationCheckRow(
                        spec_id=spec.verification_spec_id,
                        check_id=check.check_id,
                        environment_id=env,
                        definition=check.model_dump(mode="json"),
                        status="PENDING",
                        generation=0,
                    )
                )
            emit(
                db,
                env,
                "VerificationSpec",
                spec.verification_spec_id,
                "VerificationSpecCreated",
                "Independent read-only checks registered",
                principal.principal_id,
            )
            return spec.verification_spec_id

    def claim(
        self,
        env: str,
        principal: ServicePrincipal,
        *,
        spec_id: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        principal.require("verification:execute", env)
        with Session(self.engine) as db, db.begin():
            lock_environment(db, env)
            ts = instant(db, now)
            control = db.get(ResponseControlRow, env)
            if control:
                from zhiyu.response.capacity import available

                if not available(
                    db, env, ResponsePolicy.model_validate(control.configuration), principal, "RECOVERY", ts
                ):
                    return None
            query = select(VerificationCheckRow).where(
                VerificationCheckRow.environment_id == env,
                or_(
                    VerificationCheckRow.status == "PENDING",
                    (VerificationCheckRow.status == "RUNNING") & (VerificationCheckRow.lease_until <= ts),
                ),
            )
            if spec_id:
                query = query.where(VerificationCheckRow.spec_id == spec_id)
            for job in db.scalars(
                query.order_by(VerificationCheckRow.spec_id, VerificationCheckRow.check_id).with_for_update(
                    skip_locked=True
                )
            ):
                runtime = db.get(VerificationRuntimeRow, job.spec_id)
                assert runtime is not None
                policy = VerificationPolicy.model_validate(runtime.policy)
                if ts < datetime.fromisoformat(
                    runtime.binding.get("not_before", runtime.created_at.isoformat())
                ):
                    continue
                control = db.get(ResponseControlRow, env)
                if (
                    job.definition["capability_id"] in {"safe_http_probe", "lab_containment_probe"}
                    and control
                    and control.next_probe_at > ts
                    and runtime.valid_until > ts
                ):
                    continue
                job.generation += 1
                job.status, job.worker_id = "RUNNING", principal.principal_id
                job.started_at, job.lease_until = ts, ts + timedelta(seconds=policy.lease_seconds)
                emit(
                    db,
                    env,
                    "VerificationCheck",
                    f"{job.spec_id}:{job.check_id}:{job.generation}",
                    "CheckStarted",
                    "fenced independent observation lease",
                    principal.principal_id,
                )
                if job.generation == 1:
                    emit(
                        db,
                        env,
                        "VerificationSpec",
                        f"{job.spec_id}:{job.check_id}",
                        "VerificationStarted",
                        "check dispatch",
                        principal.principal_id,
                    )
                return {"spec_id": job.spec_id, "check_id": job.check_id, "generation": job.generation}
            return None

    def run_claim(
        self, env: str, claim: dict[str, Any], principal: ServicePrincipal, *, now: datetime | None = None
    ) -> dict[str, Any]:
        principal.require("verification:execute", env)
        start = perf_counter()
        with Session(self.engine) as db, db.begin():
            environment = lock_environment(db, env)
            job = db.get(VerificationCheckRow, (claim["spec_id"], claim["check_id"]))
            runtime = db.get(VerificationRuntimeRow, claim["spec_id"])
            ts = instant(db, now)
            if not job or not runtime or runtime.environment_id != env:
                raise ReferenceError("verification job not found")
            prior = db.get(VerificationObservationRow, (job.spec_id, job.check_id))
            if prior:
                return {
                    "status": prior.execution_status,
                    "assertion": prior.assertion_status,
                    "evidence_id": prior.evidence_id,
                    "duplicate": True,
                }
            if (
                job.status != "RUNNING"
                or job.worker_id != principal.principal_id
                or job.generation != claim["generation"]
                or not job.lease_until
                or job.lease_until <= ts
            ):
                raise LeaseLostError("verification lease expired or superseded")
            check = VerificationCheckSpec.model_validate(job.definition)
            if runtime.binding.get("objective_type") == "CONTAINMENT":
                from zhiyu.db.models import ActionAttemptRow

                original_attempt = db.get(ActionAttemptRow, runtime.action_result_id)
                if original_attempt and original_attempt.worker_id == principal.principal_id:
                    raise ConflictError("containment verification requires a different worker identity")
            policy = VerificationPolicy.model_validate(runtime.policy)
            samples: list[dict[str, Any]] = []
            status, reason = "SUCCEEDED", "independent observations collected"
            if job.generation > policy.max_attempts or runtime.valid_until <= ts:
                status, reason = "TIMEOUT", "verification retry or time budget exhausted"
            else:
                try:
                    for _ in range(check.repetitions):
                        state, values, detail = VerificationCheckExecutor(db).execute(
                            runtime, check, environment, principal, ts
                        )
                        samples.append(values)
                        if state != "SUCCEEDED":
                            status, reason = state, detail
                            break
                except (ValueError, OSError, KeyError, TypeError):
                    status, reason = "FAILED", "check executor error"
            finished = instant(db, now)
            if not job.lease_until or finished >= job.lease_until:
                raise LeaseLostError("observation finished after lease deadline")
            assertions = [
                assert_value(sample, assertion) for sample in samples for assertion in check.assertions
            ]
            assertion_status = (
                "INCONCLUSIVE"
                if status != "SUCCEEDED"
                or not assertions
                or len(samples) < check.repetitions
                or any(a["outcome"] == "INCONCLUSIVE" for a in assertions)
                else "FAIL"
                if any(a["outcome"] == "FAIL" for a in assertions)
                else "PASS"
            )
            evidence_id = identity("verification-evidence", [job.spec_id, job.check_id])
            evidence = Evidence(
                evidence_id=evidence_id,
                environment_id=env,
                incident_id=runtime.incident_id,
                source_event_ids=[],
                provenance_group=f"independent-check:{job.spec_id}:{job.check_id}",
                claim_kind="OBSERVATION",
                observed_at=ts,
                collected_at=finished,
                valid_until=finished + timedelta(seconds=policy.evidence_ttl_seconds),
                content_ref=f"db://verification_observations/{job.spec_id}/{job.check_id}",
                integrity_hash=canonical_hash(samples),
                collector_id=principal.principal_id,
                collection_method="verification-check/1.0.0",
                trust_status="VERIFIED_ORIGIN",
                supports=["bounded check observation"],
                contradicts=[],
                data_origin=runtime.binding["data_origin"],
            )
            db.add(EvidenceRow(**values_for(evidence, EvidenceRow)))
            db.flush()
            db.add(
                VerificationObservationRow(
                    spec_id=job.spec_id,
                    check_id=job.check_id,
                    evidence_id=evidence_id,
                    generation=job.generation,
                    execution_status=status,
                    assertion_status=assertion_status,
                    samples=samples,
                    assertions=assertions,
                    reason=reason,
                    executor_version="verification-check/1.0.0",
                    started_at=ts,
                    checked_at=finished,
                    latency_ms=(perf_counter() - start) * 1000,
                )
            )
            job.status, job.worker_id, job.lease_until = status, None, None
            emit(
                db,
                env,
                "VerificationCheck",
                f"{job.spec_id}:{job.check_id}",
                "CheckCompleted",
                f"execution={status}; assertion={assertion_status}; {reason}",
                principal.principal_id,
            )
            return {
                "status": status,
                "assertion": assertion_status,
                "evidence_id": evidence_id,
                "duplicate": False,
            }


def observation_health(
    db: Session, runtime: VerificationRuntimeRow, environment: EnvironmentRow, ts: datetime
) -> dict[str, Any]:
    policy = VerificationPolicy.model_validate(runtime.policy)
    health = []
    for sensor_id in sorted(set(runtime.binding["sensor_ids"]) | set(environment.required_sensor_ids)):
        row = db.get(SensorHealthRow, (sensor_id, environment.environment_id))
        effective = "UNAVAILABLE" if row is None or row.status in {"OFFLINE", "UNKNOWN"} else row.status
        if row and not 0 <= (ts - row.last_heartbeat_at).total_seconds() <= policy.sensor_ttl_seconds:
            effective = "STALE"
        health.append(
            {
                "sensor_id": sensor_id,
                "effective_status": effective,
                "telemetry_complete": bool(
                    row
                    and row.coverage_validated
                    and runtime.scope_id in row.coverage_scope_ids
                    and row.lost_event_count == 0
                    and row.lag_seconds <= policy.sensor_ttl_seconds
                    and row.last_event_at
                    and 0 <= (ts - row.last_event_at).total_seconds() <= policy.sensor_ttl_seconds
                    and (
                        runtime.binding.get("objective_type") != "CONTAINMENT"
                        or (
                            row.last_event_at
                            >= datetime.fromisoformat(
                                runtime.binding.get("not_before", runtime.created_at.isoformat())
                            )
                            and row.last_heartbeat_at
                            >= datetime.fromisoformat(
                                runtime.binding.get("not_before", runtime.created_at.isoformat())
                            )
                            + timedelta(seconds=policy.minimum_window_seconds)
                        )
                    )
                ),
            }
        )
    evidence = [db.get(EvidenceRow, eid) for eid in runtime.binding["input_evidence_ids"]]
    return {
        "sensors": health,
        "sensors_healthy": bool(health) and all(h["effective_status"] == "HEALTHY" for h in health),
        "telemetry_complete": bool(health) and all(h["telemetry_complete"] for h in health),
        "evidence_fresh": bool(evidence)
        and all(
            e
            and e.environment_id == runtime.environment_id
            and e.incident_id == runtime.incident_id
            and e.observed_at <= ts < e.valid_until
            and e.trust_status == "VERIFIED_ORIGIN"
            and not e.contradicts
            for e in evidence
        ),
    }


class VerificationCheckExecutor:
    """New reads/probes only; never consumes ActionResult.output or execution success."""

    version = "verification-check/1.0.0"

    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(
        self,
        runtime: VerificationRuntimeRow,
        check: VerificationCheckSpec,
        env: EnvironmentRow,
        principal: ServicePrincipal,
        ts: datetime,
    ) -> tuple[str, dict[str, Any], str]:
        db = self.db
        scope = db.get(ScopeRow, (runtime.scope_id, env.environment_id))
        if (
            not scope
            or scope.version != runtime.binding["scope_version"]
            or env.version != runtime.binding["environment_version"]
            or not scope.valid_from <= ts < scope.valid_until
        ):
            return "INCONCLUSIVE", {}, "verification scope or environment changed"
        if check.capability_id == "sensor_health_check":
            return "SUCCEEDED", observation_health(db, runtime, env, ts), "fresh sensor/evidence query"
        target = db.get(ResourceRow, (check.target_resource_id, env.environment_id))
        if not target or target.resource_id not in scope.target_resource_ids:
            return "INCONCLUSIVE", {}, "target missing"
        if check.capability_id == "state_snapshot_check":
            return (
                "SUCCEEDED",
                {"resource_id": target.resource_id, "binding_version": target.binding_version},
                "independent database query",
            )
        principal.require("response:execute", env.environment_id)
        principal.require("capability:safe_http_probe", env.environment_id)
        control = db.get(ResponseControlRow, env.environment_id)
        if (
            not control
            or not control.enabled
            or not control.valid_from <= ts < control.valid_until
            or control.policy_version != env.policy_version
            or env.deployment_stage != "LAB"
            or env.asset_domain != "IT"
            or env.max_auto_risk < "R2"
            or env.autonomy_mode != "CONTROLLED_AUTONOMY"
            or env.active_validation != "ISOLATED_ONLY"
            or "safe_http_probe" not in scope.allowed_capabilities
            or "safe_http_probe" not in env.capability_allowlist
        ):
            return "INCONCLUSIVE", {}, "independent active-check policy disallows probe"
        policy = ResponsePolicy.model_validate(control.configuration)
        source_id = policy.worker_sources.get(principal.principal_id)
        if check.source_resource_id and check.source_resource_id != source_id:
            return "INCONCLUSIVE", {}, "verification worker source mismatch"
        source = db.get(ResourceRow, (source_id, env.environment_id)) if source_id else None
        if (
            not source
            or source.resource_id not in scope.source_resource_ids
            or source.resource_id not in scope.capability_source_ids.get("safe_http_probe", [])
            or not policy.allow_lab_r2
        ):
            return "INCONCLUSIVE", {}, "bound verification source missing"
        network = scope.network_constraints
        if not network or not any(
            source.resource_id in n["source_resource_ids"]
            and target.resource_id in n["target_resource_ids"]
            and target.locator.get("port") in n["destination_ports"]
            and target.locator.get("protocol") in n["protocols"]
            for n in network
        ):
            return "INCONCLUSIVE", {}, "network path outside registered scope"
        # Shared bounded transport, a NEW request. No ActionResult is read or reused.
        if control.next_probe_at > ts:
            return "INCONCLUSIVE", {}, "scope rate budget not ready at probe boundary"
        control.next_probe_at = ts + timedelta(seconds=1 / scope.max_requests_per_second)
        original = db.get(ActionRow, runtime.action_id)
        assert original is not None
        if check.capability_id == "lab_containment_probe":
            from zhiyu.response.lab_client import binding_for

            principal.require("capability:" + CAPABILITY, env.environment_id)
            if original.capability_id != CAPABILITY:
                return "INCONCLUSIVE", {}, "containment probe lacks a Lab action"
            binding_for(
                contract_from(original, ActionRequest).model_copy(
                    update={
                        "source": contract_from(source, ResourceRef),
                        "target": contract_from(target, ResourceRef),
                    }
                )
            )
        request = contract_from(original, ActionRequest).model_copy(
            update={
                "capability_id": check.capability_id,
                "source": contract_from(source, ResourceRef),
                "target": contract_from(target, ResourceRef),
                "parameters": {"protocol": "http", "timeout_ms": check.timeout_seconds * 1000},
            }
        )
        output = SafeHttpProbeExecutor().execute(request)
        return (
            {"EXECUTION_SUCCESS": "SUCCEEDED", "EXECUTION_FAILURE": "FAILED", "TIMEOUT": "TIMEOUT"}[
                output.execution_outcome
            ],
            output.output,
            output.error_code or "new independent HEAD /health",
        )
