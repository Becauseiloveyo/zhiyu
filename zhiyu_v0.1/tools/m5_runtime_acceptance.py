"""All v0.4 checks plus real local model, adversarial outputs and AI-assisted closed loops."""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from m4_runtime_acceptance import M4Acceptance
from runtime_acceptance import ROOT, RuntimeFailure, main

MODEL_SHA = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
REVISION = "91cad51170dc346986eccefdc2dd33a9da36ead9"


class M5Acceptance(M4Acceptance):
    cleanup_profiles = ("response-test", "verification-test", "ai-test")

    def __init__(self, directory):
        super().__init__(directory)
        model = Path(os.environ["ZHIYU_MODEL_PATH"]).resolve()
        key_path = Path(os.environ["ZHIYU_MODEL_KEY_FILE"]).resolve()
        with model.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != MODEL_SHA:
                raise ValueError("model checksum mismatch")
        self.model_key = key_path.read_text().strip()
        if not self.model_key:
            raise ValueError("private model credential required")
        self.env.update(ZHIYU_MODEL_PATH=str(model), ZHIYU_MODEL_KEY_FILE=str(key_path))
        cases = ["valid", "hallucination", "injection", "down", "claims-success", "interrupt", "commit"]
        environments = ["m3-m5-" + c for c in cases] + [f"m3-m5-eval-{i:02d}" for i in range(24)]
        tokens = json.loads(self.env["ZHIYU_SERVICE_TOKENS"])
        for principal in tokens.values():
            principal["environment_ids"] += environments
            principal["permissions"] += ["ai:context", "ai:read", "ai:analyze", "ai:plan"]
        self.env["ZHIYU_SERVICE_TOKENS"] = json.dumps(tokens)
        providers = {
            "local": {
                "provider": "local",
                "location": "LOCAL",
                "endpoint": "http://local-model:8080/v1",
                "model": "zhiyu-qwen2.5-1.5b",
                "revision": REVISION,
                "timeout_seconds": 110,
                "max_output_tokens": 1200,
                "structured_format": "JSON_OBJECT_SCHEMA",
                "api_key_env": "ZHIYU_LOCAL_MODEL_KEY",
            }
        }
        for case, name in [
            ("hallucination", "SCRIPTED_HALLUCINATION"),
            ("injection", "SCRIPTED_INJECTION"),
            ("claims-success", "SCRIPTED_CLAIMS_SUCCESS"),
            ("commit", "SCRIPTED_VALID"),
        ]:
            providers[case] = {
                "provider": case,
                "location": "LOCAL",
                "endpoint": "http://model-fault-fixture:8080/v1",
                "model": name,
                "revision": "CONTROLLED_FAULT_NOT_AI",
                "timeout_seconds": 3,
            }
        policies = {
            env: {
                "enabled": True,
                "mode": "ASSISTED",
                "provider_id": env.removeprefix("m3-m5-")
                if env.removeprefix("m3-m5-") in providers
                else "local",
            }
            for env in environments
        }
        for env in environments:
            if "eval-" in env:
                policies[env]["mode"] = "SHADOW"
        self.env.update(ZHIYU_AI_POLICIES=json.dumps(policies), ZHIYU_AI_PROVIDERS=json.dumps(providers))
        self.report["model_runtime"] = {
            "provider": "local",
            "model": providers["local"]["model"],
            "revision": REVISION,
            "weights_sha256": MODEL_SHA,
            "location": "LOCAL",
            "cloud_calls": 0,
            "cost_usd": None,
        }

    def sanitize(self, value):
        return super().sanitize(value).replace(getattr(self, "model_key", "\x00"), "<redacted>")

    def compose(self, *args, **kwargs):
        return self.docker(
            "compose",
            "--project-name",
            self.project,
            "-f",
            str(ROOT / "docker-compose.yml"),
            "-f",
            str(ROOT / "docker-compose.ai.yml"),
            *args,
            **kwargs,
        )

    def request(self, path, body=None):
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.token},
        )
        try:
            with self.http.open(request, timeout=260) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def ai_fixture(self, verb, env, *args):
        return json.loads(
            self.compose("exec", "-T", "api", "python", "tools/ai_fixture.py", verb, env, *args).stdout
        )

    def model_ready(self):
        until = time.monotonic() + 100
        while time.monotonic() < until:
            r = self.compose(
                "exec",
                "-T",
                "api",
                "python",
                "tools/ai_fixture.py",
                "model-health",
                "m3-m5-valid",
                expected=None,
            )
            if r.returncode == 0:
                return
            time.sleep(2)
        raise RuntimeFailure("local model failed readiness")

    def valid_decision_expected(self, decision):
        return "AI_ASSISTED"

    def seed(self, env):
        fixture = self.ai_fixture("seed", env, self.target_ip, self.source_ip)
        return self.call(
            "/v1/incidents/" + fixture["incident_id"] + "/contexts",
            {"environment_id": env, "scope_id": "scope-lab-web"},
        )

    def execute_verify(self, env, decision, expected="PASS"):
        body = {"environment_id": env}
        self.ai_fixture("refresh", env)
        plan = self.request("/v1/plans/" + decision["plan_id"])[1]["plan"]
        actions = [self.call("/v1/response/worker/tick", body) for _ in plan["tasks"]]
        self.check(
            env + "_fresh_authorization_execution",
            all(
                a["policy_outcome"] == "ALLOW" and a["result"]["execution_outcome"] == "EXECUTION_SUCCESS"
                for a in actions
            ),
        )
        time.sleep(1.1)
        specification = self.ai_fixture("spec", env, "fail" if expected == "FAIL" else "pass")
        spec_id = self.call("/v1/verifications", specification)["verification_spec_id"]
        for _ in range(3):
            self.call("/v1/verifications/" + spec_id + "/tick", body)
        result = self.call("/v1/verifications/" + spec_id + "/decide", body)
        self.check(env + "_independent_verification", result["status"] == expected, result)
        replan = self.call("/v1/verification-results/" + result["verification_id"] + "/apply", body)
        self.check(
            env + "_bounded_replan",
            replan["status"] == ("CREATED" if expected == "FAIL" else "NO_REPLAN"),
            replan,
        )
        return result, replan

    def run(self, *, no_cache):
        super().run(no_cache=no_cache)
        self.compose(
            "--profile", "ai-test", "up", "-d", "--build", "local-model", "model-fault-fixture", timeout=240
        )
        self.model_ready()
        model = self.container("local-model")
        self.check(
            "m5_model_isolated",
            not model["HostConfig"]["PortBindings"]
            and model["HostConfig"]["ReadonlyRootfs"]
            and model["Config"]["User"] == "10001:10001"
            and "--no-agent" in model["Config"]["Cmd"],
        )
        network = self.project + "_control"
        self.target_ip = self.container("response-target")["NetworkSettings"]["Networks"][network][
            "IPAddress"
        ]
        self.source_ip = self.container("api")["NetworkSettings"]["Networks"][network]["IPAddress"]
        interrupted = self.seed("m3-m5-interrupt")
        self.compose(
            "exec",
            "-T",
            "api",
            "python",
            "tools/ai_fault_worker.py",
            "interrupt",
            "m3-m5-interrupt",
            interrupted["context_id"],
            expected=31,
        )
        interrupted_at = time.monotonic()
        self.report["ai_chains"] = {}
        for case in ["valid", "hallucination", "injection", "down", "claims-success"]:
            env = "m3-m5-" + case
            context = self.seed(env)
            body = {"environment_id": env}
            if case == "down":
                self.compose("stop", "local-model")
            if case == "valid":
                with ThreadPoolExecutor(max_workers=2) as pool:
                    parallel = list(
                        pool.map(
                            lambda _: self.call(
                                "/v1/contexts/" + context["context_id"] + "/ai-decision", body
                            ),
                            range(2),
                        )
                    )
                decision = next((r for r in parallel if r["status"] != "IN_PROGRESS"), parallel[0])
                self.report["ai_concurrent_receipts"] = parallel
            else:
                decision = self.call("/v1/contexts/" + context["context_id"] + "/ai-decision", body)
            expected = (
                "REJECTED"
                if case in {"hallucination", "injection"}
                else "DETERMINISTIC_FALLBACK"
                if case == "down"
                else self.valid_decision_expected(decision)
                if case == "valid"
                else "AI_ASSISTED"
            )
            self.check("m5_" + case + "_decision", decision["status"] == expected, decision)
            if case == "down":
                self.compose("start", "local-model")
                self.model_ready()
            if decision["plan_id"]:
                self.execute_verify(env, decision, "FAIL" if case == "claims-success" else "PASS")
            snapshot = self.ai_fixture("snapshot", env)
            self.check(
                "m5_" + case + "_lineage_and_risk",
                snapshot["high_risk_executions"] == 0
                and snapshot["audit_valid"]
                and snapshot["counts"]["incidents"] == 1
                and (
                    snapshot["counts"]["action_requests"] == 0
                    if expected == "REJECTED"
                    else snapshot["counts"]["action_execution_results"] >= 1
                ),
            )
            if case == "valid":
                self.check(
                    "m5_real_model_calls_and_one_plan",
                    snapshot["counts"]["model_runs"] == 2
                    and snapshot["counts"]["plans"] == 1
                    and all(
                        r["provider"] == "local" and r["input_tokens"] > 0
                        for r in snapshot["rows"]["model_runs"]
                    ),
                )
            if case == "claims-success":
                self.check(
                    "m5_verification_overrides_model_success",
                    snapshot["rows"]["verification_results"][0]["status"] == "FAIL"
                    and "Remediation succeeded" in json.dumps(snapshot["rows"]["ai_situation_analyses"]),
                )
            self.check(
                "m5_" + case + "_decision_replay",
                self.call("/v1/contexts/" + context["context_id"] + "/ai-decision", body) == decision,
            )
            self.report["ai_chains"][case] = {
                "decision": decision,
                "snapshot": snapshot,
                "metrics": self.request("/v1/ai-metrics?environment_id=" + env)[1],
                "provider_kind": "REAL_LOCAL_MODEL"
                if case in {"valid", "down"}
                else "SCRIPTED_ADVERSARIAL_NOT_AI",
            }
            self.save()
        # A worker dies after a durable terminal ModelRun; replay must not resample it.
        commit = self.seed("m3-m5-commit")
        self.compose(
            "exec",
            "-T",
            "api",
            "python",
            "tools/ai_fault_worker.py",
            "after-commit",
            "m3-m5-commit",
            commit["context_id"],
            expected=32,
        )
        self.compose("restart", "api")
        self.locate_api()
        self.await_http("/ready", 200)
        committed = self.call(
            "/v1/contexts/" + commit["context_id"] + "/ai-decision", {"environment_id": "m3-m5-commit"}
        )
        self.check(
            "m5_postcommit_crash_recovery",
            committed["status"] == "AI_ASSISTED"
            and self.ai_fixture("snapshot", "m3-m5-commit")["counts"]["model_runs"] == 2,
        )
        self.compose("stop", "postgres")
        self.check("m5_db_outage_observable", self.fetch("/ready")[0] == 503)
        self.compose("start", "postgres")
        self.wait_service("postgres")
        self.await_http("/ready", 200)
        self.compose("restart", "local-model")
        self.model_ready()
        saved = self.report["ai_chains"]["valid"]["decision"]
        self.check(
            "m5_api_db_model_restart_persistence",
            self.call(
                "/v1/contexts/" + saved["context_id"] + "/ai-decision", {"environment_id": "m3-m5-valid"}
            )
            == saved,
        )
        while time.monotonic() - interrupted_at < 127:
            time.sleep(1)
        recovery = self.call(
            "/v1/contexts/" + interrupted["context_id"] + "/ai-decision",
            {"environment_id": "m3-m5-interrupt"},
        )
        interrupted_snapshot = self.ai_fixture("snapshot", "m3-m5-interrupt")
        self.check(
            "m5_interrupted_model_call_fallback",
            recovery["status"] == "DETERMINISTIC_FALLBACK"
            and interrupted_snapshot["rows"]["model_receipts"][0]["error_code"] == "INTERRUPTED_CALL"
            and interrupted_snapshot["counts"]["model_runs"] == 1,
        )
        self.report["ai_recovery"] = {
            "interrupted": interrupted_snapshot,
            "postcommit": self.ai_fixture("snapshot", "m3-m5-commit"),
        }
        from ai_evaluation import run_evaluation

        run_evaluation(self)
        self.save()


if __name__ == "__main__":
    raise SystemExit(main(M5Acceptance))
