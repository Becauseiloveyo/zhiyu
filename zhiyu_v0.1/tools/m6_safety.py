"""Gate C host coordinator; preserves Gate B's completed report and evidence."""

import argparse
import json
import os
import traceback
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml
from m6_reliability import Reliability
from runtime_acceptance import ROOT

STATE = ROOT.parent / ".work/m6-safety-state.json"


class Safety(Reliability):
    def __init__(self):
        path = STATE if STATE.exists() else ROOT.parent / ".work/m6-reliability-state.json"
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.project, self.token, self.password = saved["project"], saved["token"], saved["password"]
        self.env = {**os.environ, **saved["env"]}
        self.model_key = Path(self.env["ZHIYU_MODEL_KEY_FILE"]).read_text().strip()
        self.base = saved.get("base", "")
        self.target_ip, self.source_ip = saved.get("target_ip"), saved.get("source_ip")
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        if STATE.exists():
            self.directory = Path(saved["directory"])
            self.report = json.loads((self.directory / "result.json").read_text())
            if self.report["status"] == "FAIL":
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
                (self.directory / ("failed-attempt-" + stamp + ".json")).write_text(
                    json.dumps(self.report, indent=2), encoding="utf-8"
                )
                self.report["status"] = "IN_PROGRESS"
            return
        prior = Path(saved["directory"])
        prerequisite = json.loads((prior / "result.json").read_text())
        assert prerequisite["gate"] == "B" and prerequisite["status"] == "PASS"
        self.directory = ROOT / "docs/m6-runtime/gate-c-001"
        self.directory.mkdir(exist_ok=False)
        environments = [f"m3-m6-eval-e{i:02d}" for i in range(1, 81)]
        environments += ["m3-m6-lab-a", "m3-m6-lab-b", "m3-m6-c-override", "m3-m6-c-canary"]
        tokens = json.loads(self.env["ZHIYU_SERVICE_TOKENS"])
        for principal in tokens.values():
            principal["environment_ids"] += environments
        self.env["ZHIYU_SERVICE_TOKENS"] = json.dumps(tokens)
        policies = json.loads(self.env["ZHIYU_AI_POLICIES"])
        policies.update(
            {env: {"enabled": True, "mode": "SHADOW", "provider_id": "local"} for env in environments}
        )
        self.env["ZHIYU_AI_POLICIES"] = json.dumps(policies)
        overlay = yaml.safe_load((prior / "compose.override.yml").read_text())
        api = overlay["services"]["api"]
        api["command"] = ["python", "tools/ai_api.py"]
        api["environment"].pop("ZHIYU_M6_FAULT_LAB", None)
        api["volumes"] = [v for v in api["volumes"] if v["target"] != "/fault-control"]
        api["volumes"].append({"type": "bind", "source": str(self.directory), "target": "/safety-output"})
        (self.directory / "compose.override.yml").write_text(yaml.safe_dump(overlay), encoding="utf-8")
        self.report = {
            "gate": "C",
            "status": "IN_PROGRESS",
            "project": self.project,
            "started_at": datetime.now(UTC).isoformat(),
            "checks": {},
            "commands": [],
            "gate_b_evidence": str(prior.relative_to(ROOT)),
            "model_runtime": prerequisite["model_runtime"],
            "remaining": ["80 real-model cases", "boundary matrix", "semantic review"],
        }
        self.save()
        self.persist()

    def persist(self):
        selected = {
            k: v
            for k, v in self.env.items()
            if k.startswith("ZHIYU_") or k in {"POSTGRES_PASSWORD", "COMPOSE_ANSI", "BUILDKIT_PROGRESS"}
        }
        STATE.write_text(
            json.dumps(
                {
                    "project": self.project,
                    "directory": str(self.directory),
                    "token": self.token,
                    "password": self.password,
                    "env": selected,
                    "base": self.base,
                    "target_ip": self.target_ip,
                    "source_ip": self.source_ip,
                }
            ),
            encoding="utf-8",
        )

    def start(self):
        self.compose("up", "-d", "--no-build", "--no-deps", "api", timeout=180)
        self.locate_api()
        self.await_http("/ready", 200)
        self.model_ready()
        network = self.project + "_control"
        self.target_ip = self.container("response-target")["NetworkSettings"]["Networks"][network][
            "IPAddress"
        ]
        self.source_ip = self.container("api")["NetworkSettings"]["Networks"][network]["IPAddress"]
        self.check(
            "isolated_control_network",
            json.loads(self.docker("network", "inspect", network).stdout)[0]["Internal"],
        )
        self.persist()

    def evaluate(self):
        extra = ["--start", "38", "--run-id", "r002-"] if self.directory.name == "gate-c-002" else []
        self.compose(
            "exec",
            "-T",
            "api",
            "python",
            "tools/m6_ai_evaluation.py",
            self.target_ip,
            self.source_ip,
            *extra,
            timeout=14400,
        )
        result = json.loads((self.directory / "evaluation.json").read_text(encoding="utf-8"))
        self.check(
            "selected_cases_processed",
            result["status"] == "COMPLETED" and result["cases_completed"] == result["target_cases"],
        )
        measured = sum(
            any(r["input_tokens"] and r["output_tokens"] for r in case["model_runs"])
            for case in result["results"]
        )
        self.check(
            "all_selected_cases_have_real_model_response",
            measured == result["target_cases"],
            {"metered": measured, "selected": result["target_cases"]},
        )

    def recover(self):
        assert self.directory.name == "gate-c-001"
        original = json.loads((self.directory / "evaluation.json").read_text(encoding="utf-8"))
        assert original["cases_completed"] == 80
        self.report["status"] = "FAIL"
        self.report["checks"].pop("80_real_model_cases_completed", None)
        self.report["checks"]["all_cases_processed_with_fallbacks"] = {"status": "PASS", "detail": 80}
        self.report["checks"]["minimum_real_responses"] = {
            "status": "FAIL",
            "detail": {"metered_cases": 38, "required": 60},
        }
        self.report["failure"] = (
            "Model container OOMKilled=true; 4 timeouts followed by 38 connection failures. Retained all 80 attempts."
        )
        self.save()
        old = self.directory
        self.directory = ROOT / "docs/m6-runtime/gate-c-002"
        self.directory.mkdir(exist_ok=False)
        overlay = yaml.safe_load((old / "compose.override.yml").read_text())
        for volume in overlay["services"]["api"]["volumes"]:
            if volume["target"] == "/safety-output":
                volume["source"] = str(self.directory)
        (self.directory / "compose.override.yml").write_text(yaml.safe_dump(overlay), encoding="utf-8")
        environments = [f"m3-m6-eval-r002-e{i:02d}" for i in range(38, 81)]
        tokens = json.loads(self.env["ZHIYU_SERVICE_TOKENS"])
        for principal in tokens.values():
            principal["environment_ids"] += environments
        self.env["ZHIYU_SERVICE_TOKENS"] = json.dumps(tokens)
        policies = json.loads(self.env["ZHIYU_AI_POLICIES"])
        policies.update(
            {env: {"enabled": True, "mode": "SHADOW", "provider_id": "local"} for env in environments}
        )
        self.env["ZHIYU_AI_POLICIES"] = json.dumps(policies)
        self.report = {
            "gate": "C",
            "status": "IN_PROGRESS",
            "project": self.project,
            "started_at": datetime.now(UTC).isoformat(),
            "checks": {},
            "commands": [],
            "prior_attempt": str(old.relative_to(ROOT)),
            "model_runtime": self.report["model_runtime"],
            "remaining": ["E38-E80 actual model recovery", "joint Gate C review"],
            "model_cache_mib": 256,
            "reason": "Bound prompt-cache RAM after observed OOM; same weights, model, context, token and timeout limits",
        }
        self.save()
        self.persist()
        self.compose("up", "-d", "--no-build", "--no-deps", "local-model", timeout=180)
        self.start()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["start", "evaluate", "recover"])
    args = parser.parse_args()
    run = Safety()
    try:
        getattr(run, args.phase)()
    except Exception:
        run.report["status"] = "FAIL"
        run.report["error"] = run.sanitize(traceback.format_exc())
        run.save()
        raise


if __name__ == "__main__":
    main()
