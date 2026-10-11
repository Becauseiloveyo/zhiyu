"""Resumable host harness for real process/database faults, isolated from sensor DB."""

import argparse
import json
import os
import shutil
import time
import traceback
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import yaml
from m5_runtime_acceptance import M5Acceptance
from runtime_acceptance import ROOT

STATE = ROOT.parent / ".work/m6-reliability-state.json"


class Reliability(M5Acceptance):
    def __init__(self):
        if STATE.exists():
            saved = json.loads(STATE.read_text(encoding="utf-8"))
            self.project, self.token, self.password = saved["project"], saved["token"], saved["password"]
            self.directory, self.control = Path(saved["directory"]), Path(saved["control"])
            self.env = {**os.environ, **saved["env"]}
            self.model_key = Path(self.env["ZHIYU_MODEL_KEY_FILE"]).read_text().strip()
            self.report = json.loads((self.directory / "result.json").read_text())
            if self.report["status"] == "FAIL":
                (
                    self.directory
                    / ("failed-attempt-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + ".json")
                ).write_text(json.dumps(self.report, indent=2), encoding="utf-8")
                self.report["status"] = "IN_PROGRESS"
            self.base = saved.get("base", "")
            self.target_ip, self.source_ip = saved.get("target_ip"), saved.get("source_ip")
            self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            return
        prerequisite = json.loads((ROOT / "docs/m6-runtime/gate-a-acceptance.json").read_text())
        assert prerequisite["status"] == "PASS"
        super().__init__(ROOT / "docs/m6-runtime")
        self.control = ROOT.parent / ".work" / (self.project + "-fault-control")
        self.control.mkdir(exist_ok=False)
        cases = [
            "api-ingest",
            "api-plan",
            "api-verification",
            "api-model",
            "db",
            "model-down",
            "model-restarted",
            "model-timeout",
            "model-malformed",
            "model-partial",
            "model-http",
            "model-refusal",
            "network-reset",
            "network-dns",
            "network-isolation",
        ]
        cases += [
            f"worker-{kind}-{stage}"
            for kind in ["event", "task", "action", "verification", "ai"]
            for stage in ["lease", "before", "after", "commit", "stale"]
        ]
        environments = ["m3-m6-" + case for case in cases]
        tokens = json.loads(self.env["ZHIYU_SERVICE_TOKENS"])
        for principal in tokens.values():
            principal["environment_ids"] += environments
        self.env["ZHIYU_SERVICE_TOKENS"] = json.dumps(tokens)
        providers = json.loads(self.env["ZHIYU_AI_PROVIDERS"])
        providers["m6-scripted"] = {
            "provider": "m6-scripted",
            "location": "LOCAL",
            "endpoint": "http://model-fault-fixture:8080/v1",
            "model": "SCRIPTED_VALID",
            "revision": "CONTROLLED_FAULT_NOT_AI",
            "timeout_seconds": 2,
        }
        policies = json.loads(self.env["ZHIYU_AI_POLICIES"])
        policies.update(
            {env: {"enabled": True, "mode": "SHADOW", "provider_id": "m6-scripted"} for env in environments}
        )
        for suffix in ["model-down", "model-restarted"]:
            policies["m3-m6-" + suffix]["provider_id"] = "local"
        self.env.update(ZHIYU_AI_POLICIES=json.dumps(policies), ZHIYU_AI_PROVIDERS=json.dumps(providers))
        services = {}
        for service in [
            "api",
            "tests",
            "migrate",
            "bootstrap",
            "response-target",
            "verification-target",
            "model-fault-fixture",
        ]:
            services[service] = {
                "image": "zhiyu-smoke-a6edef3fbf39-tests:latest",
                "working_dir": "/workspace",
                "environment": {"PYTHONPATH": "/workspace/src:/workspace/tools"},
                "volumes": [{"type": "bind", "source": str(ROOT), "target": "/workspace", "read_only": True}],
            }
        services["api"]["command"] = ["python", "tools/m6_fault_api.py"]
        services["api"]["networks"] = ["control", "ingress"]
        services["api"]["environment"]["ZHIYU_M6_FAULT_LAB"] = "1"
        services["api"]["volumes"].append(
            {"type": "bind", "source": str(self.control), "target": "/fault-control"}
        )
        overlay = {"services": services, "networks": {"control": {"internal": True}, "ingress": {}}}
        (self.directory / "compose.override.yml").write_text(yaml.safe_dump(overlay), encoding="utf-8")
        self.report.update(
            gate="B",
            status="IN_PROGRESS",
            real_sensor_runtime="PASS_CONTROLLED_LAB_SEPARATE_GATE_A",
            remaining=["process/database", "workers", "models/network/storage", "fault-matrix-review"],
        )
        self.save()
        self.persist()

    def persist(self):
        keys = {
            key: value
            for key, value in self.env.items()
            if key.startswith("ZHIYU_") or key in {"POSTGRES_PASSWORD", "COMPOSE_ANSI", "BUILDKIT_PROGRESS"}
        }
        STATE.write_text(
            json.dumps(
                {
                    "project": self.project,
                    "directory": str(self.directory),
                    "control": str(self.control),
                    "token": self.token,
                    "password": self.password,
                    "env": keys,
                    "base": self.base,
                    "target_ip": getattr(self, "target_ip", None),
                    "source_ip": getattr(self, "source_ip", None),
                }
            ),
            encoding="utf-8",
        )

    def compose(self, *args, **kwargs):
        return self.docker(
            "compose",
            "--project-name",
            self.project,
            "-f",
            str(ROOT / "docker-compose.yml"),
            "-f",
            str(ROOT / "docker-compose.ai.yml"),
            "-f",
            str(self.directory / "compose.override.yml"),
            *args,
            **kwargs,
        )

    def fixture(self, verb, env, *args):
        return json.loads(
            self.compose("exec", "-T", "api", "python", "tools/m6_fault_fixture.py", verb, env, *args).stdout
        )

    def all_tables(self, label):
        value = json.loads(
            self.compose("exec", "-T", "api", "python", "tools/m6_database_snapshot.py").stdout
        )
        (self.directory / (label + ".json")).write_text(json.dumps(value, indent=2), encoding="utf-8")
        return value

    def start(self):
        self.compose(
            "up",
            "-d",
            "--no-build",
            "postgres",
            "migrate",
            "bootstrap",
            "api",
            "response-target",
            "model-fault-fixture",
            "local-model",
            timeout=180,
        )
        self.wait_service("postgres")
        self.wait_service("migrate", job=True)
        self.wait_service("bootstrap", job=True)
        self.locate_api()
        self.await_http("/ready", 200)
        self.model_ready()
        network = self.project + "_control"
        self.target_ip = self.container("response-target")["NetworkSettings"]["Networks"][network][
            "IPAddress"
        ]
        self.source_ip = self.container("api")["NetworkSettings"]["Networks"][network]["IPAddress"]
        self.check(
            "fault_network_is_internal",
            json.loads(self.docker("network", "inspect", network).stdout)[0]["Internal"],
        )
        self.persist()

    def restart_api(self):
        self.compose("start", "api")
        self.locate_api()
        self.await_http("/ready", 200)
        self.persist()

    def crash_request(self, case, path, body, *, sql_prefix="", stage="after_sql"):
        instruction = {"case": case, "stage": stage, "sql_prefix": sql_prefix}
        (self.control / "armed.json").write_text(json.dumps(instruction), encoding="utf-8")
        marker = self.control / (case + ".hit.json")
        if marker.exists():
            raise RuntimeError("refuse to overwrite prior physical fault experiment")
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.request, path, body)
            deadline = time.monotonic() + 35
            while not marker.exists() and time.monotonic() < deadline:
                if pending.done():
                    raise RuntimeError("request ended before barrier: " + str(pending.result()))
                time.sleep(0.1)
            self.check(case + "_barrier_reached", marker.exists(), instruction)
            (self.directory / (case + "-barrier.json")).write_bytes(marker.read_bytes())
            self.compose("kill", "-s", "SIGKILL", "api")
            state = self.container("api")["State"]
            self.check(
                case + "_actual_sigkill",
                state["ExitCode"] == 137 and not state["Running"],
                {"exit_code": state["ExitCode"]},
            )
            try:
                value = pending.result(timeout=15)
            except (OSError, ValueError) as error:
                value = {"connection_failure": type(error).__name__}
            (self.directory / (case + "-interrupted-request.json")).write_text(
                json.dumps(value), encoding="utf-8"
            )
        self.restart_api()

    def plan(self, env, seed):
        return self.call(
            "/v1/incidents/" + seed["incident_id"] + "/plans",
            {"environment_id": env, "scope_id": "scope-lab-web", "expected_version": 2},
        )

    def process_faults(self):
        self.start()
        if self.report["checks"].get("db_sigkill_wal_recovery", {}).get("status") != "PASS":
            before = self.all_tables("db-before")
            self.compose("stop", "postgres")
            self.check("db_down_health_liveness", self.fetch("/health")[0] == 200)
            self.check("db_down_readiness", self.fetch("/ready")[0] == 503)
            self.compose("start", "postgres")
            self.wait_service("postgres")
            self.await_http("/ready", 200)
            self.check("db_stop_recovery_all_committed_tables", self.all_tables("db-after-stop") == before)
            self.compose("kill", "-s", "SIGKILL", "postgres")
            self.check("db_crash_readiness", self.fetch("/ready")[0] == 503)
            self.compose("start", "postgres")
            self.wait_service("postgres")
            self.await_http("/ready", 200)
            self.check("db_sigkill_wal_recovery", self.all_tables("db-after-kill") == before)
        for case, prefix in [("ingest", "INSERT INTO normalized_events"), ("plan", "INSERT INTO plans")]:
            env = "m3-m6-api-" + case
            if (self.directory / (case + "-replayed.json")).exists():
                saved = json.loads((self.directory / (case + "-committed.json")).read_text())
                after = json.loads((self.directory / (case + "-replayed.json")).read_text())
                if case == "ingest":
                    # Receipts and audit are per delivery, not logical event identities.
                    self.check(
                        "ingest_replay_no_duplicate_event",
                        all(
                            saved["tables"][name] == after["tables"][name]
                            for name in ["raw_records", "normalized_events", "outbox"]
                        )
                        and after["tables"]["event_receipts"]["count"]
                        - saved["tables"]["event_receipts"]["count"]
                        == 1,
                        {"per_delivery_receipt_growth": 1, "original_snapshots_retained": True},
                    )
                continue
            seed = self.fixture("empty" if case == "ingest" else "seed", env, self.target_ip, self.source_ip)
            path, body = (
                ("/v1/events/raw-batches", seed["inputs"][0])
                if case == "ingest"
                else (
                    "/v1/incidents/" + seed["incident_id"] + "/plans",
                    {"environment_id": env, "scope_id": "scope-lab-web", "expected_version": 2},
                )
            )
            before = self.all_tables(case + "-before")
            self.crash_request("api-" + case, path, body, sql_prefix=prefix)
            self.check(case + "_crash_transaction_rollback", self.all_tables(case + "-rolled-back") == before)
            status, first = self.request(path, body)
            self.check(case + "_retry_commits", status == (202 if case == "ingest" else 200), first)
            saved = self.all_tables(case + "-committed")
            status, again = self.request(path, body)
            after = self.all_tables(case + "-replayed")
            if case == "ingest":
                self.check(
                    "ingest_replay_no_duplicate_event",
                    again["accepted"] == again["errors"] == 0
                    and again["duplicates"] == first["accepted"]
                    and all(
                        saved["tables"][name] == after["tables"][name]
                        for name in ["raw_records", "normalized_events", "outbox"]
                    ),
                )
            else:
                self.check("plan_replay_no_duplicate_objects", first == again and saved == after)
        env = "m3-m6-api-verification"
        seed = self.fixture("seed", env, self.target_ip, self.source_ip)
        self.plan(env, seed)
        for _ in range(3):
            receipt = self.call("/v1/response/worker/tick", {"environment_id": env})
            assert receipt["result"]["execution_outcome"] == "EXECUTION_SUCCESS"
        spec = self.fixture("spec", env)
        identifier = self.call("/v1/verifications", spec)["verification_spec_id"]
        before = self.all_tables("verification-before")
        path, body = "/v1/verifications/" + identifier + "/tick", {"environment_id": env}
        self.crash_request("api-verification", path, body, sql_prefix="INSERT INTO evidence")
        after = self.all_tables("verification-rolled-back")
        self.check(
            "verification_no_half_evidence_observation",
            all(
                before["tables"][name] == after["tables"][name]
                for name in ["evidence", "verification_observations", "verification_results"]
            ),
        )
        time.sleep(11)  # Actual PostgreSQL lease expiry, no artificial clock argument.
        for _ in range(3):
            self.call(path, body)
        result = self.call("/v1/verifications/" + identifier + "/decide", body)
        self.check("verification_crash_recovery", result["status"] == "PASS", result)
        self.check(
            "verification_decision_replay",
            result == self.call("/v1/verifications/" + identifier + "/decide", body),
        )
        env = "m3-m6-api-model"
        seed = self.fixture("seed", env, self.target_ip, self.source_ip)
        context = self.call(
            "/v1/incidents/" + seed["incident_id"] + "/contexts",
            {"environment_id": env, "scope_id": "scope-lab-web"},
        )
        path, body = "/v1/contexts/" + context["context_id"] + "/ai-decision", {"environment_id": env}
        self.crash_request("api-model", path, body, stage="model_response")
        snapshot = self.fixture("snapshot", env)
        self.check(
            "model_response_crash_no_accepted_result",
            snapshot["counts"]["model_runs"] == 0 and snapshot["counts"]["plans"] == 0,
        )
        time.sleep(18)
        result = self.call(path, body)
        self.check("model_interrupted_fallback", result["status"] == "DETERMINISTIC_FALLBACK", result)
        self.check("model_fallback_replay", self.call(path, body) == result)
        final = self.all_tables("process-faults-final")
        self.check(
            "process_faults_audit_and_no_high_risk",
            all(final["audit_chains"].values()) and final["high_risk_automatic_actions"] == 0,
        )
        self.report["remaining"].remove("process/database")
        self.save()

    def workers(self):
        assert "process/database" not in self.report["remaining"]
        for kind in ["event", "task", "action", "verification", "ai"]:
            if self.report["checks"].get("worker_" + kind, {}).get("status") == "PASS":
                continue
            try:
                self.compose(
                    "exec",
                    "-T",
                    "api",
                    "python",
                    "tools/m6_worker_matrix.py",
                    kind,
                    self.target_ip,
                    self.source_ip,
                    timeout=240,
                )
            finally:
                source = self.control / ("worker-" + kind)
                if source.exists():
                    shutil.copytree(source, self.directory / ("worker-" + kind), dirs_exist_ok=True)
            result = json.loads((self.directory / ("worker-" + kind) / "result.json").read_text())
            self.check("worker_" + kind, result["status"] == "PASS" and len(result["cases"]) == 5, result)
        if "workers" in self.report["remaining"]:
            self.report["remaining"].remove("workers")
        self.save()

    def failure_routes(self):
        assert "workers" not in self.report["remaining"]
        providers = json.loads(self.env["ZHIYU_AI_PROVIDERS"])
        policies = json.loads(self.env["ZHIYU_AI_POLICIES"])
        names = {
            "model-timeout": "TIMEOUT",
            "model-malformed": "MALFORMED",
            "model-partial": "PARTIAL",
            "model-http": "HTTP",
            "model-refusal": "REFUSAL",
            "network-reset": "RESET",
            "network-latency": "LATENCY",
            "network-dns": "DNS",
            "network-isolation": "ISOLATION",
        }
        for suffix, mode in names.items():
            provider_id = "m6-" + suffix
            providers[provider_id] = {
                **providers["m6-scripted"],
                "provider": provider_id,
                "model": "M6_" + mode,
            }
            if suffix == "network-dns":
                providers[provider_id]["endpoint"] = "http://m6-does-not-exist.invalid:8080/v1"
            policies["m3-m6-" + suffix] = {"enabled": True, "mode": "SHADOW", "provider_id": provider_id}
        providers["m6-local-short"] = {
            **providers["local"],
            "provider": "m6-local-short",
            "timeout_seconds": 2,
        }
        for suffix in ["model-down", "model-startup-slow"]:
            policies["m3-m6-" + suffix] = {"enabled": True, "mode": "SHADOW", "provider_id": "m6-local-short"}
        tokens = json.loads(self.env["ZHIYU_SERVICE_TOKENS"])
        extra = ["m3-m6-network-latency", "m3-m6-model-startup-slow", "m3-m6-storage", "m3-m6-sensor-faults"]
        for principal in tokens.values():
            principal["environment_ids"] = sorted(set(principal["environment_ids"] + extra))
        self.env.update(
            ZHIYU_AI_PROVIDERS=json.dumps(providers),
            ZHIYU_AI_POLICIES=json.dumps(policies),
            ZHIYU_SERVICE_TOKENS=json.dumps(tokens),
        )
        path = self.directory / "compose.override.yml"
        overlay = yaml.safe_load(path.read_text())
        overlay["services"]["model-fault-fixture"]["command"] = ["python", "tools/m6_http_faults.py"]
        path.write_text(yaml.safe_dump(overlay), encoding="utf-8")
        self.persist()
        self.compose("up", "-d", "--no-build", "api", "model-fault-fixture", timeout=120)
        self.locate_api()
        self.await_http("/ready", 200)
        network = self.project + "_control"
        self.source_ip = self.container("api")["NetworkSettings"]["Networks"][network]["IPAddress"]
        self.persist()

    def fault_context(self, suffix):
        env = "m3-m6-" + suffix
        seed = self.fixture("seed", env, self.target_ip, self.source_ip)
        context = self.call(
            "/v1/incidents/" + seed["incident_id"] + "/contexts",
            {"environment_id": env, "scope_id": "scope-lab-web"},
        )
        return env, context

    def fallback(self, suffix, expected):
        env, context = self.fault_context(suffix)
        receipt = self.call("/v1/contexts/" + context["context_id"] + "/ai-decision", {"environment_id": env})
        snapshot = self.fixture("snapshot", env)
        errors = [row["error_code"] for row in snapshot["rows"]["model_receipts"]]
        self.check(
            suffix + "_safe_fallback",
            receipt["status"] == "DETERMINISTIC_FALLBACK"
            and bool(errors)
            and all(code in expected for code in errors)
            and snapshot["counts"]["action_requests"] == 0
            and snapshot["counts"]["plans"] == 1
            and snapshot["audit_valid"],
            {"receipt": receipt, "provider_error_codes": errors},
        )
        (self.directory / (suffix + "-snapshot.json")).write_text(
            json.dumps(snapshot, indent=2), encoding="utf-8"
        )

    def transports_storage(self):
        self.failure_routes()
        cases = {
            "model-timeout": {"TIMEOUT"},
            "model-malformed": {"INVALID_JSON_OR_ENVELOPE"},
            "model-partial": {"INCOMPLETE_RESPONSE"},
            "model-http": {"HTTP_FAILURE"},
            "model-refusal": {"MODEL_REFUSAL"},
            "network-reset": {"CONNECTION_FAILURE"},
            "network-dns": {"CONNECTION_FAILURE", "TIMEOUT"},
        }
        for suffix, expected in cases.items():
            if self.report["checks"].get(suffix + "_safe_fallback", {}).get("status") != "PASS":
                self.fallback(suffix, expected)
        if self.report["checks"].get("network-latency_bounded", {}).get("status") != "PASS":
            env, context = self.fault_context("network-latency")
            value = self.call(
                "/v1/contexts/" + context["context_id"] + "/ai-analysis", {"environment_id": env}
            )
            snapshot = self.fixture("snapshot", env)
            self.check(
                "network-latency_bounded",
                snapshot["rows"]["model_receipts"][0]["provider_ms"] >= 450
                and snapshot["rows"]["model_receipts"][0]["status"] == "COMPLETED",
                {"analysis": value, "receipts": snapshot["rows"]["model_receipts"]},
            )
        if self.report["checks"].get("network-isolation_safe_fallback", {}).get("status") != "PASS":
            cid = self.container("model-fault-fixture")["Id"]
            network = self.project + "_control"
            self.docker("network", "disconnect", network, cid)
            try:
                self.fallback("network-isolation", {"CONNECTION_FAILURE", "TIMEOUT"})
            finally:
                self.docker("network", "connect", "--alias", "model-fault-fixture", network, cid)
        if self.report["checks"].get("model-down_safe_fallback", {}).get("status") != "PASS":
            self.compose("stop", "local-model")
            try:
                self.fallback("model-down", {"CONNECTION_FAILURE"})
            finally:
                self.compose("start", "local-model")
                self.model_ready()
        if self.report["checks"].get("model-startup-slow_safe_fallback", {}).get("status") != "PASS":
            # An actual paused model process supplies no health/response; bounded gateway deadline applies.
            self.compose("pause", "local-model")
            try:
                self.fallback("model-startup-slow", {"TIMEOUT"})
            finally:
                self.compose("unpause", "local-model")
                self.model_ready()
        if self.report["checks"].get("real_model_restart_response", {}).get("status") != "PASS":
            self.compose("restart", "local-model")
            self.model_ready()
            env, context = self.fault_context("model-restarted")
            value = self.call(
                "/v1/contexts/" + context["context_id"] + "/ai-analysis", {"environment_id": env}
            )
            snapshot = self.fixture("snapshot", env)
            runs = snapshot["rows"]["model_runs"]
            self.check(
                "real_model_restart_response",
                len(runs) == 1
                and runs[0]["provider"] == "local"
                and runs[0]["input_tokens"] > 0
                and snapshot["counts"]["action_requests"] == 0,
                {"analysis_status": value["status"], "model_runs": runs},
            )
            (self.directory / "model-restarted-snapshot.json").write_text(
                json.dumps(snapshot, indent=2), encoding="utf-8"
            )
        for name, script in [("storage", "m6_storage_faults.py"), ("outbox", "m6_outbox_faults.py")]:
            if self.report["checks"].get(name + "_recovery", {}).get("status") == "PASS":
                continue
            try:
                self.compose(
                    "exec",
                    "-T",
                    "api",
                    "python",
                    "tools/" + script,
                    *([self.target_ip, self.source_ip] if name == "storage" else []),
                )
            finally:
                if (self.control / name).exists():
                    shutil.copytree(self.control / name, self.directory / name, dirs_exist_ok=True)
            result = json.loads((self.directory / name / "result.json").read_text())
            self.check(name + "_recovery", result["status"] == "PASS", result)
        code = """import errno,json,logging
from pathlib import Path
result={}
for name,call in [('artifact_directory_unavailable',lambda:Path('/tmp/m6-artifact').write_text('lab')),('log_destination_unavailable',lambda:logging.FileHandler('/tmp/m6-log')),('bounded_volume_full',lambda:Path('/fault/bounded').write_bytes(b'x'*32768))]:
 try: call()
 except OSError as e: result[name]={'errno':e.errno,'status':'PASS' if e.errno in (errno.EROFS,errno.ENOSPC) else 'FAIL'}
 else: result[name]={'status':'FAIL'}
assert all(x['status']=='PASS' for x in result.values()),result
print(json.dumps({'scope':'FILESYSTEM_HARNESS_NOT_PRODUCT_EVIDENCE_STORE','host_disk_filled':False,'volume_limit_bytes':8192,'checks':result}))
"""
        fs = json.loads(
            self.docker(
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--tmpfs",
                "/fault:rw,size=8192,uid=10001,gid=10001",
                "zhiyu-smoke-a6edef3fbf39-tests:latest",
                "python",
                "-c",
                code,
            ).stdout
        )
        self.check(
            "bounded_filesystem_failures", all(row["status"] == "PASS" for row in fs["checks"].values()), fs
        )
        self.compose("logs", "--no-color", "model-fault-fixture")
        self.report["remaining"].remove("models/network/storage")
        self.save()

    def review_faults(self):
        assert self.report["remaining"] == ["fault-matrix-review"]
        if self.report["checks"].get("sensor_clock_reorder_dedup", {}).get("status") != "PASS":
            try:
                self.compose(
                    "exec", "-T", "api", "python", "tools/m6_sensor_faults.py", self.target_ip, self.source_ip
                )
            finally:
                if (self.control / "sensor-faults").exists():
                    shutil.copytree(
                        self.control / "sensor-faults", self.directory / "sensor-faults", dirs_exist_ok=True
                    )
            result = json.loads((self.directory / "sensor-faults/result.json").read_text())
            self.check("sensor_clock_reorder_dedup", result["status"] == "PASS", result)
        if (
            self.report["checks"].get("model_down_deterministic_execution_verification", {}).get("status")
            != "PASS"
        ):
            env = "m3-m6-model-down"
            self.fixture("refresh", env)
            self.compose("stop", "local-model")
            try:
                results = []
                for _ in range(3):
                    results.append(self.call("/v1/response/worker/tick", {"environment_id": env}))
                assert all(row["result"]["execution_outcome"] == "EXECUTION_SUCCESS" for row in results)
                body = self.fixture("spec", env)
                identifier = self.call("/v1/verifications", body)["verification_spec_id"]
                for _ in range(3):
                    self.call("/v1/verifications/" + identifier + "/tick", {"environment_id": env})
                verdict = self.call("/v1/verifications/" + identifier + "/decide", {"environment_id": env})
                self.check(
                    "model_down_deterministic_execution_verification",
                    verdict["status"] == "PASS",
                    {
                        "executions": results,
                        "verification": verdict,
                        "sensor_observations": "SYNTHETIC_FIXTURE",
                        "business_probe": "ACTUAL_HTTP_HEAD",
                    },
                )
            finally:
                self.compose("start", "local-model")
                self.model_ready()
        if self.report["checks"].get("db_down_workers_fail_closed", {}).get("status") != "PASS":
            before = self.all_tables("worker-db-fault-before")
            self.compose("stop", "postgres")
            try:
                cases = {
                    kind: {
                        "environment": "m3-m6-worker-" + kind + "-commit",
                        "worker": kind,
                        "stage": "stale",
                    }
                    for kind in ["event", "task", "action", "verification", "ai"]
                }
                for kind in ["verification", "ai"]:
                    cases[kind] = json.loads(
                        (self.directory / ("worker-" + kind) / "commit/task.json").read_text()
                    )
                    cases[kind]["stage"] = "stale"
                outputs = {}
                for kind, task in cases.items():
                    row = self.compose(
                        "exec",
                        "-T",
                        "api",
                        "python",
                        "tools/m6_worker_process.py",
                        json.dumps(task),
                        expected=None,
                    )
                    assert row.returncode != 0 and "OperationalError" in row.stderr
                    outputs[kind] = {
                        "exit_code": row.returncode,
                        "database_error": "OperationalError",
                        "result_committed": False,
                    }
                self.check(
                    "db_down_workers_fail_closed",
                    len(outputs) == 5 and self.fetch("/health")[0] == 200 and self.fetch("/ready")[0] == 503,
                    outputs,
                )
                observed = self.compose(
                    "exec",
                    "-T",
                    "api",
                    "python",
                    "-c",
                    "import urllib.request; print(urllib.request.urlopen(urllib.request.Request('http://response-target:8081/health',method='HEAD'),timeout=3).status)",
                )
                self.check("db_outage_underlying_business_survives", observed.stdout.strip() == "200")
            finally:
                self.compose("start", "postgres")
                self.wait_service("postgres")
                self.await_http("/ready", 200)
            self.check(
                "worker_db_fault_no_committed_change", self.all_tables("worker-db-fault-after") == before
            )
        final = self.all_tables("gate-b-final")
        self.check(
            "gate_b_final_audit_integrity",
            all(final["audit_chains"].values()) and final["high_risk_automatic_actions"] == 0,
        )
        assert all(check["status"] == "PASS" for check in self.report["checks"].values())
        self.report["remaining"] = []
        self.report["status"] = "PASS"
        self.report["finished_at"] = datetime.now(UTC).isoformat()
        self.report["scope"] = "CONTROLLED_LAB_CURRENT_READ_ONLY_EXECUTORS"
        self.report["limitations"] = [
            "Fault cases use SYNTHETIC fixtures; real sensors are separately proven by Gate A",
            "Slow startup represented by a physically paused model process; actual loading readiness verified separately",
            "Artifact/log failure is a filesystem harness; product Evidence storage error uses a scoped PostgreSQL trigger",
            "Event Intelligence uses transaction row locking, not expiring WorkerLease",
            "No production, state-changing executor, cloud, Windows or OT claim",
        ]
        self.save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["process", "start", "workers", "transports", "review"])
    args = parser.parse_args()
    run = Reliability()
    try:
        {
            "process": run.process_faults,
            "start": run.start,
            "workers": run.workers,
            "transports": run.transports_storage,
            "review": run.review_faults,
        }[args.phase]()
    except Exception:
        run.report["status"] = "FAIL"
        (run.directory / ("failure-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + ".txt")).write_text(
            run.sanitize(traceback.format_exc()), encoding="utf-8"
        )
        run.save()
        raise
    print(
        json.dumps(
            {
                "status": run.report["status"],
                "report": str(run.directory / "result.json"),
                "remaining": run.report["remaining"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
