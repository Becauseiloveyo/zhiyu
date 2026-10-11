"""Gate D coordinator; previous Gate evidence is immutable and never rewritten."""

import argparse
import hashlib
import json
import os
import subprocess
import threading
import traceback
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml
from m6_safety import Safety
from runtime_acceptance import ROOT

STATE = ROOT.parent / ".work/m6-load-state.json"


class Load(Safety):
    def __init__(self):
        prerequisite = json.loads((ROOT / "docs/m6-runtime/gate-c-acceptance.json").read_text())
        assert prerequisite["status"] == "PASS_CONTROLLED_LAB"
        source = STATE if STATE.exists() else ROOT.parent / ".work/m6-safety-state.json"
        saved = json.loads(source.read_text(encoding="utf-8"))
        self.project, self.token, self.password = saved["project"], saved["token"], saved["password"]
        self.env = {**os.environ, **saved["env"]}
        self.model_key = Path(self.env["ZHIYU_MODEL_KEY_FILE"]).read_text().strip()
        self.base = saved["base"]
        self.target_ip, self.source_ip = saved["target_ip"], saved["source_ip"]
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        if STATE.exists():
            self.directory = Path(saved["directory"])
            self.report = json.loads((self.directory / "result.json").read_text())
            if self.report["status"] == "FAIL":
                name = "failed-attempt-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + ".json"
                (self.directory / name).write_text(json.dumps(self.report, indent=2), encoding="utf-8")
                self.report["status"] = "IN_PROGRESS"
                self.report.pop("error", None)
                self.save()
            return
        self.directory = ROOT / "docs/m6-runtime/gate-d-001"
        self.directory.mkdir(exist_ok=False)
        prior = Path(saved["directory"])
        overlay = yaml.safe_load((prior / "compose.override.yml").read_text())
        volumes = overlay["services"]["api"]["volumes"]
        volumes[:] = [v for v in volumes if v["target"] != "/safety-output"]
        volumes.append({"type": "bind", "source": str(self.directory), "target": "/load-output"})
        (self.directory / "compose.override.yml").write_text(yaml.safe_dump(overlay), encoding="utf-8")
        environments = [
            f"m3-m6-d-{kind}-{i:02d}"
            for kind in ["pilot", "soak", "sequential", "concurrent2", "concurrent4", "budget"]
            for i in range(40)
        ]
        tokens = json.loads(self.env["ZHIYU_SERVICE_TOKENS"])
        for principal in tokens.values():
            principal["environment_ids"] += environments
        policies = json.loads(self.env["ZHIYU_AI_POLICIES"])
        policies.update(
            {env: {"enabled": True, "mode": "SHADOW", "provider_id": "local"} for env in environments}
        )
        self.env.update(ZHIYU_SERVICE_TOKENS=json.dumps(tokens), ZHIYU_AI_POLICIES=json.dumps(policies))
        self.report = {
            "gate": "D",
            "status": "IN_PROGRESS",
            "project": self.project,
            "started_at": datetime.now(UTC).isoformat(),
            "checks": {},
            "commands": [],
            "model_runtime": json.loads((prior / "result.json").read_text())["model_runtime"],
            "gate_c_sha256": hashlib.sha256(
                (ROOT / "docs/m6-runtime/gate-c-acceptance.json").read_bytes()
            ).hexdigest(),
            "limitations": "Shared, prepopulated B/C laboratory DB; new D environment identities. Current source mounted read-only. No production SLA.",
        }
        self.save()
        self.persist()

    def persist(self):
        STATE.write_text(
            json.dumps(
                {
                    "project": self.project,
                    "directory": str(self.directory),
                    "token": self.token,
                    "password": self.password,
                    "env": {
                        k: v
                        for k, v in self.env.items()
                        if k.startswith("ZHIYU_")
                        or k in {"POSTGRES_PASSWORD", "COMPOSE_ANSI", "BUILDKIT_PROGRESS"}
                    },
                    "base": self.base,
                    "target_ip": self.target_ip,
                    "source_ip": self.source_ip,
                }
            ),
            encoding="utf-8",
        )

    def monitored(self, name, command, timeout):
        stop = threading.Event()
        path = self.directory / (name + "-resources.jsonl")
        assert not path.exists(), "preserve prior measurement; choose a new attempt name"

        def collect():
            names = [self.project + "-" + service + "-1" for service in ["api", "postgres", "local-model"]]
            while True:
                row = {"observed_at": datetime.now(UTC).isoformat()}
                for label, args in [
                    ("stats", ["stats", "--no-stream", "--format", "{{json .}}", *names]),
                    ("states", ["inspect", "--format", "{{json .State}} {{.RestartCount}}", *names]),
                    (
                        "model_memory",
                        [
                            "exec",
                            names[-1],
                            "sh",
                            "-c",
                            "cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak /sys/fs/cgroup/memory.swap.current /sys/fs/cgroup/memory.events; cat /proc/1/status",
                        ],
                    ),
                ]:
                    try:
                        result = subprocess.run(
                            ["docker", *args],
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            timeout=20,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                        )
                        row[label] = {"returncode": result.returncode, "stdout": result.stdout}
                    except subprocess.TimeoutExpired:
                        row[label] = {"error": "METRICS_TIMEOUT"}
                with path.open("a", encoding="utf-8") as stream:
                    stream.write(self.sanitize(json.dumps(row)) + "\n")
                if stop.wait(15):
                    return

        monitor = threading.Thread(target=collect, daemon=True)
        monitor.start()
        try:
            self.compose("exec", "-T", "api", "python", *command, timeout=timeout)
        finally:
            stop.set()
            monitor.join(timeout=65)
            assert not monitor.is_alive(), "resource monitor did not finish"

    def pilot(self):
        self.monitored(
            "pilot",
            ["tools/m6_soak.py", self.target_ip, self.source_ip, "--seconds", "10", "--kind", "pilot"],
            240,
        )

    def soak(self):
        self.monitored("soak", ["tools/m6_soak.py", self.target_ip, self.source_ip], 2400)
        result = json.loads((self.directory / "soak.json").read_text())
        self.check(
            "soak_actual_30_minutes",
            result["status"] == "COMPLETED" and result["elapsed_seconds"] >= 1800,
            result["elapsed_seconds"],
        )

    def benchmark(self, kind):
        self.monitored(kind, ["tools/m6_benchmarks.py", kind, "--largest-budget-seconds", "3600"], 10800)
        result = json.loads((self.directory / (kind + ".json")).read_text())
        self.check(kind + "_measurement_recorded", result["status"] == "COMPLETED_MEASUREMENT")

    def events(self):
        self.benchmark("events")

    def events_finish(self):
        self.monitored("events-finish", ["tools/m6_finish_events.py"], 4200)
        result = json.loads((self.directory / "events-completed.json").read_text())
        self.check("events_100k_dataset_completed", result["result"]["events"] == 100000)

    def events_streaming(self):
        self.monitored("events-streaming", ["tools/m6_streaming_events.py"], 4200)
        result = json.loads((self.directory / "events-streaming.json").read_text())
        self.check("events_100k_fresh_completed", result["result"]["events"] == 100000)

    def remaining_load(self):
        self.monitored("late-review", ["tools/m6_late_load_review.py"], 900)
        self.events_streaming()
        self.response()
        self.verification()
        self.ai()

    def response(self):
        self.benchmark("response")

    def verification(self):
        self.benchmark("verification")

    def ai(self):
        started = datetime.now(UTC).isoformat()
        self.monitored("ai", ["tools/m6_ai_load.py", self.target_ip, self.source_ip], 2400)
        logs = self.docker("logs", "--timestamps", "--since", started, self.project + "-local-model-1")
        (self.directory / "ai-model-server.log").write_text(
            self.sanitize(logs.stdout + logs.stderr), encoding="utf-8"
        )
        result = json.loads((self.directory / "ai-load.json").read_text())
        self.check(
            "ai_bounded_load_recorded",
            result["status"] == "COMPLETED_MEASUREMENT" and result["provider_calls"] == 16,
        )

    def finish(self):
        for name in ["response.json", "verification.json", "ai-load.json"]:
            assert json.loads((self.directory / name).read_text())["status"] == "COMPLETED_MEASUREMENT"
        path = self.directory / "final-database-snapshot.json"
        assert not path.exists(), "preserve prior final snapshot"
        if not (self.directory / "load-queue-review.json").exists():
            self.compose("exec", "-T", "api", "python", "tools/m6_queue_review.py", timeout=180)
        result = self.compose(
            "exec",
            "-T",
            "api",
            "python",
            "tools/m6_database_snapshot.py",
            "--statement-timeout-ms",
            "180000",
            timeout=1800,
        )
        snapshot = json.loads(result.stdout)
        assert snapshot["high_risk_automatic_actions"] == 0 and all(snapshot["audit_chains"].values())
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        from m6_runtime_proof import main as prove_runtime

        prove_runtime("D")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase",
        choices=[
            "start",
            "pilot",
            "soak",
            "events",
            "events_finish",
            "events_streaming",
            "response",
            "verification",
            "ai",
            "remaining_load",
            "finish",
        ],
    )
    run = Load()
    try:
        getattr(run, parser.parse_args().phase)()
    except Exception:
        run.report["status"] = "FAIL"
        run.report["error"] = run.sanitize(traceback.format_exc())
        run.save()
        raise


if __name__ == "__main__":
    main()
