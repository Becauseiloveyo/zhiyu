"""M1–M3 regression plus live HTTP/DB closed loops, worker restarts and measured verification."""

import json
import time

from m3_runtime_acceptance import M3Acceptance
from runtime_acceptance import main

PREFIX = """
import json,os,sys
from zhiyu.core.config import settings
from zhiyu.db.session import get_engine
from zhiyu.verification.runtime import VerificationService
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.replan import DeterministicReplanner
p=next(p for p in settings.service_tokens.values() if p.principal_id=='compose-smoke')
env,identifier=sys.argv[1:3]
"""
CRASH_CHECK = (
    PREFIX
    + "lease=VerificationService(get_engine()).claim(env,p,spec_id=identifier);print(json.dumps(lease),flush=True);os._exit(23)"
)
CRASH_DECISION = (
    PREFIX
    + "result=VerificationEngine(get_engine()).decide(env,identifier,p);print(result.model_dump_json(),flush=True);os._exit(24)"
)
CRASH_REPLAN = (
    PREFIX
    + "result=DeterministicReplanner(get_engine()).handle(env,identifier,p);print(json.dumps(result),flush=True);os._exit(25)"
)
PARALLEL = (
    PREFIX
    + """
import subprocess
workers=[subprocess.Popen([sys.executable,'-m','zhiyu.verification.worker','--environment',env,'--spec',identifier,'--principal',actor],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for actor in ['compose-smoke','compose-verify-b']]
results=[]
for worker in workers:
    out,err=worker.communicate(timeout=40)
    if worker.returncode: raise RuntimeError(err)
    results.append(json.loads(out))
print(json.dumps(results))
"""
)
FENCE = (
    PREFIX
    + """
from zhiyu.core.errors import LeaseLostError
try:
    VerificationService(get_engine()).run_claim(env,json.loads(sys.argv[3]),p)
except LeaseLostError:
    print(json.dumps({'fenced':True}))
else:
    raise RuntimeError('expired check lease accepted')
"""
)


