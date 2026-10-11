"""100/1000 independently observed synthetic verification runs, no production SLA."""

import argparse
import hashlib
import json
import platform
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

from response_benchmark import distribution
from response_fixture import SCOPE, fixture_principal, prepare, refresh_health
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from verification_fixture import spec_body

from zhiyu import __version__
from zhiyu.db.models import ScopeRow
from zhiyu.db.session import get_engine
from zhiyu.db.verification_decisions import EffectivenessRow
from zhiyu.db.verification_replan import ReplanDecisionRow, VerificationStateUpdateRow
from zhiyu.db.verification_runtime import VerificationObservationRow, VerificationRuntimeRow
from zhiyu.domain.contracts import VerificationSpec
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy, emit
from zhiyu.response.worker import ResponseWorker
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.replan import DeterministicReplanner, activate
from zhiyu.verification.runtime import VerificationService

ROOT = Path(__file__).resolve().parents[1]


def measure(size):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            calls.append(time.perf_counter())
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    engine = get_engine()
    env = "m3-m4-bench-" + str(size) + "-" + uuid4().hex[:8]
    principal = fixture_principal(env)
    principal = principal.model_copy(
        update={
            "permissions": principal.permissions
            | {"verification:write", "verification:execute", "verification:replan", "verification:read"}
        }
    )
    try:
        fixture = prepare(
            engine, env, principal, target="127.0.0.1", source="127.0.0.2", port=server.server_port
        )
        with Session(engine) as db, db.begin():
            scope = db.get(ScopeRow, (SCOPE, env))
            scope.max_requests_per_second = 100
            scope.version += "-SYNTHETIC-BENCH-100RPS"
            emit(
                db,
                env,
                "ScopeDefinition",
                scope.scope_id,
                "SyntheticBenchmarkRateConfigured",
                "100 RPS ceiling for local loopback-only performance fixture",
                principal.principal_id,
            )
        with Session(engine) as db:
            plan = DeterministicResponsePlanner(
                db, PlannerPolicy(include_http_probe=True, max_replans=2)
            ).create(env, fixture["incident_id"], expected_version=2, scope_id=SCOPE, principal=principal)
        activate(engine, env, plan.plan_id, principal)
        for _ in range(4):
            assert (
                ResponseWorker(engine).tick(env, principal)["result"]["execution_outcome"]
                == "EXECUTION_SUCCESS"
            )
        base = spec_body(engine, env)
        service = VerificationService(engine)
        samples = {
            k: []
            for k in [
                "spec_generation",
                "check_scheduling",
                "security_check",
                "business_check",
                "observation_check",
                "decision",
                "state_update",
                "replan_evaluation",
                "replan_creation",
            ]
        }
        start = refresh = time.perf_counter()
        for index in range(size):
            if time.perf_counter() - refresh > 40:
                refresh_health(engine, env, principal)
                refresh = time.perf_counter()
            # Distinct request identities, same post-action read-only objective; fresh observations each time.
            body = spec_body(engine, env, "security" if index == size - 1 else "pass", str(index))
            spec = VerificationSpec.model_validate(body["spec"])
            service.create(env, base["action_result_id"], spec, principal)
            for _ in range(3):
                clock = time.perf_counter()
                lease = service.claim(env, principal, spec_id=spec.verification_spec_id)
                while lease is None:
                    time.sleep(0.02)
                    lease = service.claim(env, principal, spec_id=spec.verification_spec_id)
                samples["check_scheduling"].append((time.perf_counter() - clock) * 1000)
                service.run_claim(env, lease, principal)
            result = VerificationEngine(engine).decide(env, spec.verification_spec_id, principal)
            assert result.status == ("FAIL" if index == size - 1 else "PASS")
            receipt = DeterministicReplanner(engine).handle(env, result.verification_id, principal)
            assert receipt["status"] == ("CREATED" if index == size - 1 else "NO_REPLAN")
            with Session(engine) as db:
                runtime = db.get(VerificationRuntimeRow, spec.verification_spec_id)
                samples["spec_generation"].append(runtime.generation_ms)
                for row in db.scalars(
                    select(VerificationObservationRow).where(
                        VerificationObservationRow.spec_id == spec.verification_spec_id
                    )
                ):
                    samples[
                        {
                            "security-context": "security_check",
                            "business-health": "business_check",
                            "observation-health": "observation_check",
                        }[row.check_id]
                    ].append(row.latency_ms)
                samples["decision"].append(db.get(EffectivenessRow, result.verification_id).decision_ms)
                samples["state_update"].append(
                    db.get(VerificationStateUpdateRow, result.verification_id).latency_ms
                )
                elapsed = db.get(ReplanDecisionRow, result.verification_id).latency_ms
                samples["replan_evaluation"].append(elapsed)
                if receipt["status"] == "CREATED":
                    samples["replan_creation"].append(elapsed)
        return {
            "environment_id": env,
            "verification_runs": size,
            "configured_scope_max_rps": 100,
            "check_jobs": size * 3,
            "pass": size - 1,
            "fail": 1,
            "replans_created": 1,
            "http_requests": len(calls),
            "elapsed_seconds": time.perf_counter() - start,
            "stage_latency": {k: distribution(v) for k, v in samples.items()},
            "raw_samples_ms": samples,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sizes", type=int, nargs="+", default=[100, 1000])
    args = parser.parse_args()
    if any(s not in {100, 1000} for s in args.sizes):
        raise ValueError("supported sizes 100/1000")
    with get_engine().connect() as connection:
        postgres = connection.scalar(text("SHOW server_version"))
    report = {
        "status": "RUNNING",
        "code_version": __version__,
        "label": "SYNTHETIC; sequential PostgreSQL and real local HEAD; no production SLA",
        "source_digest": hashlib.sha256(
            b"".join(
                p.relative_to(ROOT / "src").as_posix().encode() + p.read_bytes()
                for p in sorted((ROOT / "src").rglob("*.py"))
            )
        ).hexdigest(),
        "host": {"python": platform.python_version(), "os": platform.platform(), "postgres": postgres},
        "started_at": datetime.now(UTC).isoformat(),
        "results": [],
    }
    for size in args.sizes:
        report["results"].append(measure(size))
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report.update(status="PASS", finished_at=datetime.now(UTC).isoformat())
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
