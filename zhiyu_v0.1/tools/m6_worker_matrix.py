"""Real child exits/lease expiry against PostgreSQL; fixtures are explicitly SYNTHETIC."""

import json
import os
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from ai_fixture import snapshot, spec
from response_fixture import prepare, refresh_health
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from zhiyu.ai.context import ContextManager
from zhiyu.ai.gateway import ModelGateway
from zhiyu.core.config import settings
from zhiyu.core.errors import LeaseLostError
from zhiyu.db.ai_gateway import ModelRequestRow
from zhiyu.db.models import EvidenceRow
from zhiyu.db.session import get_engine
from zhiyu.domain.contracts import VerificationSpec
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.gateway import ActionGateway
from zhiyu.response.planner import DeterministicResponsePlanner
from zhiyu.response.worker import ResponseWorker
from zhiyu.services.event_intelligence import EventIntelligenceEngine
from zhiyu.services.raw_ingest import RawIngestService, RawInput
from zhiyu.verification.runtime import VerificationService


def write(path, value):
    path.write_text(json.dumps(value, default=str, indent=2), encoding="utf-8")


def main():
    kind, target, source = sys.argv[1:4]
    assert kind in {"event", "task", "action", "verification", "ai"}
    assert os.environ.get("ZHIYU_M6_FAULT_LAB") == "1"
    root = Path("/fault-control") / ("worker-" + kind)
    root.mkdir(exist_ok=True)
    engine = get_engine()
    principal = next(p for p in settings.service_tokens.values() if p.principal_id == "compose-smoke")
    result_path = root / "result.json"
    result = (
        json.loads(result_path.read_text())
        if result_path.exists()
        else {"worker": kind, "status": "RUNNING", "data_origin": "SYNTHETIC", "cases": {}}
    )
    pending = []
    try:
        for stage in ["lease", "before", "after", "commit", "stale"]:
            if result["cases"].get(stage, {}).get("status") == "PASS":
                continue
            directory = root / stage
            directory.mkdir(exist_ok=True)
            env = "m3-m6-worker-" + kind + "-" + stage
            task = {"environment": env, "worker": kind, "stage": stage}
            if (directory / "task.json").exists():
                task = json.loads((directory / "task.json").read_text())
            else:
                seeded = prepare(
                    engine, env, principal, target=target, source=source, port=8081, seed=kind != "event"
                )
                if kind == "event":
                    for batch in seeded["inputs"]:
                        with Session(engine) as db:
                            RawIngestService(db).ingest(
                                [RawInput(**row) for row in batch["records"]],
                                environment_id=env,
                                collector_id=batch["collector_id"],
                                source_type=batch["source_type"],
                                principal=principal,
                                data_origin="SYNTHETIC",
                            )
                elif kind == "ai":
                    task["context_id"] = ContextManager(engine).build(
                        env, seeded["incident_id"], "scope-lab-web", principal
                    )["context_id"]
                else:
                    with Session(engine) as db:
                        DeterministicResponsePlanner(db).create(
                            env,
                            seeded["incident_id"],
                            expected_version=2,
                            scope_id="scope-lab-web",
                            principal=principal,
                        )
                    if kind == "verification":
                        for _ in range(3):
                            executed = ResponseWorker(engine).tick(env, principal)
                            assert executed["result"]["execution_outcome"] == "EXECUTION_SUCCESS"
                        body = spec(engine, env)
                        task["spec_id"] = VerificationService(engine).create(
                            env,
                            body["action_result_id"],
                            VerificationSpec.model_validate(body["spec"]),
                            principal,
                        )
                write(directory / "task.json", task)
                write(directory / "before.json", snapshot(engine, env))
                with Session(engine) as db:
                    write(
                        directory / "evidence-before.json",
                        list(
                            db.scalars(
                                select(EvidenceRow.evidence_id).where(EvidenceRow.environment_id == env)
                            )
                        ),
                    )
            if not (directory / "child.json").exists():
                if kind == "event" and stage == "stale":
                    # EI has no expiring lease: its entire transaction holds the environment row lock.
                    with ThreadPoolExecutor(max_workers=2) as pool:

                        def process(_):
                            with Session(engine) as db:
                                return EventIntelligenceEngine(db).process(env, principal=principal)

                        values = list(pool.map(process, range(2)))
                    write(directory / "concurrent.json", values)
                    assert (
                        sorted(v["processed"] for v in values)[0] == 0
                        and sum(v["processed"] > 0 for v in values) == 1
                    )
                    child = {"exit_code": 0, "messages": [{"kind": "serialized", "value": values}]}
                else:
                    run = subprocess.run(
                        [sys.executable, "tools/m6_worker_process.py", json.dumps(task)],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    (directory / "stdout.jsonl").write_text(run.stdout, encoding="utf-8")
                    (directory / "stderr.log").write_text(run.stderr, encoding="utf-8")
                    messages = [json.loads(line) for line in run.stdout.splitlines() if line.strip()]
                    child = {
                        "exit_code": run.returncode,
                        "messages": messages,
                        "finished_at": datetime.now(UTC).isoformat(),
                    }
                write(directory / "child.json", child)
                write(directory / "after-crash.json", snapshot(engine, env))
            child = json.loads((directory / "child.json").read_text())
            assert child["exit_code"] == (0 if stage == "stale" else 71), child
            if stage == "stale" and kind in {"task", "action", "verification"}:
                assert any(row["kind"] == "fenced" for row in child["messages"])
            pending.append((stage, env, task, directory, child))
            print(
                json.dumps({"worker": kind, "stage": stage, "physical_exit": child["exit_code"]}), flush=True
            )
        for stage, env, task, directory, child in pending:
            before = json.loads((directory / "before.json").read_text())
            after_crash = json.loads((directory / "after-crash.json").read_text())
            messages = {row["kind"]: row["value"] for row in child["messages"]}
            if kind == "event":
                if stage in {"lease", "before", "after"}:
                    assert (
                        after_crash["counts"]["event_groups"]
                        == after_crash["counts"]["correlation_decisions"]
                        == 0
                    )
                    assert (
                        before["audit"] == after_crash["audit"] and before["outbox"] == after_crash["outbox"]
                    )
                with Session(engine) as db:
                    recovered = EventIntelligenceEngine(db).process(env, principal=principal)
                if stage in {"commit", "stale"}:
                    assert recovered["processed"] == 0
                else:
                    assert recovered["processed"] == before["counts"]["normalized_events"]
                write(directory / "recovered.json", recovered)
                with Session(engine) as db:
                    assert EventIntelligenceEngine(db).process(env, principal=principal)["processed"] == 0
            elif kind in {"task", "action"}:
                lease = messages["lease"]
                if stage == "commit":
                    auth = messages["authorization"]
                    replay = ActionGateway(engine).dispatch(
                        env, lease["task_id"], lease["generation"], auth["authorization_id"], principal
                    )
                    assert replay["disposition"] == "DUPLICATE"
                else:
                    assert not after_crash["counts"]["action_execution_results"]
                    delay = (datetime.fromisoformat(lease["expires_at"]) - datetime.now(UTC)).total_seconds()
                    if delay > 0:
                        time.sleep(delay + 0.1)
                    refresh_health(engine, env, principal)
                    worker = ResponseWorker(engine)
                    replay = worker.tick(env, principal)
                    if replay["status"] == "IDLE":
                        time.sleep(1.15)
                        replay = worker.tick(env, principal)
                    assert (
                        replay["lease"]["task_id"] == lease["task_id"] and replay["lease"]["generation"] == 2
                    )
                    assert replay["result"]["execution_outcome"] == "EXECUTION_SUCCESS"
                    try:
                        with Session(engine) as db:
                            AuthorizationService(db).authorize_task(
                                env, lease["task_id"], generation=lease["generation"], principal=principal
                            )
                    except LeaseLostError:
                        pass
                    else:
                        raise AssertionError("stale worker authorization accepted")
                write(directory / "recovery.json", replay)
                current = snapshot(engine, env)
                assert current["counts"]["action_requests"] == 1
                assert (
                    sum(
                        row["execution_outcome"] == "EXECUTION_SUCCESS"
                        for row in current["rows"]["action_execution_results"]
                    )
                    == 1
                )
            elif kind == "verification":
                service, old = VerificationService(engine), messages["lease"]
                if stage == "commit":
                    replay = service.run_claim(env, old, principal)
                    assert replay["duplicate"] and replay["evidence_id"] == messages["result"]["evidence_id"]
                else:
                    assert after_crash["counts"]["verification_observations"] == 0
                    with Session(engine) as db:
                        actual = sorted(
                            db.scalars(
                                select(EvidenceRow.evidence_id).where(EvidenceRow.environment_id == env)
                            )
                        )
                    assert actual == sorted(json.loads((directory / "evidence-before.json").read_text()))
                    with engine.connect() as connection:
                        seconds = connection.scalar(
                            text(
                                "SELECT GREATEST(0,EXTRACT(EPOCH FROM (lease_until-clock_timestamp()))) FROM verification_checks WHERE spec_id=:s AND check_id=:c"
                            ),
                            {"s": old["spec_id"], "c": old["check_id"]},
                        )
                    if seconds:
                        time.sleep(float(seconds) + 0.1)
                    refresh_health(engine, env, principal)
                    recovered = service.claim(env, principal, spec_id=task["spec_id"])
                    assert recovered["check_id"] == old["check_id"] and recovered["generation"] == 2
                    try:
                        service.run_claim(env, old, principal)
                    except LeaseLostError:
                        pass
                    else:
                        raise AssertionError("stale verification lease accepted")
                    replay = service.run_claim(env, recovered, principal)
                    assert replay["status"] == "SUCCEEDED" and replay["assertion"] == "PASS"
                write(directory / "recovery.json", replay)
                assert snapshot(engine, env)["counts"]["verification_observations"] == 1
            elif kind == "ai":
                policy = settings.ai_policies[env]
                gateway = ModelGateway(engine, policy, settings.ai_providers[policy.provider_id])
                with Session(engine) as db:
                    request = db.scalar(select(ModelRequestRow).where(ModelRequestRow.environment_id == env))
                    until = request.lease_until
                if stage not in {"commit", "stale"}:
                    assert after_crash["counts"]["model_runs"] == 0
                    delay = (until - datetime.now(UTC)).total_seconds()
                    if delay > 0:
                        time.sleep(delay + 0.1)
                recovered = gateway.analyze(env, task["context_id"], principal)
                assert recovered["status"] == ("COMPLETED" if stage == "commit" else "FALLBACK")
                if stage != "commit":
                    assert recovered["error_code"] == "INTERRUPTED_CALL"
                assert gateway.analyze(env, task["context_id"], principal) == recovered
                write(directory / "recovery.json", recovered)
                current = snapshot(engine, env)
                assert current["counts"]["model_runs"] == 1 and current["counts"]["action_requests"] == 0
            final = snapshot(engine, env)
            assert final["audit_valid"] and final["high_risk_executions"] == 0
            write(directory / "final.json", final)
            result["cases"][stage] = {
                "status": "PASS",
                "environment": env,
                "physical_exit": child["exit_code"],
                "counts": final["counts"],
                "audit_valid": True,
                "high_risk_executions": 0,
            }
            if kind == "event":
                result["cases"][stage]["concurrency_semantics"] = (
                    "Environment row transaction lock; no standalone WorkerLease in Event Intelligence"
                )
            write(result_path, result)
            print(json.dumps({"worker": kind, "stage": stage, "status": "PASS"}), flush=True)
        assert len(result["cases"]) == 5
        result["status"] = "PASS"
    except Exception:
        result["status"] = "FAIL"
        (root / ("failure-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + ".txt")).write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        raise
    finally:
        write(result_path, result)


if __name__ == "__main__":
    main()
