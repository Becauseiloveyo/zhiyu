"""Recheck preserved real-sensor evidence before admitting Gate B."""

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from m6_jsonl import complete_records

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/m6-runtime"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    checks, hashes, captures = {}, {}, {}

    def retain(path):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[path.relative_to(ROOT).as_posix()] = digest
        return digest

    for name in ["sensor-007", "sensor-008"]:
        directory = EVIDENCE / name
        manifest, result = read(directory / "manifest.json"), read(directory / "result.json")
        assert result["status"] == "PASS" and result["data_origin"] == "OBSERVED"
        for filename, expected in manifest["files"].items():
            assert retain(directory / filename) == expected["sha256"]
        source_records = {
            source: {
                line: (raw, value)
                for line, raw, value in complete_records((directory / file).read_bytes())[0]
            }
            for source, file in [("suricata", "eve.json"), ("wazuh", "alerts.json")]
        }
        for lineage in result["lineage"]:
            raw, value = source_records[lineage["source"]][lineage["raw_line"]]
            assert hashlib.sha256(raw).hexdigest() == lineage["sha256"]
            assert datetime.fromisoformat(value["timestamp"]) == datetime.fromisoformat(
                lineage["source_timestamp"]
            )
            assert all(
                lineage[key]
                for key in [
                    "collector_id",
                    "origin_event_id",
                    "raw_ref",
                    "ingested_at",
                    "parser_version",
                    "mapping_version",
                ]
            )
            service = "suricata" if lineage["source"] == "suricata" else "wazuh-agent"
            assert lineage["provenance_group"].endswith(manifest["containers"][service]["id"])
        assert len(result["lineage"]) == result["snapshot"]["counts"]["normalized_events"]
        assert result["cross_source_groups"] and result["snapshot"]["counts"]["incidents"] > 0
        assert result["snapshot"]["audit_chain_valid"]
        captures[name] = {
            "environment_id": result["environment_id"],
            "counts": result["snapshot"]["counts"],
            "event_types": result["observed_event_types"],
            "cross_source_groups": [g["group_id"] for g in result["cross_source_groups"]],
            "containers": manifest["containers"],
        }
        for file in [
            "manifest.json",
            "result.json",
            "traffic.stdout",
            "agent-registration.stdout",
            "wazuh-version.stdout",
            "suricata-version.stdout",
        ]:
            retain(directory / file)
    counts = Counter()
    for capture in captures.values():
        counts.update(capture["event_types"])
    required = {"suricata." + t for t in ["flow", "dns", "http", "tls", "alert"]} | {"wazuh.alert"}
    assert required <= counts.keys()
    checks["real_sources_all_event_types_and_lineage"] = "PASS"
    initial_path = EVIDENCE / "sensor-008-health-initial/verification.json"
    initial = read(initial_path)
    assert initial["verification"]["status"] == "PASS"
    assert len(initial["response"]["executions"]) == 3
    assert all(
        r["execution_outcome"] == "EXECUTION_SUCCESS" and r["side_effect"] == "NONE"
        for r in initial["response"]["executions"]
    )
    retain(initial_path)
    checks["authorized_read_only_detection_verification"] = "PASS"
    fault_path = EVIDENCE / "gate-a-002/result.json"
    fault = read(fault_path)
    assert fault["status"] == "PASS" and fault["stale_elapsed_seconds"] >= 131
    assert len(fault["checks"]) == 12
    for name, check in fault["checks"].items():
        assert check["status"] == "PASS"
        checks[name] = "PASS"
    for path in sorted((EVIDENCE / "gate-a-002").rglob("*")):
        if path.is_file():
            retain(path)
        if path.name == "proof.json":
            proof = read(path)
            for source, filename in [("suricata", "eve.json"), ("wazuh", "alerts.json")]:
                assert retain(path.parent / filename) == proof[source]["raw_sha256"]
    report = {
        "gate": "A",
        "status": "PASS",
        "scope": "CONTROLLED_LAB",
        "validated_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "captures": captures,
        "sha256": hashes,
        "windows_wazuh_real_runtime": "NOT_RUN",
        "production": "NOT_RUN",
        "high_risk_automatic_actions": 0,
        "limitations": [
            "Read-only DETECTION only",
            "Time-bounded observations, not present or sustained health",
            "Public disposable Lab credentials in retained raw EVE",
            "Earlier failures retained and excluded from PASS counts",
        ],
    }
    output = EVIDENCE / "gate-a-acceptance.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps({"status": report["status"], "checks": len(checks), "hashed_evidence_files": len(hashes)})
    )


if __name__ == "__main__":
    main()
