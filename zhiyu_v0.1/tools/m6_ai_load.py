"""Ten sequential and bounded 2/4 concurrent real calls through the unchanged Gateway."""

import hashlib
import json
import os
import threading
import time
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from ai_fixture import snapshot
from m6_benchmarks import ROOT, distribution
from response_fixture import prepare

from zhiyu import __version__
from zhiyu.ai.analysis import AISituationAnalyzer
from zhiyu.ai.context import ContextManager
from zhiyu.ai.context_policy import ContextBudget, ContextPolicy
from zhiyu.ai.gateway import ModelGateway
from zhiyu.ai.provider import OpenAICompatibleProvider
from zhiyu.core.config import settings
from zhiyu.db.session import get_engine

OUTPUT = Path("/load-output")


class CountedTransport:
    """Observe invocations only; transport validation and behavior are delegated intact."""

    def __init__(self):
        self.calls = 0
        self.lock = threading.Lock()

    def complete(self, config, request):
        with self.lock:
            self.calls += 1
        return OpenAICompatibleProvider().complete(config, request)


def main():
    import sys

    target, source = sys.argv[1:3]
    os.environ["ZHIYU_LOCAL_MODEL_KEY"] = Path(os.environ["ZHIYU_MODEL_KEY_FILE"]).read_text().strip()
    output = OUTPUT / "ai-load.json"
    assert not output.exists(), "preserve prior attempt"
    engine = get_engine()
    principal = next(p for p in settings.service_tokens.values() if p.principal_id == "compose-smoke")
    transport = CountedTransport()
    report = {
        "status": "RUNNING",
        "code_version": __version__,
        "source_digest": hashlib.sha256(
            b"".join(
                p.relative_to(ROOT / "src").as_posix().encode() + p.read_bytes()
                for p in sorted((ROOT / "src").rglob("*.py"))
            )
        ).hexdigest(),
        "started_at": datetime.now(UTC).isoformat(),
        "model": "Real local Qwen2.5-1.5B, 1 server slot, 6 threads, 1200 output tokens, 110 second client timeout",
        "queue_delay": "NOT_SEPARATELY_MEASURED; provider_ms includes transport, server queue and inference. Synchronized arrivals, completion timestamps and server slot logs evidence queue behavior without inventing exact per-request queue latency.",
        "groups": [],
        "budget_exhaustion": None,
    }

    def save():
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    def setup(kind, index):
        env = f"m3-m6-d-{kind}-{index:02d}"
        fixture = prepare(engine, env, principal, target=target, source=source, port=8081)
        started = time.perf_counter()
        ctx = ContextManager(
            engine,
            ContextPolicy(
                budget=ContextBudget(
                    max_events=0, max_timeline_entries=0, max_prior_plans=0, max_state_items=4
                )
            ),
        ).build(env, fixture["incident_id"], "scope-lab-web", principal)
        elapsed = (time.perf_counter() - started) * 1000
        return env, ctx, elapsed

    def one(seed, barrier=None, check_budget=False):
        env, ctx, context_ms = seed
        policy = settings.ai_policies[env]
        if check_budget:
            policy = policy.model_copy(update={"budget": policy.budget.model_copy(update={"max_calls": 1})})
        gateway = ModelGateway(engine, policy, settings.ai_providers[policy.provider_id], adapter=transport)
        if barrier:
            barrier.wait(timeout=20)
        started_at = datetime.now(UTC).isoformat()
        started = time.perf_counter()
        analysis = AISituationAnalyzer(engine, gateway).analyze(env, ctx["context_id"], principal)
        analysis_ms = (time.perf_counter() - started) * 1000
        finished_at = datetime.now(UTC).isoformat()
        if check_budget:
            before = transport.calls
            denial = gateway.propose_plan(env, ctx["context_id"], principal, analysis=analysis.get("output"))
            assert denial["status"] == "FALLBACK" and denial["error_code"] == "AI_BUDGET_EXHAUSTED"
            assert transport.calls == before == 1
            report["budget_exhaustion"] = {
                "status": "PASS",
                "actual_provider_calls": before,
                "second_request": denial,
            }
        snap = snapshot(engine, env)
        assert snap["counts"]["action_requests"] == snap["counts"]["tasks"] == 0
        assert snap["audit_valid"] and snap["high_risk_executions"] == 0
        assert all(r["claim_kind"] == "INFERENCE" for r in snap["rows"]["state_entities"])
        row = {
            "environment": env,
            "context_id": ctx["context_id"],
            "context_build_ms": context_ms,
            "request_started_at": started_at,
            "finished_at": finished_at,
            "analysis_ms": analysis_ms,
            "analysis_status": analysis["status"],
            "runs": snap["rows"]["model_runs"],
            "receipts": snap["rows"]["model_receipts"],
            "executor_calls": 0,
            "audit_valid": True,
        }
        directory = OUTPUT / env
        directory.mkdir(exist_ok=False)
        for name, value in [("context", ctx), ("analysis", analysis), ("snapshot", snap), ("result", row)]:
            payload = json.dumps(value, ensure_ascii=False, default=str, indent=2)
            assert os.environ["ZHIYU_LOCAL_MODEL_KEY"] not in payload
            (directory / (name + ".json")).write_text(payload, encoding="utf-8")
        return row

    save()
    try:
        sequential = {"kind": "sequential", "concurrency": 1, "requested_calls": 10, "results": []}
        report["groups"].append(sequential)
        for index in range(10):
            sequential["results"].append(one(setup("sequential", index), check_budget=index == 0))
            save()
            print(json.dumps({"sequential_completed": index + 1}), flush=True)
        for concurrency in [2, 4]:
            kind = f"concurrent{concurrency}"
            seeds = [setup(kind, index) for index in range(concurrency)]
            barrier = threading.Barrier(concurrency)
            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                pending = [pool.submit(one, seed, barrier) for seed in seeds]
                rows = [future.result() for future in pending]
            report["groups"].append(
                {
                    "kind": kind,
                    "concurrency": concurrency,
                    "requested_calls": concurrency,
                    "elapsed_seconds": time.perf_counter() - started,
                    "results": rows,
                }
            )
            save()
            print(json.dumps({"concurrent_completed": concurrency}), flush=True)
        for group in report["groups"]:
            rows = group["results"]
            receipts = [receipt for row in rows for receipt in row["receipts"] if receipt["model_run_id"]]
            group.update(
                analysis_statuses=dict(Counter(r["analysis_status"] for r in rows)),
                error_codes=dict(Counter(r["error_code"] or "NONE" for r in receipts)),
                context_build=distribution([r["context_build_ms"] for r in rows]),
                analysis_latency=distribution([r["analysis_ms"] for r in rows]),
                provider_latency=distribution([r["provider_ms"] for r in receipts]),
                gateway_overhead=distribution([r["overhead_ms"] for r in receipts]),
                metered_responses=sum(
                    any(r["input_tokens"] and r["output_tokens"] for r in row["runs"]) for row in rows
                ),
            )
        assert transport.calls == 16
        report.update(
            status="COMPLETED_MEASUREMENT",
            provider_calls=transport.calls,
            finished_at=datetime.now(UTC).isoformat(),
        )
    except Exception:
        report.update(status="FAIL", failure=traceback.format_exc())
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
