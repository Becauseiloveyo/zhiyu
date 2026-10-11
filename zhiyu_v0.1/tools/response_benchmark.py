"""Measured 100/1000 read-only task dispatches; synthetic fixture, never a production SLA."""

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from response_fixture import SCOPE, fixture_principal, prepare, refresh_health
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from zhiyu import __version__
from zhiyu.db.models import ActionRow, TaskRow
from zhiyu.db.response_authority import AuthorizationSnapshotRow
from zhiyu.db.response_planning import ResponsePlanRow
from zhiyu.db.session import get_engine
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.gateway import ActionGateway
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy
from zhiyu.response.scheduler import TaskScheduler

ROOT = Path(__file__).resolve().parents[1]


def distribution(samples):
    values = sorted(samples)
    return {
        "count": len(values),
        "mean_ms": statistics.mean(values),
        "p50_ms": statistics.median(values),
        "p95_ms": values[math.ceil(len(values) * 0.95) - 1],
        "min_ms": values[0],
        "max_ms": values[-1],
    }


def measure(count):
    engine = get_engine()
    environment = "m3-bench-" + str(count) + "-" + uuid4().hex[:8]
    principal = fixture_principal(environment)
    fixture = prepare(engine, environment, principal)
    samples = {
        k: []
        for k in [
            "plan_generation",
            "task_graph_creation",
            "authorization",
            "policy_gate",
            "scheduler_lease",
            "gateway_overhead",
            "safe_executor",
        ]
    }
    completed, plan_count = 0, 0
    start = time.perf_counter()
    refreshed = start
    while completed < count:
        if time.perf_counter() - refreshed > 45:
            refresh_health(engine, environment, principal)
            refreshed = time.perf_counter()
        # Distinct synthetic policy versions exercise plan creation without mutating Incident snapshots.
        policy = PlannerPolicy(policy_version=f"response-plan/benchmark/{plan_count}")
        with Session(engine) as db:
            plan = DeterministicResponsePlanner(db, policy).create(
                environment, fixture["incident_id"], expected_version=2, scope_id=SCOPE, principal=principal
            )
        with Session(engine) as db:
            metadata = db.get(ResponsePlanRow, plan.plan_id)
            samples["plan_generation"].append(metadata.generation_ms)
            samples["task_graph_creation"].append(metadata.graph_ms)
        plan_count += 1
        for _ in range(min(3, count - completed)):
            with Session(engine) as db:
                lease = TaskScheduler(db).claim(environment, principal)
            assert lease is not None
            samples["scheduler_lease"].append(lease["lease_ms"])
            with Session(engine) as db:
                decision = AuthorizationService(db).authorize_task(
                    environment, lease["task_id"], generation=lease["generation"], principal=principal
                )
            assert decision.outcome == "ALLOW", decision.reasons
            with Session(engine) as db:
                snapshot = db.get(AuthorizationSnapshotRow, decision.authorization_context_id)
                samples["authorization"].append(snapshot.authorization_ms)
                samples["policy_gate"].append(snapshot.policy_ms)
            result = ActionGateway(engine).dispatch(
                environment, lease["task_id"], lease["generation"], decision.authorization_id, principal
            )
            assert result["execution_outcome"] == "EXECUTION_SUCCESS", result
            samples["gateway_overhead"].append(result["gateway_overhead_ms"])
            samples["safe_executor"].append(result["executor_ms"])
            completed += 1
            if completed % 100 == 0:
                print(json.dumps({"completed_tasks": completed, "target": count}), flush=True)
    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count()).select_from(ActionRow).where(ActionRow.environment_id == environment)
            )
            == count
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(TaskRow)
                .where(TaskRow.environment_id == environment, TaskRow.status == "SUCCEEDED")
            )
            == count
        )
    return {
        "environment_id": environment,
        "synthetic_incidents": 1,
        "plans_created": plan_count,
        "tasks_created": plan_count * 3,
        "tasks_executed": count,
        "logical_actions": count,
        "unexecuted_tail_tasks": plan_count * 3 - count,
        "elapsed_seconds": time.perf_counter() - start,
        "stage_latency": {key: distribution(values) for key, values in samples.items()},
        "raw_samples_ms": samples,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[100, 1000])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if any(n not in {100, 1000} for n in args.sizes):
        raise ValueError("supported sizes are 100/1000")
    with get_engine().connect() as connection:
        postgres = connection.scalar(text("SELECT version()"))
    report = {
        "label": "SYNTHETIC response task benchmark; service calls over PostgreSQL, no HTTP serialization, no production SLA",
        "workload": "Sequential 100/1000 task dispatches. One fresh synthetic Incident per size; distinct synthetic policy versions produce 34/334 three-task plans. Last two tasks remain unexecuted. Real bounded database read executors; real HTTP probe latency is recorded separately in Docker golden chain. Fixture health refresh is outside stage measurements.",
        "code_version": __version__,
        "source_digest": hashlib.sha256(
            b"".join(
                p.relative_to(ROOT / "src").as_posix().encode() + p.read_bytes()
                for p in sorted((ROOT / "src").rglob("*.py"))
            )
        ).hexdigest(),
        "host": {
            "python": platform.python_version(),
            "os": platform.platform(),
            "cpus": os.cpu_count(),
            "postgres": postgres,
        },
        "started_at": datetime.now(UTC).isoformat(),
        "results": [],
    }
    for size in args.sizes:
        report["results"].append(measure(size))
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["finished_at"] = datetime.now(UTC).isoformat()
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