class M4Acceptance(M3Acceptance):
    cleanup_profiles = ("response-test", "verification-test")

    def __init__(self, directory):
        super().__init__(directory)
        tokens = json.loads(self.env["ZHIYU_SERVICE_TOKENS"])
        for principal in tokens.values():
            principal["environment_ids"] += [
                "m3-m4-" + case for case in ["pass", "security", "offline", "business"]
            ]
            principal["permissions"] += [
                "verification:write",
                "verification:read",
                "verification:execute",
                "verification:replan",
            ]
        # Two distinct configured service identities; no runtime caller-supplied authority.
        import hashlib

        other = json.loads(json.dumps(next(iter(tokens.values()))))
        other["principal_id"] = "compose-verify-b"
        tokens[hashlib.sha256((self.token + "verification-worker-b").encode()).hexdigest()] = other
        self.env["ZHIYU_SERVICE_TOKENS"] = json.dumps(tokens)

    def fixture(self, verb, env, *args):
        return json.loads(
            self.compose(
                "exec", "-T", "api", "python", "tools/verification_fixture.py", verb, env, *args
            ).stdout
        )

    def call(self, path, body):
        status, value = self.request(path, body)
        if status != 200:
            raise RuntimeError(f"{path}: HTTP {status} {value}")
        return value

    def run(self, *, no_cache):
        benchmark, self.benchmark = self.benchmark, False
        super().run(no_cache=no_cache)
        self.compose(
            "--profile", "verification-test", "up", "-d", "--build", "verification-target", timeout=180
        )
        network = self.project + "_control"
        target_ip = self.container("response-target")["NetworkSettings"]["Networks"][network]["IPAddress"]
        bad_ip = self.container("verification-target")["NetworkSettings"]["Networks"][network]["IPAddress"]
        source_ip = self.container("api")["NetworkSettings"]["Networks"][network]["IPAddress"]
        self.report["verification_chains"] = {}
        for case, expected in [
            ("pass", "PASS"),
            ("security", "FAIL"),
            ("offline", "INCONCLUSIVE"),
            ("business", "FAIL"),
        ]:
            env = "m3-m4-" + case
            body = {"environment_id": env}
            fixture = self.fixture("seed", env, bad_ip if case == "business" else target_ip, source_ip)
            plan = self.call(
                "/v1/continuous-plans",
                {
                    **body,
                    "incident_id": fixture["incident_id"],
                    "expected_version": 2,
                    "scope_id": "scope-lab-web",
                },
            )
            self.check(
                "m4_" + case + "_plan",
                len(plan["tasks"]) == 4 and plan["max_replans"] == 2 and plan["total_model_calls"] == 0,
            )
            actions = [self.call("/v1/response/worker/tick", body) for _ in range(4)]
            self.check(
                "m4_" + case + "_action_execution",
                all(a["result"]["execution_outcome"] == "EXECUTION_SUCCESS" for a in actions),
            )
            target_service = "verification-target" if case == "business" else "response-target"
            heads_before = self.compose("logs", "--no-color", target_service).stdout.count('"method": "HEAD"')
            spec_body = self.fixture("spec", env, case)
            spec_body["policy"] = {
                "validity_seconds": 300,
                "evidence_ttl_seconds": 300,
                "sensor_ttl_seconds": 300,
            }
            spec_id = self.call("/v1/verifications", spec_body)["verification_spec_id"]
            self.check(
                "m4_" + case + "_spec_idempotent",
                self.call("/v1/verifications", spec_body)["verification_spec_id"] == spec_id,
            )
            if case == "pass":
                time.sleep(1.1)  # Allow the shared Scope probe-rate budget to become ready.
                old = json.loads(
                    self.compose(
                        "exec", "-T", "api", "python", "-c", CRASH_CHECK, env, spec_id, expected=23
                    ).stdout
                )
                workers = json.loads(
                    self.compose("exec", "-T", "api", "python", "-c", PARALLEL, env, spec_id).stdout
                )
                self.check(
                    "m4_two_verification_workers",
                    len({r["lease"]["check_id"] for r in workers}) == 2,
                    workers,
                )
                self.compose("restart", "api")
                self.locate_api()
                self.await_http("/ready", 200)
                self.compose("stop", "postgres")
                self.check(
                    "m4_postgres_down_readiness",
                    self.fetch("/health")[0] == 200 and self.fetch("/ready")[0] == 503,
                )
                self.compose("start", "postgres")
                self.wait_service("postgres")
                self.await_http("/ready", 200)
                time.sleep(11)
                fenced = json.loads(
                    self.compose(
                        "exec", "-T", "api", "python", "-c", FENCE, env, spec_id, json.dumps(old)
                    ).stdout
                )
                self.check("m4_expired_verification_worker_fenced", fenced["fenced"])
                recovered = json.loads(
                    self.compose(
                        "exec",
                        "-T",
                        "api",
                        "python",
                        "-m",
                        "zhiyu.verification.worker",
                        "--environment",
                        env,
                        "--spec",
                        spec_id,
                        "--principal",
                        "compose-smoke",
                    ).stdout
                )
                self.check(
                    "m4_verification_worker_recovered",
                    recovered["lease"]["generation"] == 2 and recovered["result"]["assertion"] == "PASS",
                    recovered,
                )
                crashed = json.loads(
                    self.compose(
                        "exec", "-T", "api", "python", "-c", CRASH_DECISION, env, spec_id, expected=24
                    ).stdout
                )
                self.compose("restart", "api")
                self.locate_api()
                self.await_http("/ready", 200)
                result = self.call(
                    "/v1/verifications/" + spec_id + "/decide",
                    body,
                )
                self.check("m4_decision_before_crash_idempotent", crashed == result)
            else:
                completed = 0
                deadline = time.monotonic() + 15
                while completed < 3 and time.monotonic() < deadline:
                    tick = self.call("/v1/verifications/" + spec_id + "/tick", body)
                    if "result" in tick:
                        completed += 1
                    else:
                        time.sleep(0.2)
                self.check("m4_" + case + "_checks_scheduled_with_scope_rate", completed == 3)
                result = self.call("/v1/verifications/" + spec_id + "/decide", body)
            self.check("m4_" + case + "_verdict", result["status"] == expected, result)
            heads_after = self.compose("logs", "--no-color", target_service).stdout.count('"method": "HEAD"')
            self.check(
                "m4_" + case + "_new_independent_http_request",
                heads_after == heads_before + 1,
                {"before_checks": heads_before, "after_checks": heads_after},
            )
            if case == "security":
                replan = json.loads(
                    self.compose(
                        "exec",
                        "-T",
                        "api",
                        "python",
                        "-c",
                        CRASH_REPLAN,
                        env,
                        result["verification_id"],
                        expected=25,
                    ).stdout
                )
                self.compose("restart", "api")
                self.locate_api()
                self.await_http("/ready", 200)
                repeated = self.call("/v1/verification-results/" + result["verification_id"] + "/apply", body)
                self.check(
                    "m4_replan_before_crash_idempotent",
                    replan == repeated and replan["status"] == "CREATED",
                    replan,
                )
                extra = self.call("/v1/response/worker/tick", body)
                self.check(
                    "m4_replan_new_authorization_and_execution",
                    extra["result"]["execution_outcome"] == "EXECUTION_SUCCESS"
                    and extra["authorization_id"] not in [a["authorization_id"] for a in actions],
                )
            else:
                replan = self.call("/v1/verification-results/" + result["verification_id"] + "/apply", body)
            snapshot = self.fixture("snapshot", env)
            self.check(
                "m4_" + case + "_evidence_transaction_and_risk",
                snapshot["observation_evidence_atomic"] and snapshot["high_risk_executions"] == 0,
            )
            evidence = snapshot["rows"]["verification_observations"]
            self.check(
                "m4_" + case + "_independent_evidence",
                len(evidence) == 3
                and len({e["evidence_id"] for e in evidence}) == 3
                and all(e["executor_version"] == "verification-check/1.0.0" for e in evidence),
            )
            operations = snapshot["audit"]
            required = [
                "VerificationSpecCreated",
                "VerificationStarted",
                "CheckStarted",
                "CheckCompleted",
                "EffectivenessEvaluated",
                "EnvironmentStateUpdated",
                "ReplanRequested",
            ]
            self.check(
                "m4_" + case + "_audit_outbox",
                snapshot["audit_valid"]
                and all(
                    operations.get(k, 0) > 0 and operations[k] == snapshot["outbox"].get(k) for k in required
                ),
            )
            self.check(
                "m4_" + case + "_no_false_closure",
                snapshot["rows"]["incidents"][0]["status"] not in ["CLOSED", "CONTAINED", "RESOLVED"],
            )
            status, metrics = self.fetch("/v1/verification-metrics?environment_id=" + env)
            self.check(
                "m4_" + case + "_metrics",
                status == 200
                and metrics["verification_total"] == 1
                and metrics["verification_evidence_count"] == 4,
                metrics,
            )
            status, visible = self.fetch("/v1/verifications/" + result["verification_id"])
            self.check(
                "m4_" + case + "_api_lineage",
                status == 200
                and visible["runtime"]["plan_id"] == plan["plan_id"]
                and visible["effectiveness"] is not None,
            )
            self.report["verification_chains"][case] = {
                "result": result,
                "replan": replan,
                "snapshot": snapshot,
                "metrics": metrics,
            }
            self.save()
        if benchmark:
            name = self.project + "-verification-benchmark"
            runner = "import os,runpy,sys;os.environ['ZHIYU_DATABASE_URL']=os.environ['ZHIYU_TEST_DATABASE_URL'];sys.path.insert(0,'tools');runpy.run_path('tools/verification_benchmark.py',run_name='__main__')"
            self.compose(
                "--profile",
                "test",
                "run",
                "--no-deps",
                "-T",
                "--name",
                name,
                "tests",
                "python",
                "-c",
                runner,
                "--output",
                "/tmp/verification-benchmark.json",
                timeout=1800,
            )
            self.docker(
                "cp",
                name + ":/tmp/verification-benchmark.json",
                str(self.directory / "verification-benchmark.json"),
            )
            self.docker("rm", name)
            measured = json.loads((self.directory / "verification-benchmark.json").read_text())
            self.check(
                "m4_verification_benchmark_measured",
                measured["status"] == "PASS"
                and [r["verification_runs"] for r in measured["results"]] == [100, 1000],
                {
                    "results": [
                        {k: v for k, v in r.items() if k != "raw_samples_ms"} for r in measured["results"]
                    ]
                },
            )
            self.report["verification_benchmark"] = {
                "artifact": "verification-benchmark.json",
                "source_digest": measured["source_digest"],
            }
        self.save()


if __name__ == "__main__":
    raise SystemExit(main(M4Acceptance))
