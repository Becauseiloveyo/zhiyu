"""A10: retain actual independent sensor observations across a controller DB outage."""

import json

import m6_sensor_capture as sensor
from runtime_acceptance import ROOT


def run(command, directory):
    directory.mkdir(exist_ok=False)
    report = {"status": "RUNNING", "scope": "CONTROLLED_LAB_REAL_SENSORS"}
    try:
        sensor.command([*command, "stop", "postgres"], directory, "database-stop")
        state = json.loads(
            sensor.command(
                [*command, "ps", "--all", "--format", "json", "postgres"], directory, "database-state"
            )
        )
        assert state["State"] == "exited"
        capture = directory / "traffic-during-database-outage"
        manifest = sensor.capture(capture, traffic=True)
        assert manifest["containers"]["postgres"]["status"] == "exited"
        assert all(
            manifest["containers"][s]["status"] == "running"
            for s in ("target", "suricata", "wazuh-manager", "wazuh-agent")
        )
        sensor.command([*command, "start", "postgres"], directory, "database-recover")
        result = json.loads(
            sensor.command(
                [
                    *command,
                    "run",
                    "--rm",
                    "runner",
                    "python",
                    "tools/m6_sensor_ingest.py",
                    capture.relative_to(ROOT).as_posix(),
                    "--environment",
                    "m6-real-" + capture.name,
                ],
                directory,
                "recovered-ingest",
            )
        )
        (directory / "ingest-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        assert result["status"] == "PASS"
        report.update(
            status="PASS",
            database_during_traffic="exited",
            sensors_during_traffic="running",
            request_ids=manifest["request_ids"],
            capture=capture.relative_to(ROOT).as_posix(),
        )
    except Exception:
        report["status"] = "FAIL"
        raise
    finally:
        sensor.command([*command, "start", "postgres"], directory, "ensure-database-recovery")
        (directory / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
