"""Gate A real stop/recovery, stale observations, replay and persistence acceptance."""

import argparse
import json
import subprocess
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

from m6_jsonl import complete_records
from m6_sensor_capture import COMPOSE, DOCKER, ROOT, command
from m6_sensor_health_capture import collect


def traffic(directory):
    raw = command([*COMPOSE, "run", "--rm", "client"], directory, "traffic")
    expected = {row["request_id"] for row in json.loads(raw)["requests"] if "request_id" in row}
    return expected


def await_alerts(directory, expected):
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        response = subprocess.run(
            [*COMPOSE, "exec", "-T", "wazuh-manager", "cat", "/var/ossec/logs/alerts/alerts.json"],
            capture_output=True,
            timeout=15,
        )
        (directory / "alerts-poll.raw").write_bytes(response.stdout)
        seen = {row.get("data", {}).get("request_id") for _, _, row in complete_records(response.stdout)[0]}
        if expected <= seen:
            time.sleep(6)
            return
        time.sleep(2)
    raise RuntimeError("real agent delivery did not recover within 75 seconds")


def await_agent_collector(directory):
    """Container start/agent connection precedes logcollector readiness on Wazuh."""
    cid = subprocess.check_output([*COMPOSE, "ps", "-q", "wazuh-agent"], text=True).strip()
    state = json.loads(
        command([DOCKER, "inspect", "--format", "{{json .State}}", cid], directory, "agent-state")
    )
    started = datetime.fromisoformat(state["StartedAt"].replace("Z", "+00:00")).replace(microsecond=0)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        raw = command(
            [*COMPOSE, "exec", "-T", "wazuh-agent", "cat", "/var/ossec/logs/ossec.log"],
            directory,
            "agent-readiness",
        )
        for line in raw.decode("utf-8").splitlines():
            if "wazuh-logcollector: INFO: Started (pid:" not in line:
                continue
            observed = datetime.strptime(line[:19], "%Y/%m/%d %H:%M:%S").replace(tzinfo=UTC)
            if observed >= started:
                return
        time.sleep(1)
    raise RuntimeError("Wazuh logcollector did not become ready within 45 seconds")


def execute(capture, output):
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "gate": "A",
        "scope": "CONTROLLED_LAB",
        "status": "RUNNING",
        "checks": {},
        "started_at": datetime.now(UTC).isoformat(),
    }
    base_requests = set(json.loads((capture / "manifest.json").read_text())["request_ids"])
    relative = capture.relative_to(ROOT).as_posix()

    def save():
        (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    def verdict(name, expected, requests=None, record=True):
        directory = output / name
        directory.mkdir()
        args = [
            *COMPOSE,
            "run",
            "--rm",
            "runner",
            "python",
            "tools/m6_sensor_verification.py",
            relative,
            "--case",
            output.name + "/" + name,
        ]
        if record:
            collect(directory / "health", requests or base_requests)
            args += ["--proof", (directory / "health/proof.json").relative_to(ROOT).as_posix()]
        data = json.loads(command(args, directory, "verification"))
        (directory / "verification.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        actual = data["verification"]["status"]
        result["checks"][name] = {
            "status": "PASS" if actual == expected else "FAIL",
            "expected_verdict": expected,
            "actual_verdict": actual,
            "verification_id": data["verification"]["verification_id"],
        }
        save()
        assert actual == expected, (name, expected, actual)
        print(f"{name}: expected={expected} actual={actual}", flush=True)

    def recovery(name, service):
        directory = output / (name + "-traffic")
        directory.mkdir()
        command([*COMPOSE, "start", service], directory, "start")
        if service == "wazuh-agent":
            await_agent_collector(directory)
        expected = traffic(directory)
        await_alerts(directory, expected)
        verdict(name, "PASS", expected)
        return expected

    try:
        for service in ["suricata", "wazuh-manager", "wazuh-agent"]:
            directory = output / (service + "-stop")
            directory.mkdir()
            command([*COMPOSE, "stop", service], directory, "stop")
            verdict(service + "-unavailable", "INCONCLUSIVE")
            base_requests = recovery(service + "-recovered", service)
        # Freeze only the collector's last real DB observation, not wall time or sensor processes.
        wait_started = time.monotonic()
        while time.monotonic() - wait_started < 131:
            time.sleep(min(30, 131 - (time.monotonic() - wait_started)))
            print(f"collector paused for real stale test: {time.monotonic() - wait_started:.1f}s", flush=True)
        result["stale_elapsed_seconds"] = time.monotonic() - wait_started
        verdict("collector-stale", "INCONCLUSIVE", record=False)
        directory = output / "delay-traffic"
        directory.mkdir()
        command([*COMPOSE, "pause", "wazuh-agent"], directory, "pause")
        expected = traffic(directory)
        verdict("agent-delivery-delayed", "INCONCLUSIVE", expected)
        command([*COMPOSE, "unpause", "wazuh-agent"], directory, "unpause")
        await_alerts(directory, expected)
        verdict("agent-delivery-caught-up", "PASS", expected)
        directory = output / "database-restart"
        directory.mkdir()
        args = [*COMPOSE, "run", "--rm", "runner", "python", "tools/m6_database_snapshot.py"]
        before = json.loads(command(args, directory, "before"))
        command([*COMPOSE, "restart", "postgres"], directory, "restart")
        after = json.loads(command(args, directory, "after"))
        assert before == after, "committed database tables changed across restart"
        result["checks"]["database-restart-persistence"] = {
            "status": "PASS",
            "tables_verified": len(after["tables"]),
        }
        replay = json.loads(
            command(
                [
                    *COMPOSE,
                    "run",
                    "--rm",
                    "runner",
                    "python",
                    "tools/m6_sensor_ingest.py",
                    relative,
                    "--environment",
                    "m6-real-" + capture.name,
                    "--replay",
                ],
                directory,
                "replay",
            )
        )
        for delivery in replay["deliveries"].values():
            assert delivery["accepted"] == delivery["errors"] == 0 and delivery["duplicates"] > 0
        assert replay["grouped"]["processed"] == 0
        final = json.loads(command(args, directory, "after-replay"))
        logical = [
            "normalized_events",
            "raw_records",
            "event_groups",
            "incidents",
            "evidence",
            "plans",
            "tasks",
            "action_requests",
            "action_execution_results",
            "verification_results",
        ]
        assert all(after["tables"][name] == final["tables"][name] for name in logical)
        assert all(final["audit_chains"].values()) and final["high_risk_automatic_actions"] == 0
        result["checks"]["duplicate-replay"] = {"status": "PASS", "logical_tables_unchanged": logical}
        result["checks"]["audit-and-high-risk"] = {"status": "PASS", "high_risk_automatic_actions": 0}
        result["status"] = "PASS"
    except Exception:
        result["status"] = "FAIL"
        (output / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        # Restore only this task's three sensor containers, keeping all data volumes.
        subprocess.run([*COMPOSE, "unpause", "wazuh-agent"], capture_output=True, timeout=30)
        subprocess.run(
            [*COMPOSE, "start", "suricata", "wazuh-manager", "wazuh-agent"], capture_output=True, timeout=90
        )
        result["finished_at"] = datetime.now(UTC).isoformat()
        save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    capture, output = args.capture.resolve(), args.output.resolve()
    assert capture.is_relative_to(ROOT / "docs/m6-runtime") and output.is_relative_to(
        ROOT / "docs/m6-runtime"
    )
    execute(capture, output)


if __name__ == "__main__":
    main()
