"""At least 30 actual minutes of low load with real PostgreSQL, HEAD and local model."""

import argparse
import hashlib
import json
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

from ai_fixture import snapshot, spec
from response_fixture import prepare
from sqlalchemy import text
from sqlalchemy.orm import Session

from zhiyu import __version__
from zhiyu.ai.analysis import AISituationAnalyzer
from zhiyu.ai.context import ContextManager
from zhiyu.ai.context_policy import ContextBudget, ContextPolicy
from zhiyu.ai.gateway import ModelGateway
from zhiyu.core.config import settings
from zhiyu.db.session import get_engine
from zhiyu.domain.contracts import VerificationSpec
from zhiyu.response.planner import DeterministicResponsePlanner
from zhiyu.response.worker import ResponseWorker
from zhiyu.services.raw_ingest import RawIngestService, RawInput
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.runtime import VerificationService

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("/load-output")


def save(path, value):
    payload = json.dumps(value, ensure_ascii=False, default=str, indent=2)
    secret = os.environ.get("ZHIYU_LOCAL_MODEL_KEY", "")
    assert not secret or secret not in payload
    path.write_text(payload, encoding="utf-8")


def metrics(engine, prefix):
    with engine.connect() as c:
        result = {
            "database_size_bytes": c.scalar(text("SELECT pg_database_size(current_database())")),
            "connections": c.scalar(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()")
            ),
            "database_activity": dict(
                c.execute(
                    text(
                        "SELECT state,count(*) FROM pg_stat_activity WHERE datname=current_database() GROUP BY state"
                    )
                ).all()
            ),
        }
        for table in ["tasks", "verification_checks", "model_requests"]:
            result[table + "_states"] = dict(
                c.execute(
                    text(
                        "SELECT status,count(*) FROM "
                        + table
                        + " WHERE environment_id LIKE :prefix GROUP BY status"
                    ),
                    {"prefix": prefix + "%"},
                ).all()
            )
        result["pending_outbox"] = c.scalar(
            text("SELECT count(*) FROM outbox WHERE environment_id LIKE :prefix AND published_at IS NULL"),
            {"prefix": prefix + "%"},
        )
        result["active_task_leases"] = c.scalar(
            text(
                "SELECT count(*) FROM worker_leases l JOIN tasks t ON t.task_id=l.task_id WHERE t.environment_id LIKE :prefix AND t.status='RUNNING' AND l.expires_at>clock_timestamp()"
            ),
            {"prefix": prefix + "%"},
        )
        result["expired_running_tasks"] = c.scalar(
            text(
                "SELECT count(*) FROM tasks t JOIN worker_leases l ON l.lease_id=t.active_lease_id WHERE t.environment_id LIKE :prefix AND t.status='RUNNING' AND l.expires_at<=clock_timestamp()"
            ),
            {"prefix": prefix + "%"},
        )
    result["python_rss_status"] = [
        line
        for line in Path("/proc/self/status").read_text().splitlines()
        if line.startswith(("VmRSS:", "VmHWM:", "VmSwap:"))
    ]
    result["observed_at"] = datetime.now(UTC).isoformat()
    return result


