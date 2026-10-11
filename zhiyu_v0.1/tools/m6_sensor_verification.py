"""Use real sensor health proofs with the unchanged authorization/verification path."""

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from m6_sensor_ingest import principal as collector_principal
from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import ActionRow, EnvironmentRow, IncidentRow, SensorHealthRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.session import get_engine
from zhiyu.domain.contracts import ActionRequest, SensorHealth
from zhiyu.response.admin import ControlRequest, configure
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.catalog import INPUTS
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.gateway import ActionGateway
from zhiyu.response.planner import DeterministicResponsePlanner, emit
from zhiyu.response.registry import CapabilityRegistry
from zhiyu.response.scheduler import TaskScheduler
from zhiyu.services.incident_lifecycle import transition
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.runtime import VerificationService, default_spec


def actor(environment, capture):
    original = collector_principal(environment, json.loads((capture / "manifest.json").read_text()))
    return original.model_copy(
        update={
            "principal_id": "m6-real-verifier",
            "permissions": original.permissions
            | {
                "response:plan",
                "response:read",
                "response:execute",
                "response:admin",
                "incidents:write",
                "verification:write",
                "verification:execute",
                "verification:read",
                "verification:replan",
                *["capability:" + capability for capability in INPUTS],
            },
        }
    )


def health_from_proof(environment, proof, proof_hash, now):
    expected = set(proof["expected_requests"])
    rows = []
    for source in ["suricata", "wazuh"]:
        sample = proof[source]
        if source == "suricata":
            up = proof["processes"]["suricata"]["running"]
            stats = sample["stats"] or {}
            heartbeat = stats.get("timestamp")
            totals = stats.get("stats", {})
            dropped = totals.get("capture", {}).get("kernel_drops", 0) + totals.get("decoder", {}).get(
                "invalid", 0
            )
            coverage = bool(stats) and expected <= set(sample["seen_requests"]) and dropped == 0
        else:
            up = all(proof["processes"][service]["running"] for service in ["wazuh-manager", "wazuh-agent"])
            detail = (sample["agent_status"] or {}).get("data", {})
            heartbeat = (
                datetime.fromtimestamp(int(detail["lastKeepAlive"]), UTC).isoformat()
                if str(detail.get("lastKeepAlive", "")).isdigit()
                else None
            )
            dropped = len(expected - set(sample["seen_requests"]))
            coverage = detail.get("status") == "Active" and bool(expected) and dropped == 0
        last_event = datetime.fromisoformat(sample["last_event_at"]) if sample["last_event_at"] else None
        hb = datetime.fromisoformat(heartbeat) if heartbeat else datetime.fromisoformat(proof["observed_at"])
        fresh = bool(
            last_event
            and 0 <= (now - last_event).total_seconds() <= 120
            and heartbeat
            and 0 <= (now - hb).total_seconds() <= 120
        )
        rows.append(
            SensorHealth(
                sensor_id="sensor-" + source,
                environment_id=environment,
                status="OFFLINE" if not up else "HEALTHY" if coverage and fresh else "DEGRADED",
                last_heartbeat_at=hb,
                last_event_at=last_event,
                lag_seconds=max(0, (now - last_event).total_seconds()) if last_event else 86400,
                lost_event_count=dropped,
                coverage_scope_ids=["scope-lab-web"] if coverage else [],
                coverage_validated=coverage and up,
                config_version="real-lab-proof/" + proof_hash,
            )
        )
    return rows


