"""Full M1/M2 regression plus deterministic controlled action and restart acceptance."""

import json
import time

from m2_runtime_acceptance import M2Acceptance
from runtime_acceptance import main

SETUP = """
import json,sys
sys.path.insert(0,'tools')
from response_fixture import prepare
from zhiyu.core.config import settings
from zhiyu.db.session import get_engine
p=next(p for p in settings.service_tokens.values() if p.principal_id=='compose-smoke')
print(json.dumps(prepare(get_engine(),'m3-golden',p,target=sys.argv[1],source=sys.argv[2],port=8081,seed=False)))
"""
SNAPSHOT = """
import json,hashlib
from sqlalchemy import text
from sqlalchemy.orm import Session
from zhiyu.db.session import get_engine
from zhiyu.repositories.audit import AuditRepository
tables=['incidents','plans','response_plan_metadata','tasks','task_runtime','task_graph_edges','worker_leases','action_requests','action_control','authorization_contexts','authorization_decisions','response_authorization_snapshots','action_dispatches']
with get_engine().connect() as c:
    filters={'worker_leases':'task_id IN (SELECT task_id FROM tasks WHERE environment_id=:env)', 'authorization_decisions':'action_id IN (SELECT action_id FROM action_requests WHERE environment_id=:env)'}
    rows={t:c.scalars(text('SELECT row_to_json(r) FROM '+t+' r WHERE '+filters.get(t,'environment_id=:env')+' ORDER BY row_to_json(r)::text'),{'env':'m3-golden'}).all() for t in tables}
    rows['action_execution_results']=c.scalars(text("SELECT row_to_json(r) FROM action_execution_results r JOIN action_dispatches d USING(attempt_id) WHERE d.environment_id='m3-golden' ORDER BY r.attempt_id")).all()
    operations=dict(c.execute(text("SELECT operation,count(*) FROM audit_entries WHERE environment_id='m3-golden' GROUP BY operation")).all())
    outbox=dict(c.execute(text("SELECT event_type,count(*) FROM outbox WHERE environment_id='m3-golden' GROUP BY event_type")).all())
    verification=c.scalar(text("SELECT count(*) FROM verification_results WHERE environment_id='m3-golden'"))
with Session(get_engine()) as db: valid=AuditRepository(db).verify_chain('m3-golden')
print(json.dumps({'counts':{k:len(v) for k,v in rows.items()},'hash':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'audit':operations,'outbox':outbox,'audit_valid':valid,'verification_results':verification,'incident_status':rows['incidents'][0]['status']}))
"""
CRASH_WORKER = """
import json,os
from sqlalchemy.orm import Session
from zhiyu.core.config import settings
from zhiyu.db.session import get_engine
from zhiyu.response.scheduler import TaskScheduler
p=next(p for p in settings.service_tokens.values() if p.principal_id=='compose-smoke')
with Session(get_engine()) as db: lease=TaskScheduler(db).claim('m3-golden',p)
print(json.dumps(lease),flush=True)
os._exit(23)
"""


