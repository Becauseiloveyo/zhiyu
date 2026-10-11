"""Bounded large-load extensions of the retained M2/M3/M4 benchmark methods."""

import argparse
import hashlib
import json
import math
import platform
import statistics
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

import benchmark
import response_benchmark
import verification_benchmark
from sqlalchemy import text
from sqlalchemy.orm import Session

from zhiyu import __version__
from zhiyu.db.session import get_engine
from zhiyu.repositories.audit import AuditRepository

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("/load-output")


def distribution(values):
    ordered = sorted(values)
    return (
        {
            "count": len(ordered),
            "mean_ms": statistics.mean(ordered),
            "p50_ms": statistics.median(ordered),
            "p95_ms": ordered[math.ceil(len(ordered) * 0.95) - 1],
            "p99_ms": ordered[math.ceil(len(ordered) * 0.99) - 1],
            "max_ms": ordered[-1],
        }
        if ordered
        else {"count": 0}
    )


def database_metrics():
    with get_engine().connect() as c:
        return {
            "observed_at": datetime.now(UTC).isoformat(),
            "size_bytes": c.scalar(text("SELECT pg_database_size(current_database())")),
            "connections": c.scalar(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()")
            ),
            "postgres": c.scalar(text("SHOW server_version")),
        }


def inspect_environment(env):
    engine = get_engine()
    with engine.connect() as c:
        params = {"env": env}
        states = {
            table: dict(
                c.execute(
                    text(
                        "SELECT status,count(*) FROM " + table + " WHERE environment_id=:env GROUP BY status"
                    ),
                    params,
                ).all()
            )
            for table in ["tasks", "verification_checks"]
        }
        duplicate_actions = c.scalar(
            text("SELECT count(*)-count(DISTINCT task_id) FROM action_requests WHERE environment_id=:env"),
            params,
        )
        executions = dict(
            c.execute(
                text(
                    "SELECT r.side_effect,count(*) FROM action_execution_results r JOIN action_dispatches d USING(attempt_id) WHERE d.environment_id=:env GROUP BY r.side_effect"
                ),
                params,
            ).all()
        )
    with Session(engine) as db:
        valid = AuditRepository(db).verify_chain(env)
    assert valid and duplicate_actions == 0 and all(key == "NONE" for key in executions)
    return {
        "states": states,
        "duplicate_logical_actions": duplicate_actions,
        "side_effects": executions,
        "audit_valid": valid,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["events", "response", "verification"])
    parser.add_argument("--largest-budget-seconds", type=int, default=1200)
    args = parser.parse_args()
    assert 300 <= args.largest_budget_seconds <= 3600
    output = OUTPUT / (args.kind + ".json")
    assert not output.exists(), "preserve prior attempt"
    report = {
        "status": "RUNNING",
        "kind": args.kind,
        "code_version": __version__,
        "source_digest": hashlib.sha256(
            b"".join(
                p.relative_to(ROOT / "src").as_posix().encode() + p.read_bytes()
                for p in sorted((ROOT / "src").rglob("*.py"))
            )
        ).hexdigest(),
        "started_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "initial_database": database_metrics(),
        "method": "Sequential service-level synthetic inputs, real PostgreSQL; no HTTP API serialization in timings. Response uses bounded real read-only executors. Verification uses real loopback HEAD and three independent dimensions per run. No production SLA.",
        "partitioning": "Response chunks <=300 tasks, verification chunks <=100 three-check runs, each with a fresh environment/Incident/2-hour scope. This bounds fixture lifetime, not production tenant scaling. Original per-chunk methods and raw samples retained.",
        "verification_failure_semantics": "Last verification in each chunk deliberately fails security assertion, yields one bounded diagnostic replan. Its unexecuted next-plan tasks are intentional, not a hidden stalled queue.",
        "results": [],
    }

    def save():
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    save()
    try:
        levels = [1000, 10000, 100000] if args.kind == "events" else [100, 1000, 10000]
        for level in levels:
            start = time.perf_counter()
            budget = args.largest_budget_seconds if level == levels[-1] else None
            if args.kind == "events":
                result = benchmark.measure(
                    level, max_seconds=budget, progress_path=OUTPUT / "events.progress.json"
                )
                result["stage_batch_latency"] = {
                    key: distribution([r[key] for r in result["raw_batch_samples"]])
                    for key in ["ingest_ms", "group_correlate_ms", "promotion_ms"]
                }
                result["audit"] = inspect_environment(result["environment_id"])
                report["results"].append(result)
                save()
                continue
            units = 0
            chunks = []
            samples = {}
            item = {
                "requested": level,
                "unit": "read-only task" if args.kind == "response" else "individual check",
                "status": "RUNNING",
                "budget_seconds": budget,
                "chunks": chunks,
            }
            report["results"].append(item)
            while units < level:
                if budget and units and time.perf_counter() - start >= budget:
                    break
                if args.kind == "response":
                    value = response_benchmark.measure(min(300, level - units))
                    units += value["tasks_executed"]
                else:
                    value = verification_benchmark.measure(min(100, math.ceil((level - units) / 3)))
                    units += value["check_jobs"]
                value["audit"] = inspect_environment(value["environment_id"])
                for name, values in value["raw_samples_ms"].items():
                    samples.setdefault(name, []).extend(values)
                chunks.append(value)
                item.update(
                    actual=units, elapsed_seconds=time.perf_counter() - start, database=database_metrics()
                )
                save()
                print(
                    json.dumps(
                        {
                            "kind": args.kind,
                            "requested": level,
                            "completed": units,
                            "elapsed_seconds": item["elapsed_seconds"],
                        }
                    ),
                    flush=True,
                )
            item.update(
                status="COMPLETED" if units >= level else "PARTIAL_TIME_BUDGET",
                throughput_per_second=units / (time.perf_counter() - start),
                stage_latency={key: distribution(values) for key, values in samples.items()},
                intentional_unexecuted_tail_tasks=sum(
                    sum(v["audit"]["states"]["tasks"].get(state, 0) for state in ["QUEUED", "BLOCKED"])
                    for v in chunks
                ),
            )
            save()
        report.update(
            status="COMPLETED_MEASUREMENT",
            finished_at=datetime.now(UTC).isoformat(),
            final_database=database_metrics(),
        )
    except Exception:
        report.update(status="FAIL", failure=traceback.format_exc(), final_database=database_metrics())
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
