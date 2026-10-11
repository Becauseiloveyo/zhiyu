"""Correlate real Suricata HTTP tuples with actual Wazuh application observations."""

import json
from datetime import datetime

from m6_jsonl import complete_records
from m6_sensor_health_capture import collect


def collect_paths(directory, start):
    proof = collect(directory, set())
    boundary = datetime.fromisoformat(start)
    http = [
        r
        for _, _, r in complete_records((directory / "eve.json").read_bytes())[0]
        if r.get("event_type") == "http"
        and r.get("dest_port") == 8081
        and r.get("http", {}).get("url") in {"/attack", "/health"}
        and datetime.fromisoformat(r["timestamp"]) >= boundary
    ]
    app = [
        r
        for _, _, r in complete_records((directory / "alerts.json").read_bytes())[0]
        if str(r.get("rule", {}).get("id")) == "110003"
        and datetime.fromisoformat(r.get("data", {}).get("timestamp", r["timestamp"])) >= boundary
    ]
    pairs = []
    for flow in http:
        matches = [
            r
            for r in app
            if r["data"].get("srcip") == flow["src_ip"]
            and int(r["data"].get("srcport", 0)) == flow["src_port"]
            and r["data"].get("path") == flow["http"]["url"]
        ]
        if matches:
            pairs.append(
                {
                    "path": flow["http"]["url"],
                    "source_ip": flow["src_ip"],
                    "source_port": flow["src_port"],
                    "suricata_timestamp": flow["timestamp"],
                    "wazuh_timestamp": matches[0]["timestamp"],
                    "application_timestamp": matches[0]["data"]["timestamp"],
                    "application_http_status": int(matches[0]["data"]["http_status"]),
                    "flow_id": str(flow["flow_id"]),
                    "wazuh_alert_id": matches[0]["id"],
                }
            )
    proof.update(
        window_start=start,
        path_pairs=pairs,
        path_coverage={p: any(pair["path"] == p for pair in pairs) for p in ("/attack", "/health")},
    )
    (directory / "proof.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    return proof
