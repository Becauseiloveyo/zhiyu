"""Read actual process, heartbeat, drop, event and coverage observations from the Lab."""

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from m6_jsonl import complete_records
from m6_sensor_capture import COMPOSE, DOCKER, ROOT, command


def collect(directory, expected_requests):
    directory.mkdir(parents=True, exist_ok=False)
    now = datetime.now(UTC)
    result = {"observed_at": now.isoformat(), "expected_requests": sorted(expected_requests), "processes": {}}
    for service in ["suricata", "wazuh-manager", "wazuh-agent"]:
        cid = subprocess.check_output([*COMPOSE, "ps", "-a", "-q", service], text=True).strip()
        item = json.loads(subprocess.check_output([DOCKER, "inspect", cid]))[0]
        result["processes"][service] = {
            "id": item["Id"],
            "running": item["State"]["Running"] and not item["State"]["Paused"],
            "paused": item["State"]["Paused"],
            "started_at": item["State"]["StartedAt"],
            "hostname": item["Config"]["Hostname"],
        }
    sensor = result["processes"]["suricata"]
    path = "/var/log/suricata/" + sensor["hostname"] + "/eve.json"
    command([DOCKER, "cp", f"{sensor['id']}:{path}", str(directory / "eve.json")], directory, "eve-copy")
    payload = (directory / "eve.json").read_bytes()
    records, pending = complete_records(payload)
    stats = [entry for _, _, entry in records if entry.get("event_type") == "stats"]
    http = [
        entry
        for _, _, entry in records
        if entry.get("event_type") == "http"
        and urlsplit(entry.get("http", {}).get("url", "")).path == "/login"
    ]
    seen = {
        value
        for entry in http
        for value in parse_qs(urlsplit(entry["http"]["url"]).query).get("request_id", [])
    }
    result["suricata"] = {
        "stats": stats[-1] if stats else None,
        "last_event_at": max((entry["timestamp"] for entry in http), default=None),
        "http_records": len(http),
        "seen_requests": sorted(seen & expected_requests),
        "pending_tail": pending,
        "raw_sha256": hashlib.sha256(payload).hexdigest(),
    }
    manager = result["processes"]["wazuh-manager"]
    command(
        [DOCKER, "cp", f"{manager['id']}:/var/ossec/logs/alerts/alerts.json", str(directory / "alerts.json")],
        directory,
        "alerts-copy",
    )
    payload = (directory / "alerts.json").read_bytes()
    records, pending = complete_records(payload)
    alerts = [
        entry for _, _, entry in records if entry.get("data", {}).get("request_id") in expected_requests
    ]
    detail = None
    if manager["running"]:
        raw = command(
            [*COMPOSE, "exec", "-T", "wazuh-manager", "/var/ossec/bin/agent_control", "-i", "001", "-j"],
            directory,
            "agent-status",
            check=False,
        )
        if raw.strip():
            detail = json.loads(raw)
    result["wazuh"] = {
        "agent_status": detail,
        "seen_requests": sorted({entry["data"]["request_id"] for entry in alerts}),
        "last_event_at": max((entry["timestamp"] for entry in alerts), default=None),
        "pending_tail": pending,
        "raw_sha256": hashlib.sha256(payload).hexdigest(),
    }
    (directory / "proof.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    assert directory.is_relative_to(ROOT / "docs/m6-runtime")
    source = json.loads((args.capture / "manifest.json").read_text())
    result = collect(directory, set(source["request_ids"]))
    print(json.dumps({"proof": str(directory / "proof.json"), "processes": result["processes"]}))


if __name__ == "__main__":
    main()