class M3Acceptance(M2Acceptance):
    cleanup_profiles = ("response-test",)

    def __init__(self, directory):
        super().__init__(directory)
        tokens = json.loads(self.env["ZHIYU_SERVICE_TOKENS"])
        for principal in tokens.values():
            principal["environment_ids"].append("m3-golden")
            principal["permissions"] += [
                "response:plan",
                "response:read",
                "response:execute",
                "response:admin",
            ] + [
                "capability:" + c
                for c in [
                    "collect_resource_context",
                    "query_event_history",
                    "query_incident_evidence",
                    "safe_http_probe",
                    "check_service_reachability",
                ]
            ]
        self.env["ZHIYU_SERVICE_TOKENS"] = json.dumps(tokens)

    def m3_snapshot(self):
        return json.loads(self.compose("exec", "-T", "api", "python", "-c", SNAPSHOT).stdout)

    def run(self, *, no_cache):
        benchmark, self.benchmark = self.benchmark, False
        super().run(no_cache=no_cache)
        self.compose("--profile", "response-test", "up", "-d", "--build", "response-target", timeout=180)
        target = self.container("response-target")
        api = self.container("api")
        network = self.project + "_control"
        target_ip = target["NetworkSettings"]["Networks"][network]["IPAddress"]
        source_ip = api["NetworkSettings"]["Networks"][network]["IPAddress"]
        self.check(
            "m3_isolated_target",
            not target["HostConfig"]["PortBindings"] and target["HostConfig"]["ReadonlyRootfs"],
            {"target_ip": target_ip, "source_ip": source_ip, "port": 8081},
        )
        fixture = json.loads(
            self.compose("exec", "-T", "api", "python", "-c", SETUP, target_ip, source_ip).stdout
        )
        (self.directory / "m3-effective-inputs.json").write_text(
            json.dumps(fixture, indent=2), encoding="utf-8"
        )
        for batch in fixture["inputs"]:
            status, value = self.request("/v1/events/raw-batches", batch)
            self.check("m3_raw_" + batch["source_type"], status == 202 and value["errors"] == 0)
        status, value = self.request("/v1/intelligence/process", {"environment_id": "m3-golden"})
        self.check("m3_incident_created", status == 200 and value["incidents"]["created"] == 1, value)
        incident = next(x["incident_id"] for x in value["incidents"]["results"] if x["incident_id"])
        status, _ = self.request(
            f"/v1/incidents/{incident}/transitions",
            {"environment_id": "m3-golden", "expected_version": 1, "target": "TRIAGED"},
        )
        self.check("m3_incident_triaged", status == 200)
        body = {
            "environment_id": "m3-golden",
            "scope_id": "scope-lab-web",
            "expected_version": 2,
            "include_http_probe": True,
        }
        status, plan = self.request(f"/v1/incidents/{incident}/plans", body)
        self.check(
            "m3_plan_and_graph",
            status == 200 and len(plan["tasks"]) == 4 and plan["total_model_calls"] == 0,
            plan,
        )
        _, repeated = self.request(f"/v1/incidents/{incident}/plans", body)
        self.check("m3_plan_replay", repeated == plan)
        # A real worker process dies with a durable outstanding lease.
        crashed = self.compose("exec", "-T", "api", "python", "-c", CRASH_WORKER, expected=23)
        old = json.loads(crashed.stdout)
        self.check("m3_worker_crash_with_lease", old["generation"] == 1, old)
        self.compose("restart", "api")  # Stateless scheduler/gateway process restart.
        self.locate_api()
        self.await_http("/ready", 200)
        status, retry_claim = self.request("/v1/response/claim", {"environment_id": "m3-golden"})
        self.check(
            "m3_scheduler_restart_valid_lease", status == 200 and retry_claim["lease"] is None, retry_claim
        )
        time.sleep(21)
        # Expiry detection establishes backoff; a subsequent worker process acquires generation 2.
        self.request("/v1/response/claim", {"environment_id": "m3-golden"})
        time.sleep(1.1)
        worker = json.loads(
            self.compose(
                "exec",
                "-T",
                "api",
                "python",
                "-m",
                "zhiyu.response.worker",
                "--environment",
                "m3-golden",
                "--principal",
                "compose-smoke",
            ).stdout
        )
        self.check(
            "m3_worker_restart_recovery",
            worker["lease"]["task_id"] == old["task_id"]
            and worker["lease"]["generation"] == 2
            and worker["result"]["execution_outcome"] == "EXECUTION_SUCCESS",
            worker,
        )
        status, stale = self.request(
            f"/v1/tasks/{old['task_id']}/authorizations", {"environment_id": "m3-golden", "generation": 1}
        )
        self.check("m3_old_worker_rejected", status == 409 and stale["detail"] == "lease_lost", stale)
        results = [worker]
        for _ in range(3):
            status, value = self.request("/v1/response/worker/tick", {"environment_id": "m3-golden"})
            self.check(
                "m3_execute_task_" + str(len(results)),
                status == 200 and value["result"]["execution_outcome"] == "EXECUTION_SUCCESS",
                value,
            )
            results.append(value)
        probe = next(x for x in results if x["result"]["executor"] == "safe_http_probe")
        logs = self.compose("logs", "--no-color", "response-target").stdout
        self.check(
            "m3_real_http_head",
            logs.count('"method": "HEAD"') == 1 and probe["result"]["output"]["status_code"] == 200,
            {"receipt": probe["result"], "head_calls": logs.count('"method": "HEAD"')},
        )
        saved = self.m3_snapshot()
        required = {
            "PlanCreated",
            "TaskCreated",
            "TaskLeased",
            "TaskStarted",
            "AuthorizationEvaluated",
            "PolicyAllowed",
            "ActionRequested",
            "ActionStarted",
            "ActionSucceeded",
            "TaskSucceeded",
        }
        self.check(
            "m3_audit_outbox",
            saved["audit_valid"] and required <= set(saved["audit"]) and required <= set(saved["outbox"]),
            saved,
        )
        self.check(
            "m3_execution_not_security_verification",
            saved["verification_results"] == 0 and saved["incident_status"] == "TRIAGED",
        )
        self.compose("restart", "api")
        self.locate_api()
        self.await_http("/ready", 200)
        self.check("m3_api_gateway_restart_persistence", self.m3_snapshot()["hash"] == saved["hash"])
        execute = {
            "environment_id": "m3-golden",
            "generation": probe["lease"]["generation"],
            "authorization_id": probe["authorization_id"],
            "action_digest": probe["result"]["action_digest"],
        }
        status, replay = self.request(f"/v1/tasks/{probe['lease']['task_id']}/execute", execute)
        logs = self.compose("logs", "--no-color", "response-target").stdout
        self.check(
            "m3_gateway_replay_no_duplicate_probe",
            status == 200
            and replay["disposition"] == "DUPLICATE"
            and logs.count('"method": "HEAD"') == 1
            and self.m3_snapshot()["hash"] == saved["hash"],
            replay,
        )
        self.compose("stop", "postgres")
        self.check(
            "m3_database_down_readiness", self.fetch("/health")[0] == 200 and self.fetch("/ready")[0] == 503
        )
        self.compose("start", "postgres")
        self.wait_service("postgres")
        self.await_http("/ready", 200)
        self.check("m3_database_recovery", self.m3_snapshot()["hash"] == saved["hash"])
        status, idle = self.request("/v1/response/worker/tick", {"environment_id": "m3-golden"})
        self.check("m3_recovered_scheduler_idle", status == 200 and idle["status"] == "IDLE", idle)
        negatives = json.loads(
            self.compose("exec", "-T", "api", "python", "tools/response_negatives.py", timeout=180).stdout
        )
        for case, result in negatives.items():
            self.check("m3_negative_" + case, result["status"] == "PASS", result)
        self.report["response_golden_chain"] = {
            "label": "SYNTHETIC RESPONSE GOLDEN CHAIN",
            "snapshot": saved,
            "results": results,
            "negative_cases": negatives,
            "real_sensor_runtime": "NOT_RUN",
            "high_risk_executions": 0,
        }
        if benchmark:
            name = self.project + "-response-benchmark"
            runner = "import os,runpy,sys;os.environ['ZHIYU_DATABASE_URL']=os.environ['ZHIYU_TEST_DATABASE_URL'];sys.path.insert(0,'tools');runpy.run_path('tools/response_benchmark.py',run_name='__main__')"
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
                "/tmp/response-benchmark.json",
                timeout=1800,
            )
            self.docker(
                "cp", name + ":/tmp/response-benchmark.json", str(self.directory / "response-benchmark.json")
            )
            self.docker("rm", name)
            measured = json.loads((self.directory / "response-benchmark.json").read_text())
            self.check(
                "m3_benchmark_measured",
                [r["tasks_executed"] for r in measured["results"]] == [100, 1000],
                {
                    "code_version": measured["code_version"],
                    "results": [
                        {k: v for k, v in r.items() if k != "raw_samples_ms"} for r in measured["results"]
                    ],
                },
            )
            self.report["response_benchmark"] = {
                "artifact": "response-benchmark.json",
                "source_digest": measured["source_digest"],
            }
        self.save()


if __name__ == "__main__":
    raise SystemExit(main(M3Acceptance))
