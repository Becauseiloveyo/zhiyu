"""Container-side acceptance phases against real target, PostgreSQL and sensor proofs.

Fault injection lives only in this harness. Product executors have no fault or arbitrary-command input.
"""

import argparse
import hashlib
import http.client
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from m6_sensor_verification import actor
from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.core.config import settings
from zhiyu.core.errors import LeaseLostError
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import (
    ActionAttemptRow,
    ActionRow,
    EnvironmentRow,
    IncidentRow,
    ResourceRow,
    ScopeRow,
    SensorHealthRow,
)
from zhiyu.db.response_authority import ResponseControlRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.session import get_engine
from zhiyu.db.verification_runtime import VerificationRuntimeRow
from zhiyu.domain.contracts import ActionRequest, CapabilityHealth, SensorHealth
from zhiyu.repositories.audit import AuditRepository
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.capacity import active, classify, snapshot
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.executors import ExecutorOutput
from zhiyu.response.gateway import ActionGateway
from zhiyu.response.lab_client import LabClient
from zhiyu.response.lab_protocol import CAPABILITY, LabBinding
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy, emit
from zhiyu.response.registry import CapabilityRegistry
from zhiyu.response.scheduler import TaskScheduler
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.lab_reviews import schedule_reviews
from zhiyu.verification.policy import VerificationPolicy
from zhiyu.verification.runtime import VerificationService, containment_spec


