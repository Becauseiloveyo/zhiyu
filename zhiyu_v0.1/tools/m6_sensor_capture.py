"""Host-side evidence collection for the isolated real-sensor Compose project."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

from m6_jsonl import complete_records

ROOT = Path(__file__).resolve().parents[1]
DOCKER = os.environ.get(
    "ZHIYU_DOCKER", shutil.which("docker") or r"D:\Docker\Desktop\resources\bin\docker.exe"
)
PROJECT = "zhiyu-m6-sensors"
COMPOSE = [DOCKER, "compose", "-p", PROJECT, "-f", str(ROOT / "docker-compose.sensors.yml")]


def command(args, directory, name, *, check=True):
    run = subprocess.run(args, cwd=ROOT, capture_output=True, timeout=120)
    (directory / (name + ".stdout")).write_bytes(run.stdout)
    (directory / (name + ".stderr")).write_bytes(run.stderr)
    (directory / (name + ".command.json")).write_text(
        json.dumps(
            {"command": args, "exit_code": run.returncode, "captured_at": datetime.now(UTC).isoformat()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if check and run.returncode:
        raise RuntimeError(f"{name} exit={run.returncode}; retained logs at {directory}")
    return run.stdout


def capture(directory, *, traffic, services=None):
    directory.mkdir(parents=True, exist_ok=False)
    if traffic:
        traffic_output = command([*COMPOSE, "run", "--rm", "client"], directory, "traffic")
        request_ids = {
            item["request_id"] for item in json.loads(traffic_output)["requests"] if "request_id" in item
        }
        deadline = time.monotonic() + 60
        while True:
            result = subprocess.run(
                [*COMPOSE, "exec", "-T", "wazuh-manager", "cat", "/var/ossec/logs/alerts/alerts.json"],
                capture_output=True,
                timeout=15,
            )
            (directory / "alerts-poll.raw").write_bytes(result.stdout)
            observed, pending = complete_records(result.stdout)
            seen = {
                row.get("data", {}).get("request_id")
                for _, _, row in observed
                if str(row.get("rule", {}).get("id")) in {"110001", "110002"}
            }
            if request_ids <= seen:
                break
            if time.monotonic() > deadline:
                (directory / "alerts-timeout.raw").write_bytes(result.stdout)
                raise RuntimeError("Real Wazuh alerts not received within 60 seconds")
            time.sleep(2)
        time.sleep(12)  # Allow completed TCP flows to be emitted by the actual sensor.
    manifest = {
        "scenario": "SCN-LAB-AUTH-REAL-01",
        "captured_at": datetime.now(UTC).isoformat(),
        "project": PROJECT,
        "data_origin": "OBSERVED",
        "containers": {},
        "files": {},
    }
    if traffic:
        manifest["request_ids"] = sorted(request_ids)
    for service in services or ["target", "suricata", "wazuh-manager", "wazuh-agent", "postgres"]:
        cid = subprocess.check_output([*COMPOSE, "ps", "-a", "-q", service], text=True).strip()
        values = json.loads(subprocess.check_output([DOCKER, "inspect", cid]))[0]
        manifest["containers"][service] = {
            "id": values["Id"],
            "image_id": values["Image"],
            "image_ref": values["Config"]["Image"],
            "hostname": values["Config"]["Hostname"],
            "started_at": values["State"]["StartedAt"],
            "status": values["State"]["Status"],
            "restart_count": values["RestartCount"],
            "ports": values["NetworkSettings"]["Ports"],
        }
        command([*COMPOSE, "logs", "--no-color", service], directory, service + "-logs")
    for service, path, name in [
        (
            "suricata",
            "/var/log/suricata/" + manifest["containers"]["suricata"]["hostname"] + "/eve.json",
            "eve.json",
        ),
        ("suricata", "/etc/suricata/suricata.yaml", "suricata.yaml"),
        ("suricata", "/package-versions.txt", "package-versions.txt"),
        ("wazuh-manager", "/var/ossec/logs/alerts/alerts.json", "alerts.json"),
        ("target", "/lab-logs/auth.json", "application-auth.json"),
    ]:
        cid = manifest["containers"][service]["id"]
        command([DOCKER, "cp", f"{cid}:{path}", str(directory / name)], directory, "copy-" + name)
        payload = (directory / name).read_bytes()
        manifest["files"][name] = {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    command(
        [*COMPOSE, "exec", "-T", "wazuh-manager", "/var/ossec/bin/agent_control", "-l"],
        directory,
        "agent-registration",
    )
    command(
        [*COMPOSE, "exec", "-T", "wazuh-manager", "/var/ossec/bin/wazuh-control", "info"],
        directory,
        "wazuh-version",
    )
    command([*COMPOSE, "exec", "-T", "suricata", "suricata", "-V"], directory, "suricata-version")
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--traffic", action="store_true")
    args = parser.parse_args()
    directory = args.directory.resolve()
    assert directory.is_relative_to(ROOT / "docs/m6-runtime"), "task-owned evidence path required"
    capture(directory, traffic=args.traffic)
    relative = directory.relative_to(ROOT).as_posix()
    env = "m6-real-" + directory.name
    output = command(
        [
            *COMPOSE,
            "run",
            "--rm",
            "runner",
            "python",
            "tools/m6_sensor_ingest.py",
            relative,
            "--environment",
            env,
        ],
        directory,
        "ingest",
    )
    data = json.loads(output)
    (directory / "result.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": data["status"],
                "environment": env,
                "counts": data["snapshot"]["counts"],
                "event_types": data["observed_event_types"],
                "cross_source_groups": len(data["cross_source_groups"]),
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Keep the actual failure, including partial live-file snapshots already captured.
        import sys

        if len(sys.argv) > 1:
            destination = Path(sys.argv[1]).resolve()
            if destination.is_relative_to(ROOT / "docs/m6-runtime") and destination.exists():
                (destination / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
