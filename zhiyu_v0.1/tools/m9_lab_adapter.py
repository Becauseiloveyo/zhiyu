"""Host-installed fixed adapter. Docker authority never enters the API or runner containers.

All paths, services, targets and traffic come from this versioned adapter. The Web command
contains only A-E and a registered profile. Per-run resources have two ownership labels.
"""

import hashlib
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session

from zhiyu.db.demo_control import DemoRunRow
from zhiyu.product.access import authorize, product_settings
from zhiyu.product.contracts import Query
from zhiyu.product.demo_contracts import StepOutput, source_environment
from zhiyu.product.queries import create_snapshot
from zhiyu.product.reports import build as build_report
from zhiyu.product.reports import markdown

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT.parent / ".work/m9-demo"
EVIDENCE = ROOT / "artifacts/v0.9/lab"
OWNER = "zhiyu-v09-fixed-demo"
CONTROL_NETWORK = "zhiyu-m9-demo-control"
SERVICES = {
    "target",
    "client",
    "suricata",
    "wazuh-manager",
    "wazuh-agent",
    "runner",
    "containment-target",
    "local-model",
    "model-fault-fixture",
}
MODEL_SHA = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"


def docker(*args, env=None, timeout=120):
    return subprocess.run(
        ["docker", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def checked(*args, **kwargs):
    run = docker(*args, **kwargs)
    if run.returncode:
        raise RuntimeError("owned_docker_operation_failed")
    return run.stdout


def owned_inventory(project):
    inventory = {}
    for kind, listing in (
        ("container", ["ps", "-aq"]),
        ("network", ["network", "ls", "-q"]),
        ("volume", ["volume", "ls", "-q"]),
    ):
        values = checked(*listing, "--filter", "label=com.docker.compose.project=" + project).decode().split()
        inventory[kind] = values
        for ident in values:
            obj = json.loads(checked(kind, "inspect", ident))[0]
            labels = obj["Config"]["Labels"] if kind == "container" else obj["Labels"]
            if labels.get("zhiyu.owner") != OWNER or labels.get("zhiyu.run") != project:
                raise RuntimeError("foreign_resource_in_demo_project")
            if kind == "container" and labels.get("com.docker.compose.service") not in SERVICES:
                raise RuntimeError("unregistered_demo_service")
    return inventory


class ControlledLab:
    def __init__(self, engine, config):
        self.engine, self.config = engine, config

    def perform(self, work, current):
        source_environment(work.run_id)  # strict server-generated ID before deriving any path
        self.work, self.current = work, current
        self.project = "zhiyu-v09-" + work.run_id
        self.directory = EVIDENCE / work.run_id
        self.private = PRIVATE / work.run_id
        self.directory.mkdir(parents=True, exist_ok=True)
        self.private.mkdir(parents=True, exist_ok=True)
        self.compose = ["compose", "-p", self.project, "-f", str(self.private / "compose.json")]
        self.env = {**os.environ, "ZHIYU_DATABASE_URL": self.config["container_database_url"]}
        self.proof_index = len(list(self.directory.glob("path-proof-*")))
        (self.directory / "work.json").write_text(work.model_dump_json(), encoding="utf-8")
        if not current():
            raise RuntimeError("demo_adapter_fenced")
        if work.operation == "PREFLIGHT":
            return self.preflight()
        # Ownership is checked again after every worker restart and before cleanup.
        owned_inventory(self.project)
        if work.operation == "CLEANUP":
            return self.cleanup()
        if work.operation == "ARCHIVE":
            return self.archive()
        self.bind_collectors()
        if work.operation == "TRIGGER":
            return self.trigger()
        if work.operation == "VERIFY":
            return self.verify()
        raise ValueError("unregistered_operation")

    def call(self, *args, timeout=120):
        if not self.current():
            raise RuntimeError("demo_adapter_fenced")
        run = docker(*self.compose, *args, env=self.env, timeout=timeout)
        # Private diagnostics; never a Product API field or release-package artifact.
        with (self.private / "commands.log").open("ab") as log:
            log.write(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError("fixed_lab_command_failed")
        return run.stdout

    def phase(self, name):
        payload = self.call(
            "run",
            "--rm",
            "--no-deps",
            "runner",
            "python",
            "tools/m9_lab_phase.py",
            name,
            timeout=280 if name == "analyze" else 90,
        )
        value = json.loads(payload)
        (self.directory / (name + ".json")).write_text(json.dumps(value, indent=2), encoding="utf-8")
        return value

    def bind_collectors(self):
        import m6_gate_a
        import m6_sensor_capture
        import m6_sensor_health_capture

        for module in (m6_gate_a, m6_sensor_capture, m6_sensor_health_capture):
            module.COMPOSE = ["docker", *self.compose]
        m6_sensor_capture.PROJECT = self.project

    def preflight(self):
        if any(owned_inventory(self.project).values()):
            raise RuntimeError("preflight_existing_resources_no_redispatch")
        model = Path(self.config["model_path"])
        with model.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != MODEL_SHA:
                raise RuntimeError("model_integrity_failure")
        image = self.config["image_id"]
        if (
            not image.startswith("sha256:")
            or json.loads(checked("image", "inspect", image))[0]["Id"] != image
        ):
            raise RuntimeError("source_baked_image_required")
        # Compose input is generated from trusted repository templates, not API data.
        compose = yaml.safe_load((ROOT / "docker-compose.sensors.yml").read_text())
        compose["services"].pop("postgres")
        compose["volumes"].pop("postgres_data")
        labels = {"zhiyu.owner": OWNER, "zhiyu.run": self.project}
        compose["networks"]["control"] = {"external": True, "name": CONTROL_NETWORK}
        compose["networks"]["lab"]["labels"] = labels
        for key in compose["volumes"]:
            compose["volumes"][key] = {"labels": labels}
        services = compose["services"]
        # Trusted installation configuration may pin independently rebuilt Sensor images.
        # No Product API command can supply or change these identities.
        if "sensor_images" in self.config:
            for name in ("target", "client", "suricata"):
                services[name]["image"] = self.config["sensor_images"]["sensor"]
            services["wazuh-manager"]["image"] = self.config["sensor_images"]["wazuh"]
        for service in services.values():
            service.pop("build", None)
            service["labels"] = labels
            service["volumes"] = [
                str(ROOT / v.split(":", 1)[0][2:]) + ":" + v.split(":", 1)[1] if v.startswith("./") else v
                for v in service.get("volumes", [])
            ]
        services["suricata"]["volumes"] = [
            str(ROOT / "lab/real-sensors/remediation.rules") + ":/lab.rules:ro",
            "suricata_logs:/var/log/suricata",
        ]
        services["wazuh-manager"]["volumes"][1] = (
            str(ROOT / "lab/real-sensors/wazuh-remediation-rules.xml")
            + ":/wazuh-config-mount/etc/rules/zhiyu_lab.xml:ro"
        )
        runner = services["runner"]
        runner.update(
            image=image,
            working_dir="/app",
            environment={"PYTHONPATH": "/app/src:/app/tools", "ZHIYU_DATABASE_URL": None},
            volumes=[
                str(self.directory) + ":/evidence:ro",
                "suricata_logs:/sensor-evidence/suricata:ro",
                "wazuh_logs:/sensor-evidence/wazuh:ro",
                "lab_logs:/sensor-evidence/app:ro",
            ],
            secrets=["lab-control", "model-key"],
            read_only=True,
            tmpfs=["/tmp"],
            mem_limit="768m",
            cpus=2,
        )
        runner.pop("depends_on")
        services["containment-target"] = {
            "image": image,
            "command": ["python", "tools/m6_lab_observed_target.py"],
            "network_mode": "service:target",
            "user": "0:0",
            "environment": {
                "ZHIYU_LAB_DISPOSABLE_TARGET": "1",
                "ZHIYU_LAB_ENVIRONMENT": source_environment(self.work.run_id),
            },
            "secrets": ["lab-control"],
            "volumes": ["lab_logs:/lab-logs"],
            "tmpfs": ["/tmp"],
            "read_only": True,
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "mem_limit": "128m",
            "cpus": 1,
            "labels": labels,
            "depends_on": {"target": {"condition": "service_healthy"}},
        }
        ai = yaml.safe_load((ROOT / "docker-compose.ai.yml").read_text())["services"]
        for name in ("local-model", "model-fault-fixture"):
            service = ai[name]
            service.pop("profiles", None)
            service.pop("build", None)
            service["labels"] = labels
            if name == "local-model":
                service["command"][service["command"].index("--predict") + 1] = "2600"
                service["volumes"] = [
                    str(model) + ":/models/model.gguf:ro",
                    self.config["model_key_path"] + ":/run/secrets/model-key:ro",
                ]
            else:
                service["image"] = image
            services[name] = service
        compose["secrets"] = {
            "lab-control": {"file": self.config["lab_key_path"]},
            "model-key": {"file": self.config["model_key_path"]},
        }
        (self.private / "compose.json").write_text(json.dumps(compose, indent=2), encoding="utf-8")
        self.call(
            "up",
            "-d",
            "--wait",
            "--wait-timeout",
            "240",
            "target",
            "suricata",
            "wazuh-manager",
            "wazuh-agent",
            "containment-target",
            "model-fault-fixture",
            "local-model",
            timeout=270,
        )
        self.bind_collectors()
        from m6_gate_a import await_agent_collector

        await_agent_collector(self.directory)
        owned_inventory(self.project)
        return StepOutput(object_refs=["environment:" + source_environment(self.work.run_id)])

    def trigger(self):
        from m6_sensor_capture import capture
        from m6_sensor_health_capture import collect

        manifest = capture(
            self.directory / self.work.run_id,
            traffic=True,
            services=["target", "suricata", "wazuh-manager", "wazuh-agent"],
        )
        collect(self.directory / "initial-health", set(manifest["request_ids"]))
        prepared = self.phase("prepare")
        self.fresh_health()
        if self.work.scenario_id == "E":
            self.call("stop", "local-model")
        analyzed = self.phase("analyze")
        return StepOutput(
            object_refs=[
                "incident:" + prepared["incident_id"],
                *["model_run:" + i for i in analyzed.get("model_run_ids", [])],
            ],
            model_source=analyzed["model_source"],
        )

    def proof(self, start, offline=False):
        from m6_lab_proof import collect_paths

        deadline = time.monotonic() + 42
        while True:
            self.phase("traffic")
            time.sleep(6)
            folder = self.directory / f"path-proof-{self.proof_index:03d}"
            self.proof_index += 1
            measured = collect_paths(folder, start)
            detail = (measured["wazuh"]["agent_status"] or {}).get("data", {})
            stats = measured["suricata"]["stats"] or {}
            after = datetime.fromisoformat(start).timestamp() + 1
            if offline or (
                all(measured["path_coverage"].values())
                and all(p["running"] for p in measured["processes"].values())
                and datetime.fromisoformat(stats.get("timestamp", start)).timestamp() >= after
                and int(detail.get("lastKeepAlive", 0)) >= after
            ):
                return (folder / "proof.json").read_bytes()
            if time.monotonic() > deadline:
                raise RuntimeError("real_path_proof_unavailable")

    def fresh_health(self):
        (self.directory / "fresh-proof.json").write_bytes(self.proof(datetime.now(UTC).isoformat()))
        measured = self.phase("health")
        if not all(s["status"] == "HEALTHY" for s in measured):
            raise RuntimeError("real_sensor_health_not_ready")

    def verify(self):
        if self.work.scenario_id != "B":
            self.fresh_health()
        executed = self.phase("execute")
        scenario = self.work.scenario_id
        if scenario == "C":
            self.call("stop", "-t", "1", "wazuh-agent")
        elif scenario == "D":
            self.call(
                "exec",
                "-T",
                "containment-target",
                "python",
                "-c",
                "from pathlib import Path; Path('/tmp/business-down').touch()",
            )
        if scenario in {"A", "C", "D"}:
            (self.directory / "verification-proof.json").write_bytes(
                self.proof(executed["window_start"], offline=scenario == "C")
            )
        result = self.phase("verify")
        refs = (
            ["verification:" + result["verification"]["verification_id"]] if "verification" in result else []
        )
        if "plan_id" in executed:
            refs.append("plan:" + executed["plan_id"])
        if "receipt" in executed:
            refs.append("action:" + executed["receipt"]["action_id"])
        return StepOutput(outcome=result["outcome"], object_refs=refs)

    def archive(self):
        prepared = json.loads((self.directory / "prepare.json").read_text())
        with Session(self.engine) as db:
            row = db.get(DemoRunRow, self.work.run_id)
            principal = next(
                a.principal
                for a in product_settings.browser_users.values()
                if a.principal.principal_id == row.actor_id
            )
        query = Query(
            environment_id=source_environment(self.work.run_id), scope_id=self.work.scope_id, hours=24
        )
        with (
            self.engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection,
            connection.begin(),
        ):
            connection.execute(text("SET TRANSACTION READ ONLY"))
            with Session(bind=connection) as db:
                snapshot = create_snapshot(
                    db, query, authorize(db, principal, query), prepared["incident_id"]
                )
        content = snapshot.model_dump_json().encode()
        if len(content) > 1024 * 1024:
            raise RuntimeError("recording_budget_exceeded")
        archive = Path(product_settings.recording_root)
        archive.mkdir(parents=True, exist_ok=True)
        with (archive / (self.work.run_id + ".json")).open("xb") as stream:
            stream.write(content)
        report = build_report(snapshot)
        (self.directory / "report.json").write_text(report.model_dump_json(), encoding="utf-8")
        (self.directory / "report.md").write_text(markdown(report)["content"], encoding="utf-8")
        return StepOutput(
            object_refs=["incident:" + prepared["incident_id"], "recording:" + self.work.run_id],
            artifact_sha256=hashlib.sha256(content).hexdigest(),
        )

    def cleanup(self):
        before = owned_inventory(self.project)
        if any(before.values()):
            # Record actual process shutdown in canonical SensorHealth before deleting disposable volumes.
            from sqlalchemy.orm import Session

            from zhiyu.db.models import EnvironmentRow

            with Session(self.engine) as db:
                source_exists = db.get(EnvironmentRow, source_environment(self.work.run_id)) is not None
            if source_exists:
                self.call("stop", "-t", "1", "suricata", "wazuh-agent", "wazuh-manager")
                self.bind_collectors()
                from m6_sensor_health_capture import collect
                from m6_sensor_verification import actor, record_health

                proof = self.directory / "cleanup-sensor-proof"
                collect(proof, set())
                record_health(
                    self.engine,
                    source_environment(self.work.run_id),
                    proof / "proof.json",
                    actor(source_environment(self.work.run_id), self.directory / self.work.run_id),
                )
            self.call("down", "--volumes", "--timeout", "10", timeout=90)
        remaining = owned_inventory(self.project)
        count = sum(len(items) for items in remaining.values())
        receipt = {
            "run_id": self.work.run_id,
            "at": datetime.now(UTC).isoformat(),
            "before": before,
            "after": remaining,
            "canonical_history": "PRESERVED",
            "scope": "OWNED_DISPOSABLE_COMPOSE_RESOURCES_ONLY",
        }
        payload = json.dumps(receipt, sort_keys=True).encode()
        (self.directory / "cleanup.json").write_bytes(payload)
        return StepOutput(
            cleanup_verified=count == 0,
            residual_count=count,
            artifact_sha256=hashlib.sha256(payload).hexdigest(),
        )
