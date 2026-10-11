"""Maintainer-only synthetic fixture authoring. Expected semantics are explicit, not adapter output."""

import json
from pathlib import Path

ROOT = Path(__file__).parent
base = {
    "timestamp": "2026-09-13T10:00:00Z",
    "src_ip": "192.0.2.10",
    "dest_ip": "10.77.20.10",
    "src_port": 51000,
    "dest_port": 8080,
    "proto": "TCP",
}
cases = [
    (
        "suricata",
        "alert",
        {
            **base,
            "event_type": "alert",
            "alert": {
                "signature_id": 990001,
                "severity": 1,
                "action": "allowed",
                "category": "SYNTHETIC test alert",
            },
        },
        {
            "activity_category": "network_alert",
            "activity_name": "signature_match",
            "outcome": "UNKNOWN",
            "severity_signal": 9,
        },
    ),
    (
        "suricata",
        "authentication",
        {
            **base,
            "event_type": "alert",
            "alert": {"signature_id": 990002, "severity": 2, "action": "allowed"},
            "http": {"hostname": "auth.example.test", "url": "/login", "http_method": "POST", "status": 401},
        },
        {
            "activity_category": "authentication",
            "activity_name": "authenticate",
            "outcome": "DENIED",
            "severity_signal": 6,
        },
    ),
    (
        "suricata",
        "http",
        {
            **base,
            "event_type": "http",
            "http": {"hostname": "example.test", "url": "/status", "http_method": "GET", "status": 200},
        },
        {
            "activity_category": "web",
            "activity_name": "http_request",
            "outcome": "SUCCESS",
            "severity_signal": 0,
        },
    ),
    (
        "suricata",
        "dns",
        {
            **base,
            "proto": "UDP",
            "dest_port": 53,
            "event_type": "dns",
            "dns": {
                "type": "answer",
                "queries": [{"rrname": "example.test", "rrtype": "A"}],
                "rcode": "NOERROR",
            },
        },
        {"activity_category": "dns", "activity_name": "answer", "outcome": "UNKNOWN", "severity_signal": 0},
    ),
    (
        "suricata",
        "tls",
        {
            **base,
            "event_type": "tls",
            "tls": {"sni": "example.test", "version": "TLS 1.3", "fingerprint": "11:22:33"},
        },
        {
            "activity_category": "tls",
            "activity_name": "handshake",
            "outcome": "UNKNOWN",
            "severity_signal": 0,
        },
    ),
    (
        "suricata",
        "flow",
        {**base, "event_type": "flow", "flow_id": 42, "flow": {"state": "closed"}},
        {"activity_category": "network", "activity_name": "flow", "outcome": "UNKNOWN", "severity_signal": 0},
    ),
    (
        "suricata",
        "unknown",
        {**base, "event_type": "new_future_type", "new_future_type": {"opaque": 123}},
        {
            "activity_category": "network",
            "activity_name": "new_future_type",
            "outcome": "UNKNOWN",
            "severity_signal": 0,
        },
    ),
]
wbase = {"timestamp": base["timestamp"], "agent": {"id": "001", "name": "auth-host", "ip": "10.77.20.10"}}
cases += [
    (
        "wazuh",
        "ssh",
        {
            **wbase,
            "id": "syn-ssh-1",
            "rule": {"id": "5716", "level": 5, "groups": ["sshd", "authentication_failed"]},
            "data": {"srcip": "192.0.2.10", "srcuser": "alice", "dstport": "22"},
        },
        {
            "activity_category": "authentication",
            "activity_name": "authenticate",
            "outcome": "DENIED",
            "severity_signal": 3,
        },
    ),
    (
        "wazuh",
        "authentication",
        {
            **wbase,
            "id": "syn-auth-1",
            "rule": {"id": "5501", "level": 3, "groups": ["pam", "authentication_success"]},
            "data": {"srcuser": "bob"},
        },
        {
            "activity_category": "authentication",
            "activity_name": "authenticate",
            "outcome": "SUCCESS",
            "severity_signal": 2,
        },
    ),
    (
        "wazuh",
        "web",
        {
            **wbase,
            "id": "syn-web-1",
            "rule": {"id": "31101", "level": 6, "groups": ["web", "apache"]},
            "data": {"url": "/error", "srcip": "192.0.2.11"},
        },
        {
            "activity_category": "web",
            "activity_name": "http_request",
            "outcome": "UNKNOWN",
            "severity_signal": 4,
        },
    ),
    (
        "wazuh",
        "windows",
        {
            **wbase,
            "id": "syn-win-1",
            "rule": {"id": "61603", "level": 9, "mitre": {"id": ["T1059"], "tactic": ["Execution"]}},
            "data": {
                "win": {
                    "system": {
                        "eventID": "1",
                        "providerName": "Microsoft-Windows-Sysmon",
                        "computer": "test-win",
                    },
                    "eventdata": {
                        "image": "C:\\Windows\\System32\\cmd.exe",
                        "user": "TEST\\alice",
                        "hashes": "SHA256=" + "a" * 64,
                    },
                }
            },
        },
        {
            "activity_category": "process",
            "activity_name": "windows_event",
            "outcome": "UNKNOWN",
            "severity_signal": 6,
        },
    ),
    (
        "wazuh",
        "generic",
        {"timestamp": base["timestamp"], "rule": {"id": "999001", "level": 99}},
        {
            "activity_category": "security_alert",
            "activity_name": "rule_match",
            "outcome": "UNKNOWN",
            "severity_signal": 0,
        },
    ),
]
for source, name, raw, expected in cases:
    dest = ROOT / source / name
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "raw.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    (dest / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