def record_health(engine, environment, proof_path, operator):
    payload = proof_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    sensors = health_from_proof(environment, json.loads(payload), digest, datetime.now(UTC))
    with Session(engine) as db, db.begin():
        env = db.get(EnvironmentRow, environment)
        assert env and env.owner_id == "CONTROLLED-REAL-SENSOR-LAB"
        for sensor in sensors:
            values = values_for(sensor, SensorHealthRow)
            row = db.get(SensorHealthRow, (sensor.sensor_id, environment))
            if row is None:
                db.add(SensorHealthRow(**values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
        emit(
            db,
            environment,
            "SensorHealth",
            digest,
            "RealSensorHealthObserved",
            "process/event/coverage/drop/heartbeat proof sha256=" + digest,
            operator.principal_id,
        )
    return [sensor.model_dump(mode="json") for sensor in sensors]


def initialize(engine, environment, capture, operator):
    now = datetime.now(UTC)
    data = json.loads((capture / "result.json").read_text())
    group_ids = {group["group_id"] for group in data["cross_source_groups"]}
    incident = next(
        item for item in data["snapshot"]["rows"]["incidents"] if group_ids & set(item["event_group_ids"])
    )
    incident_id = incident["incident_id"]
    with Session(engine) as db:
        CapabilityRegistry(db).install(environment, operator)
    with Session(engine) as db, db.begin():
        env = db.get(EnvironmentRow, environment)
        assert env and env.owner_id == "CONTROLLED-REAL-SENSOR-LAB"
        env.autonomy_mode, env.max_auto_risk, env.active_validation = (
            "CONTROLLED_AUTONOMY",
            "R2",
            "ISOLATED_ONLY",
        )
        policy_version = env.policy_version
        emit(
            db,
            environment,
            "EnvironmentProfile",
            environment,
            "RealLabReadOnlyChecksEnabled",
            "isolated controlled lab: existing read-only executors and independent HEAD checks",
            operator.principal_id,
        )
    with Session(engine) as db:
        configure(
            db,
            ControlRequest(
                environment_id=environment,
                expected_version=0,
                policy_version=policy_version,
                enabled=True,
                configuration=ResponsePolicy(worker_sources={operator.principal_id: "validation-a"}),
                valid_from=now - timedelta(seconds=1),
                valid_until=now + timedelta(hours=2),
            ),
            operator,
        )
    for capability in INPUTS:
        with Session(engine) as db:
            sample = CapabilityRegistry(db).local_health(capability, environment, "response", now)
        with Session(engine) as db:
            CapabilityRegistry(db).record_health(sample, operator)
    with Session(engine) as db:
        transition(
            db,
            environment_id=environment,
            incident_id=incident_id,
            target="TRIAGED",
            expected_version=incident["state_version"],
            principal=operator,
        )
    with Session(engine) as db:
        version = db.get(IncidentRow, incident_id).state_version
    with Session(engine) as db:
        plan = DeterministicResponsePlanner(db).create(
            environment, incident_id, expected_version=version, scope_id="scope-lab-web", principal=operator
        )
    executions = []
    for _ in plan.tasks:
        with Session(engine) as db:
            lease = TaskScheduler(db).claim(environment, operator)
        assert lease, "a runnable read-only task is required"
        with Session(engine) as db:
            decision = AuthorizationService(db).authorize_task(
                environment, lease["task_id"], generation=lease["generation"], principal=operator
            )
        receipt = ActionGateway(engine).dispatch(
            environment, lease["task_id"], lease["generation"], decision.authorization_id, operator
        )
        assert receipt["execution_outcome"] == "EXECUTION_SUCCESS", receipt
        executions.append(receipt)
    return {"plan_id": plan.plan_id, "executions": executions}


def verify(engine, environment, operator, version):
    with Session(engine) as db:
        row = db.scalar(
            select(ActionRow).where(
                ActionRow.environment_id == environment, ActionRow.capability_id == "collect_resource_context"
            )
        )
        assert row is not None
        action = contract_from(row, ActionRequest)
        receipt = db.scalar(
            select(ActionResultRow)
            .join(ActionDispatchRow)
            .where(ActionDispatchRow.action_id == action.action_id)
        )
        spec = default_spec(action, ["sensor-suricata", "sensor-wazuh"], version)
        receipt_id = receipt.attempt_id
    service = VerificationService(engine)
    service.create(environment, receipt_id, spec, operator)
    observations = []
    while lease := service.claim(environment, operator, spec_id=spec.verification_spec_id):
        observations.append(service.run_claim(environment, lease, operator))
    result = VerificationEngine(engine).decide(environment, spec.verification_spec_id, operator)
    assert VerificationEngine(engine).decide(environment, spec.verification_spec_id, operator) == result
    return {"verification": result.model_dump(mode="json"), "observations": observations}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()
    environment = "m6-real-" + args.capture.name
    engine = get_engine()
    operator = actor(environment, args.capture)
    result = {"environment": environment, "case": args.case}
    if args.proof:
        result["sensor_health"] = record_health(engine, environment, args.proof, operator)
    if args.initialize:
        result["response"] = initialize(engine, environment, args.capture, operator)
    result.update(verify(engine, environment, operator, args.case))
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
