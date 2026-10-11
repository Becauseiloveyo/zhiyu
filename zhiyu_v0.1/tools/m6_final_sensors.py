"""Fresh real-sensor project, using the final source-baked test image as runner."""

import json
import subprocess

import m6_gate_a
import m6_sensor_capture
import m6_sensor_health_capture
import yaml
from runtime_acceptance import ROOT


def run(acceptance):
    directory = acceptance.directory / "sensors"
    directory.mkdir()
    project = acceptance.project + "-sensors"
    original = m6_sensor_capture.COMPOSE[:]
    secret_file = ROOT.parent / ".work" / (project + "-lab-control.token")
    secret_file.write_text(acceptance.token, encoding="utf-8")
    overlay_path = directory / "compose.runner.yml"
    overlay = {
        "services": {
            "runner": {
                "image": acceptance.project + "-tests:latest",
                "working_dir": "/app",
                "environment": {"PYTHONPATH": "/app/src:/app/tools"},
                "secrets": ["lab-control"],
                "volumes": [
                    {
                        "type": "bind",
                        "source": str(ROOT / "docs/m6-runtime"),
                        "target": "/app/docs/m6-runtime",
                        "read_only": True,
                    }
                ],
            },
            "containment-target": {
                "image": acceptance.project + "-api:latest",
                "command": ["python", "tools/m6_lab_observed_target.py"],
                "network_mode": "service:target",
                "user": "0:0",
                "environment": {
                    "ZHIYU_LAB_DISPOSABLE_TARGET": "1",
                    "ZHIYU_LAB_ENVIRONMENT": "m6-real-final-sensor-" + acceptance.project.rsplit("-", 1)[-1],
                },
                "secrets": ["lab-control"],
                "volumes": ["lab_logs:/lab-logs"],
                "tmpfs": ["/tmp"],
                "read_only": True,
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges:true"],
                "mem_limit": "128m",
                "cpus": 1,
                "depends_on": {"target": {"condition": "service_healthy"}},
            },
            "suricata": {
                "volumes": [
                    str(ROOT / "lab/real-sensors/remediation.rules") + ":/lab.rules:ro",
                    "suricata_logs:/var/log/suricata",
                ]
            },
            "wazuh-manager": {
                "volumes": [
                    str(ROOT / "lab/real-sensors/wazuh-manager.conf")
                    + ":/wazuh-config-mount/etc/ossec.conf:ro",
                    str(ROOT / "lab/real-sensors/wazuh-remediation-rules.xml")
                    + ":/wazuh-config-mount/etc/rules/zhiyu_lab.xml:ro",
                    "wazuh_logs:/var/ossec/logs",
                    "wazuh_etc:/var/ossec/etc",
                    "wazuh_queue:/var/ossec/queue",
                ]
            },
        },
        "secrets": {"lab-control": {"file": str(secret_file)}},
    }
    overlay_path.write_text(
        yaml.safe_dump(overlay).replace("    volumes:", "    volumes: !override"), encoding="utf-8"
    )
    command = [
        m6_sensor_capture.DOCKER,
        "compose",
        "-p",
        project,
        "-f",
        str(ROOT / "docker-compose.sensors.yml"),
        "-f",
        str(overlay_path),
    ]
    # Release only the previous task-owned sensor network; keep all old volumes/evidence.
    m6_sensor_capture.command([*original, "down"], directory, "previous-lab-down")
    m6_sensor_capture.COMPOSE[:] = command
    m6_sensor_capture.PROJECT = project
    result = {
        "status": "RUNNING",
        "project": project,
        "scope": "CONTROLLED_LAB",
        "runner_image": acceptance.project + "-tests:latest",
        "source_digest": acceptance.rc["source_digest"],
    }
    try:
        m6_sensor_capture.command([*command, "config"], directory, "effective-compose")
        m6_sensor_capture.command(
            [
                *command,
                "up",
                "-d",
                "--build",
                "target",
                "suricata",
                "wazuh-manager",
                "wazuh-agent",
                "postgres",
                "containment-target",
            ],
            directory,
            "up",
        )
        m6_gate_a.await_agent_collector(directory)
        m6_sensor_capture.command(
            [*command, "run", "--rm", "runner", "python", "-m", "alembic", "upgrade", "head"],
            directory,
            "migrate",
        )
        capture = directory / ("final-sensor-" + acceptance.project.rsplit("-", 1)[-1])
        manifest = m6_sensor_capture.capture(capture, traffic=True)
        relative = capture.relative_to(ROOT).as_posix()
        ingest = json.loads(
            m6_sensor_capture.command(
                [
                    *command,
                    "run",
                    "--rm",
                    "runner",
                    "python",
                    "tools/m6_sensor_ingest.py",
                    relative,
                    "--environment",
                    "m6-real-" + capture.name,
                ],
                capture,
                "ingest",
            )
        )
        (capture / "result.json").write_text(json.dumps(ingest, indent=2), encoding="utf-8")
        assert ingest["status"] == "PASS"
        proof = directory / "initial-health"
        m6_sensor_health_capture.collect(proof, set(manifest["request_ids"]))
        initialization = json.loads(
            m6_sensor_capture.command(
                [
                    *command,
                    "run",
                    "--rm",
                    "runner",
                    "python",
                    "tools/m6_sensor_verification.py",
                    relative,
                    "--proof",
                    (proof / "proof.json").relative_to(ROOT).as_posix(),
                    "--case",
                    "final-initial",
                    "--initialize",
                ],
                directory,
                "initial-verification",
            )
        )
        assert initialization["verification"]["status"] == "PASS"
        (directory / "initial-verification.json").write_text(
            json.dumps(initialization, indent=2), encoding="utf-8"
        )
        m6_gate_a.execute(capture, directory / "sensor-faults")
        from m6_final_sensor_outage import run as sensor_outage

        outage = sensor_outage(command, directory / "a10-database-outage")
        assert outage["status"] == "PASS"
        from m6_lab_host import run as remediate

        remediation = remediate(acceptance, capture, command, directory / "remediation")
        assert remediation["status"] == "PASS"
        result.update(
            status="PASS",
            capture=capture.relative_to(ROOT).as_posix(),
            sensor_health_and_recovery="sensor-faults/result.json",
            raw_lineage_count=len(ingest["lineage"]),
            high_risk_automatic_actions=remediation["high_risk_automatic_actions"],
            remediation="remediation/result.json",
            database_outage="a10-database-outage/result.json",
        )
    except Exception as error:
        result.update(status="FAIL", error=acceptance.sanitize(str(error)))
        raise
    finally:
        m6_sensor_capture.command([*command, "down"], directory, "final-lab-down")
        remaining = subprocess.check_output(
            [
                m6_sensor_capture.DOCKER,
                "ps",
                "-aq",
                "--filter",
                "label=com.docker.compose.project=" + project,
            ],
            text=True,
        ).strip()
        result["remaining_project_containers"] = remaining.splitlines()
        assert not remaining
        result["retained_volumes"] = "Evidence recovery only; no volume deletion"
        (directory / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        m6_sensor_capture.COMPOSE[:] = original
        m6_sensor_capture.PROJECT = "zhiyu-m6-sensors"
    return result