class LabAcceptance:
    def __init__(self, capture):
        self.capture = capture
        self.env = "m6-real-" + capture.name
        self.engine = get_engine()
        base = actor(self.env, capture)
        self.operator = base.model_copy(
            update={
                "principal_id": "m6-lab-action",
                "permissions": base.permissions | {"capability:" + CAPABILITY, "response:reconcile"},
            }
        )
        self.verifier = self.operator.model_copy(update={"principal_id": "m6-lab-recovery"})
        self.background = self.operator.model_copy(update={"principal_id": "m6-lab-background"})
        self.binding = LabBinding(
            environment_id=self.env,
            resource_id="target-a",
            address="10.89.60.10",
            port=8081,
            token=Path("/run/secrets/lab-control").read_text().strip(),
        )
        settings.lab_targets = {self.env + "/target-a": self.binding}

    def target(self):
        c = http.client.HTTPConnection(
            self.binding.address, self.binding.port, timeout=2, source_address=("10.89.60.30", 0)
        )
        try:
            c.request(
                "GET", "/control", headers={"X-Zhiyu-Lab-Control": self.binding.token.get_secret_value()}
            )
            r = c.getresponse()
            assert r.status == 200
            return json.loads(r.read(32768))
        finally:
            c.close()

    def traffic(self):
        result = []
        for path in ("/attack", "/health"):
            c = http.client.HTTPConnection(
                self.binding.address, self.binding.port, timeout=2, source_address=("10.89.60.30", 0)
            )
            try:
                c.request("HEAD", path)
                r = c.getresponse()
                result.append({"path": path, "status": r.status, "at": datetime.now(UTC).isoformat()})
                r.read()
            finally:
                c.close()
        return result

    def initialize(self):
        with Session(self.engine) as db:
            CapabilityRegistry(db).install(self.env, self.operator, lab=True)
        with Session(self.engine) as db, db.begin():
            env = db.get(EnvironmentRow, self.env)
            assert env.owner_id == "CONTROLLED-REAL-SENSOR-LAB" and env.deployment_stage == "LAB"
            env.capability_allowlist = sorted(set(env.capability_allowlist) | {CAPABILITY})
            target = db.get(ResourceRow, ("target-a", self.env))
            target.locator = {"address": self.binding.address, "port": self.binding.port, "protocol": "TCP"}
            target.binding_version += 1
            scope = db.get(ScopeRow, ("scope-lab-web", self.env))
            scope.allowed_capabilities = sorted(set(scope.allowed_capabilities) | {CAPABILITY})
            scope.capability_source_ids = {**scope.capability_source_ids, CAPABILITY: ["validation-a"]}
            scope.network_constraints = [
                {
                    "source_resource_ids": ["validation-a"],
                    "target_resource_ids": ["target-a"],
                    "destination_ports": [8080, 8081],
                    "protocols": ["TCP"],
                }
            ]
            control = db.get(ResponseControlRow, self.env)
            configuration = ResponsePolicy.model_validate(control.configuration).model_dump()
            configuration.update(
                reserved_capacity_enabled=True,
                worker_classes={
                    self.operator.principal_id: "SECURITY_CRITICAL",
                    self.verifier.principal_id: "RECOVERY",
                    self.background.principal_id: "BACKGROUND",
                },
                class_capacity={"BACKGROUND": 1, "SECURITY_CRITICAL": 1, "RECOVERY": 1},
            )
            configuration["worker_sources"].update(
                {p.principal_id: "validation-a" for p in (self.operator, self.verifier, self.background)}
            )
            control.configuration = ResponsePolicy.model_validate(configuration).model_dump(mode="json")
            emit(
                db,
                self.env,
                "EnvironmentProfile",
                self.env + ":lab-opt-in",
                "LabContainmentEnabled",
                "explicit disposable target and reserved worker bindings",
                self.operator.principal_id,
            )
        observed = self.target()
        with Session(self.engine) as db:
            CapabilityRegistry(db).record_health(
                CapabilityHealth(
                    capability_id=CAPABILITY,
                    capability_version="1.0.0",
                    environment_id=self.env,
                    worker_pool="response",
                    status="HEALTHY",
                    checked_at=datetime.now(UTC),
                    latency_ms=0,
                    queue_depth=0,
                    running_count=0,
                    detail="actual bounded target identity read; not a containment verdict",
                ),
                self.operator,
            )
        return {"status": "READY", "target": observed}

    def health(self, proof_path):
        payload = proof_path.read_bytes()
        proof = json.loads(payload)
        pairs, now = proof["path_pairs"], datetime.now(UTC)
        sensors = []
        for name in ("suricata", "wazuh"):
            if name == "suricata":
                stats = proof[name]["stats"] or {}
                heartbeat = stats.get("timestamp", proof["observed_at"])
                drops = stats.get("stats", {}).get("capture", {}).get("kernel_drops", 0)
                alive = proof["processes"]["suricata"]["running"]
            else:
                detail = (proof[name]["agent_status"] or {}).get("data", {})
                heartbeat = datetime.fromtimestamp(int(detail.get("lastKeepAlive", 0)), UTC).isoformat()
                drops = 0
                alive = (
                    all(proof["processes"][s]["running"] for s in ("wazuh-manager", "wazuh-agent"))
                    and detail.get("status") == "Active"
                )
            event = max((p[name + "_timestamp"] for p in pairs), default=proof["window_start"])
            last, hb = datetime.fromisoformat(event), datetime.fromisoformat(heartbeat)
            coverage = bool(pairs) and all(proof["path_coverage"].values()) and drops == 0
            fresh = 0 <= (now - hb).total_seconds() <= 120 and 0 <= (now - last).total_seconds() <= 120
            sensor = SensorHealth(
                sensor_id="sensor-" + name,
                environment_id=self.env,
                status="OFFLINE" if not alive else "HEALTHY" if coverage and fresh else "DEGRADED",
                last_heartbeat_at=hb,
                last_event_at=last,
                lag_seconds=max(0, (now - last).total_seconds()),
                lost_event_count=drops,
                coverage_scope_ids=["scope-lab-web"] if coverage else [],
                coverage_validated=coverage and alive,
                config_version="real-path-proof/" + hashlib.sha256(payload).hexdigest(),
            )
            sensors.append(sensor)
        with Session(self.engine) as db, db.begin():
            for sensor in sensors:
                row = db.get(SensorHealthRow, (sensor.sensor_id, self.env))
                for key, value in values_for(sensor, SensorHealthRow).items():
                    setattr(row, key, value)
            emit(
                db,
                self.env,
                "SensorHealth",
                hashlib.sha256(payload).hexdigest(),
                "RealPathCoverageObserved",
                "actual Suricata and Wazuh source-port/path correlation",
                self.verifier.principal_id,
            )
        self.target()
        from zhiyu.response.catalog import INPUTS

        for capability in [*INPUTS, CAPABILITY]:
            with Session(self.engine) as db:
                sample = CapabilityRegistry(db).local_health(capability, self.env, "response", now)
            if capability == CAPABILITY:
                sample.status = "HEALTHY"
                sample.detail = "actual protected Lab target identity read"
            with Session(self.engine) as db:
                CapabilityRegistry(db).record_health(sample, self.operator)
        return [s.model_dump(mode="json") for s in sensors]

    def incident(self):
        with Session(self.engine) as db:
            row = db.scalar(
                select(IncidentRow)
                .where(IncidentRow.environment_id == self.env, IncidentRow.status == "TRIAGED")
                .order_by(IncidentRow.incident_id)
            )
            assert row
            return row.incident_id, row.state_version

    def plan(self, data):
        ident, version = self.incident()
        before = data.get("before") or self.target()["state"]
        parameters = {
            "operation": "compensate" if data.get("prior") else "contain",
            "epoch": before["epoch"],
            "expected_generation": before["generation"],
            "before_digest": before["digest"],
            "ttl_seconds": data.get("ttl", 60),
            "prior_action_id": data.get("prior"),
        }
        with Session(self.engine) as db:
            plan = DeterministicResponsePlanner(
                db,
                PlannerPolicy(
                    policy_version="m6-remediation/" + data["case"],
                    lab_target="target-a",
                    lab_parameters=parameters,
                ),
            ).create(
                self.env, ident, expected_version=version, scope_id="scope-lab-web", principal=self.operator
            )
        return {"plan_id": plan.plan_id, "task_id": plan.tasks[0].task_id, "before": before}

    def execute(self, data):
        with Session(self.engine) as db:
            ready = db.get(ResponseControlRow, self.env).next_probe_at
        time.sleep(max(0, (ready - datetime.now(UTC)).total_seconds()) + 0.02)
        with Session(self.engine) as db:
            lease = TaskScheduler(db).claim(self.env, self.operator)
        assert lease
        with Session(self.engine) as db:
            decision = AuthorizationService(db).authorize_task(
                self.env, lease["task_id"], generation=lease["generation"], principal=self.operator
            )
        assert decision.outcome == "ALLOW", decision.reasons
        gateway = ActionGateway(self.engine)
        if data.get("crash"):

            def crash(*args, **kwargs):
                print(
                    json.dumps(
                        {
                            "status": "PROCESS_EXIT_AFTER_TARGET_CHANGE_BEFORE_RECEIPT_COMMIT",
                            "attempt_id": args[1],
                            "lease": lease,
                        }
                    ),
                    flush=True,
                )
                os._exit(71)

            gateway.complete = crash
        receipt = gateway.dispatch(
            self.env, lease["task_id"], lease["generation"], decision.authorization_id, self.operator
        )
        return {
            "receipt": receipt,
            "lease": lease,
            "authorization_id": decision.authorization_id,
            "target": self.target(),
        }

    def action(self, action_id):
        with Session(self.engine) as db:
            return contract_from(db.get(ActionRow, action_id), ActionRequest)

    def verify_start(self, data):
        action = self.action(data["action_id"])
        with Session(self.engine) as db:
            result = db.scalar(
                select(ActionResultRow)
                .join(ActionDispatchRow)
                .where(ActionDispatchRow.action_id == action.action_id)
            )
            attempt_id = result.attempt_id
        spec = containment_spec(action, ["sensor-suricata", "sensor-wazuh"], data["case"])
        VerificationService(self.engine).create(
            self.env, attempt_id, spec, self.verifier, VerificationPolicy(minimum_window_seconds=1)
        )
        with Session(self.engine) as db:
            runtime = db.get(VerificationRuntimeRow, spec.verification_spec_id)
            return {"spec_id": spec.verification_spec_id, "window_start": runtime.binding["not_before"]}

    def verify_finish(self, data):
        health = self.health(Path(data["proof"]))
        service, observations = VerificationService(self.engine), []
        for _ in range(100):
            lease = service.claim(self.env, self.verifier, spec_id=data["spec_id"])
            if lease:
                observations.append(service.run_claim(self.env, lease, self.verifier))
            elif len(observations) == 3:
                break
            else:
                time.sleep(0.05)
        verdict = VerificationEngine(self.engine).decide(self.env, data["spec_id"], self.verifier)
        with Session(self.engine) as db:
            incident = db.get(IncidentRow, verdict.incident_id)
            assert incident.status != "CLOSED"
        return {
            "verification": verdict.model_dump(mode="json"),
            "observations": observations,
            "sensor_health": health,
            "incident_status": incident.status,
        }

    def detect(self, proof):
        from m6_jsonl import complete_records

        from zhiyu.services.event_intelligence import EventIntelligenceEngine
        from zhiyu.services.incident_engine import IncidentEngine
        from zhiyu.services.raw_ingest import RawIngestService, RawInput

        proof_path = Path(proof)
        proof = json.loads(proof_path.read_bytes())
        boundary = datetime.fromisoformat(proof["window_start"])
        actual = [
            (line, raw, record)
            for line, raw, record in complete_records((proof_path.parent / "eve.json").read_bytes())[0]
            if record.get("event_type") == "alert"
            and record.get("dest_port") == 8081
            and record.get("alert", {}).get("signature_id") == 9900002
            and datetime.fromisoformat(record["timestamp"]) >= boundary
        ]
        assert actual, "a fresh real IDS alert is required during queue saturation"
        with Session(self.engine) as db:
            ingestion = RawIngestService(db).ingest(
                [
                    RawInput(raw.decode("utf-8"), f"m6-live-path/{record['flow_id']}/{line}")
                    for line, raw, record in actual
                ],
                environment_id=self.env,
                collector_id="sensor-suricata",
                source_type="suricata",
                principal=self.operator,
                data_origin="OBSERVED",
            )
        assert ingestion["accepted"] > 0 and ingestion["errors"] == 0
        with Session(self.engine) as db:
            grouped = EventIntelligenceEngine(db).process(self.env, principal=self.operator)
        with Session(self.engine) as db:
            promoted = IncidentEngine(db).promote(self.env, principal=self.operator)
        assert grouped["processed"] > 0
        return {
            "real_alert_ingest": ingestion,
            "grouped": grouped,
            "promoted": promoted,
            "raw_alert_sha256": [hashlib.sha256(raw).hexdigest() for _, raw, _ in actual],
        }

    def run(self, phase, data):
        if phase == "critical-alert-ingest":
            return self.detect(data["proof"])
        if phase == "init":
            return self.initialize()
        if phase == "traffic":
            return self.traffic()
        if phase == "target":
            return self.target()
        if phase == "health":
            return self.health(Path(data["proof"]))
        if phase == "plan":
            return self.plan(data)
        if phase == "execute":
            return self.execute(data)
        if phase == "critical-detection-prepare":
            ident, version = self.incident()
            with Session(self.engine) as db:
                plan = DeterministicResponsePlanner(
                    db, PlannerPolicy(policy_version="m6-critical-detection")
                ).create(
                    self.env,
                    ident,
                    expected_version=version,
                    scope_id="scope-lab-web",
                    principal=self.operator,
                )
            for task in plan.tasks:
                with Session(self.engine) as db:
                    classify(db, self.env, task.task_id, "SECURITY_CRITICAL", self.operator)
            root = self.execute({})
            assert root["receipt"]["execution_outcome"] == "EXECUTION_SUCCESS"
            return {"tasks": [t.model_dump(mode="json") for t in plan.tasks], "root": root}
        if phase == "critical-detection-finish":
            started = time.monotonic()
            detection = self.detect(data["proof"])
            results = [self.execute({}), self.execute({})]
            assert all(r["receipt"]["execution_outcome"] == "EXECUTION_SUCCESS" for r in results)
            return {
                "results": results,
                "seconds": time.monotonic() - started,
                **detection,
            }
        if phase == "database-snapshot":
            from m6_database_snapshot import snapshot as database_snapshot

            return database_snapshot()
        if phase == "reconcile":
            with Session(self.engine) as db:
                TaskScheduler(db).claim(self.env, self.verifier)
            result = ActionGateway(self.engine).reconcile(self.env, data["attempt_id"], self.verifier)
            return {"receipt": result, "target": self.target()}
        if phase == "duplicate":
            before = self.target()
            receipt = LabClient(self.action(data["action_id"])).request("POST")
            after = self.target()
            assert before["mutations"] == after["mutations"] and receipt["duplicate"]
            return {"receipt": receipt, "target": after}
        if phase == "stale-worker":
            before = self.target()
            try:
                ActionGateway(self.engine).complete(
                    self.env,
                    data["attempt_id"],
                    data["generation"],
                    self.operator,
                    ExecutorOutput("EXECUTION_SUCCESS", {}),
                    executor_name=CAPABILITY,
                    executor_version="stale-worker-fault",
                    executor_ms=0,
                )
            except LeaseLostError:
                after = self.target()
                assert before["mutations"] == after["mutations"]
                return {"stale_ack": "FENCED", "target": after}
            raise AssertionError("stale worker completion was not fenced")
        if phase == "verify-start":
            return self.verify_start(data)
        if phase == "verify-finish":
            return self.verify_finish(data)
        if phase == "ttl-reviews":
            schedule_reviews(self.engine, self.env, self.verifier)
            with Session(self.engine) as db:
                rows = db.scalars(
                    select(VerificationRuntimeRow).where(
                        VerificationRuntimeRow.environment_id == self.env,
                        VerificationRuntimeRow.action_id == data["action_id"],
                    )
                )
                return [
                    {"spec_id": r.spec_id, "window_start": r.binding["not_before"], "policy": r.policy}
                    for r in rows
                ]
        if phase == "background":
            ident, version = self.incident()
            # Extend only the explicitly managed fixture lease budget before any new claims.
            with Session(self.engine) as db, db.begin():
                control = db.get(ResponseControlRow, self.env)
                control.configuration = {**control.configuration, "lease_seconds": 60}
            for index in range(data.get("plans", 334)):
                with Session(self.engine) as db:
                    DeterministicResponsePlanner(
                        db, PlannerPolicy(policy_version=f"m6-saturation/{index}")
                    ).create(
                        self.env,
                        ident,
                        expected_version=version,
                        scope_id="scope-lab-web",
                        principal=self.operator,
                    )
            with Session(self.engine) as db:
                lease = TaskScheduler(db).claim(self.env, self.background)
            assert lease
            with Session(self.engine) as db:
                assert TaskScheduler(db).claim(self.env, self.background) is None
            with Session(self.engine) as db:
                return {"held_lease": lease, "queue": snapshot(db, self.env)}
        if phase == "snapshot":
            with Session(self.engine) as db:
                attempts = [
                    {"attempt_id": a.attempt_id, "status": a.status, "reconciliation": a.reconciliation_state}
                    for a in db.scalars(
                        select(ActionAttemptRow)
                        .join(ActionRow, ActionRow.action_id == ActionAttemptRow.action_id)
                        .where(ActionRow.environment_id == self.env, ActionRow.capability_id == CAPABILITY)
                    )
                ]
                return {
                    "queue": snapshot(db, self.env),
                    "valid_running_leases": dict(active(db, self.env, datetime.now(UTC))),
                    "attempts": attempts,
                    "audit_valid": AuditRepository(db).verify_chain(self.env),
                    "target": self.target(),
                }
        raise ValueError("unknown bounded acceptance phase")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("phase")
    parser.add_argument("--data", default="{}")
    args = parser.parse_args()
    print(
        json.dumps(LabAcceptance(args.capture).run(args.phase, json.loads(args.data)), default=str),
        flush=True,
    )


if __name__ == "__main__":
    main()