def cycle(engine, principal, environment, index, target, source, directory):
    start = time.perf_counter()
    fixture = prepare(engine, environment, principal, target=target, source=source, port=8081)
    with Session(engine) as db:
        plan = DeterministicResponsePlanner(db).create(
            environment,
            fixture["incident_id"],
            expected_version=2,
            scope_id="scope-lab-web",
            principal=principal,
        )
    analysis = None
    if index % 10 == 0:
        ctx = ContextManager(
            engine,
            ContextPolicy(
                budget=ContextBudget(
                    max_events=0, max_timeline_entries=0, max_prior_plans=0, max_state_items=4
                )
            ),
        ).build(environment, fixture["incident_id"], "scope-lab-web", principal)
        policy = settings.ai_policies[environment]
        analysis = AISituationAnalyzer(
            engine, ModelGateway(engine, policy, settings.ai_providers[policy.provider_id])
        ).analyze(environment, ctx["context_id"], principal)
        save(directory / "model-analysis.json", analysis)
    receipts = [ResponseWorker(engine).tick(environment, principal) for _ in plan.tasks]
    assert all(
        r["result"]["execution_outcome"] == "EXECUTION_SUCCESS" and r["result"]["side_effect"] == "NONE"
        for r in receipts
    )
    body = spec(engine, environment)
    service = VerificationService(engine)
    identifier = service.create(
        environment, body["action_result_id"], VerificationSpec.model_validate(body["spec"]), principal
    )
    for _ in range(3):
        lease = service.claim(environment, principal, spec_id=identifier)
        assert lease is not None
        service.run_claim(environment, lease, principal)
    result = VerificationEngine(engine).decide(environment, identifier, principal)
    assert result.status == "PASS", result.status
    first = snapshot(engine, environment)
    duplicates = 0
    for batch in fixture["inputs"]:
        with Session(engine) as db:
            replay = RawIngestService(db).ingest(
                [RawInput(**r) for r in batch["records"]],
                environment_id=environment,
                collector_id=batch["collector_id"],
                source_type=batch["source_type"],
                data_origin="SYNTHETIC",
                principal=principal,
            )
        assert replay["accepted"] == 0 and replay["errors"] == 0
        duplicates += replay["duplicates"]
    final = snapshot(engine, environment)
    assert final["counts"] == first["counts"] and duplicates == 4
    assert final["audit_valid"] and final["high_risk_executions"] == 0
    assert final["counts"]["tasks"] == final["counts"]["action_requests"] == 3
    save(directory / "snapshot.json", final)
    save(directory / "receipts.json", receipts)
    if analysis is not None:
        assert any(r["input_tokens"] > 0 and r["output_tokens"] > 0 for r in final["rows"]["model_runs"]), (
            "scheduled model call must have actual metered response"
        )
    row = {
        "environment": environment,
        "cycle": index,
        "started_at": fixture.get("created_at"),
        "finished_at": datetime.now(UTC).isoformat(),
        "seconds": time.perf_counter() - start,
        "events": 4,
        "replay_duplicates": duplicates,
        "tasks": 3,
        "checks": 3,
        "verification": result.status,
        "analysis_status": analysis["status"] if analysis else "NOT_SCHEDULED",
        "counts": final["counts"],
        "audit_valid": True,
        "ai_actions": 0,
        "high_risk_actions": 0,
    }
    save(directory / "result.json", row)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("source")
    parser.add_argument("--seconds", type=int, default=1800)
    parser.add_argument("--kind", choices=["pilot", "soak"], default="soak")
    args = parser.parse_args()
    os.environ["ZHIYU_LOCAL_MODEL_KEY"] = Path(os.environ["ZHIYU_MODEL_KEY_FILE"]).read_text().strip()
    assert 1 <= args.seconds <= 2100 and (args.kind == "pilot" or args.seconds >= 1800)
    output = OUTPUT / (args.kind + ".json")
    assert not output.exists(), "do not overwrite a previous attempt"
    engine = get_engine()
    principal = next(p for p in settings.service_tokens.values() if p.principal_id == "compose-smoke")
    prefix = "m3-m6-d-" + args.kind + "-"
    report = {
        "status": "RUNNING",
        "label": "SYNTHETIC low load; real DB/HTTP and periodic local model; not long-term stability or SLA",
        "code_version": __version__,
        "source_digest": hashlib.sha256(
            b"".join(
                p.relative_to(ROOT / "src").as_posix().encode() + p.read_bytes()
                for p in sorted((ROOT / "src").rglob("*.py"))
            )
        ).hexdigest(),
        "started_at": datetime.now(UTC).isoformat(),
        "requested_seconds": args.seconds,
        "nominal_cycle_seconds": 60,
        "outbox_consumer": "NOT_CONFIGURED; pending messages are measured durable backlog, not silently claimed as delivered",
        "initial_metrics": metrics(engine, prefix),
        "cycles": [],
    }
    save(output, report)
    clock = time.monotonic()
    try:
        index = 0
        while time.monotonic() - clock < args.seconds:
            directory = OUTPUT / (args.kind + f"-{index:02d}")
            directory.mkdir(exist_ok=False)
            row = cycle(
                engine, principal, prefix + f"{index:02d}", index, args.target, args.source, directory
            )
            row["metrics"] = metrics(engine, prefix)
            assert row["metrics"]["expired_running_tasks"] == 0
            report["cycles"].append(row)
            report["elapsed_seconds"] = time.monotonic() - clock
            save(output, report)
            print(
                json.dumps(
                    {"completed_cycles": len(report["cycles"]), "elapsed_seconds": report["elapsed_seconds"]}
                ),
                flush=True,
            )
            index += 1
            next_cycle = min(index * 60, args.seconds)
            while time.monotonic() - clock < next_cycle:
                time.sleep(min(5, next_cycle - (time.monotonic() - clock)))
        report.update(
            status="COMPLETED",
            elapsed_seconds=time.monotonic() - clock,
            finished_at=datetime.now(UTC).isoformat(),
            final_metrics=metrics(engine, prefix),
        )
    except Exception:
        report.update(status="FAIL", failure=traceback.format_exc(), elapsed_seconds=time.monotonic() - clock)
        raise
    finally:
        save(output, report)


if __name__ == "__main__":
    main()
