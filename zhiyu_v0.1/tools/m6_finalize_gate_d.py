"""Seal completed Gate D evidence only after all actual measurements are reviewed."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from m6_performance_report import DIRECTORY
from m6_performance_report import main as render_performance
from runtime_acceptance import ROOT


def read(name):
    return json.loads((DIRECTORY / name).read_text(encoding="utf-8"))


def main():
    output = DIRECTORY.parent / "gate-d-acceptance.json"
    assert not output.exists(), "do not rewrite sealed acceptance"
    checks = {}

    def check(name, condition):
        assert condition, name
        checks[name] = "PASS"

    source = hashlib.sha256(
        b"".join(
            p.relative_to(ROOT / "src").as_posix().encode() + p.read_bytes()
            for p in sorted((ROOT / "src").rglob("*.py"))
        )
    ).hexdigest()
    prerequisite = json.loads((DIRECTORY.parent / "gate-c-acceptance.json").read_text())
    check("gate_c_completed", prerequisite["status"] == "PASS_CONTROLLED_LAB")
    check(
        "event_sources",
        all(read(name)["source_digest"] == source for name in ["events.json", "events-streaming.json"]),
    )
    events = read("events.json")["results"][:2] + [read("events-streaming.json")["result"]]
    for expected, row in zip([1000, 10000, 100000], events, strict=True):
        metrics = row["metrics"]
        check(
            f"events_{expected}",
            row["status"] == "COMPLETED"
            and row["events"]
            == metrics["normalized_event_count"]
            == metrics["grouped_event_count"]
            == expected
            and metrics["pending_event_count"] == metrics["adapter_error_count"] == 0
            and row["audit"]["audit_valid"],
        )
    load_totals = {}
    for kind in ["response", "verification"]:
        report = read(kind + ".json")
        check(kind + "_source", report["source_digest"] == source)
        check(kind + "_completed", report["status"] == "COMPLETED_MEASUREMENT")
        load_totals[kind] = []
        for requested, row in zip([100, 1000, 10000], report["results"], strict=True):
            expected = requested if kind == "response" else ((requested + 2) // 3) * 3
            check(f"{kind}_{requested}", row["status"] == "COMPLETED" and row["actual"] == expected)
            for chunk in row["chunks"]:
                audit = chunk["audit"]
                check(
                    "audit_" + chunk["environment_id"],
                    audit["audit_valid"]
                    and audit["duplicate_logical_actions"] == 0
                    and set(audit["side_effects"]) <= {"NONE"},
                )
                if kind == "verification":
                    assert chunk["fail"] == chunk["replans_created"] == 1
                    assert chunk["pass"] + chunk["fail"] == chunk["verification_runs"]
                    assert audit["states"]["verification_checks"] == {"SUCCEEDED": chunk["check_jobs"]}
                else:
                    assert audit["states"]["tasks"]["SUCCEEDED"] == chunk["tasks_executed"]
            load_totals[kind].append(
                {
                    "requested": requested,
                    "actual": expected,
                    "intentional_unexecuted_tasks": row["intentional_unexecuted_tail_tasks"],
                }
            )
    soak = read("soak.json")
    check("soak_source", soak["source_digest"] == source)
    check("actual_30_minutes", soak["status"] == "COMPLETED" and soak["elapsed_seconds"] >= 1800)
    check(
        "soak_cycles",
        len(soak["cycles"]) >= 30
        and all(
            row["audit_valid"]
            and row["verification"] == "PASS"
            and row["ai_actions"] == row["high_risk_actions"] == 0
            for row in soak["cycles"]
        ),
    )
    check("soak_no_stuck_tasks", soak["final_metrics"]["expired_running_tasks"] == 0)
    ai = read("ai-load.json")
    check("ai_source", ai["source_digest"] == source)
    check("ai_completed", ai["status"] == "COMPLETED_MEASUREMENT" and ai["provider_calls"] == 16)
    check("ai_budget", ai["budget_exhaustion"]["status"] == "PASS")
    check("ten_sequential_metered_responses", ai["groups"][0]["metered_responses"] == 10)
    for size, group in zip([10, 2, 4], ai["groups"], strict=True):
        check(
            "ai_" + group["kind"],
            len(group["results"]) == size
            and all(row["audit_valid"] and row["executor_calls"] == 0 for row in group["results"]),
        )
    database = read("final-database-snapshot.json")
    check("all_final_audit_chains", bool(database["audit_chains"]) and all(database["audit_chains"].values()))
    check("no_high_risk_execution", database["high_risk_automatic_actions"] == 0)
    check("database_tables", len(database["tables"]) == 72)
    check("runtime_provenance", read("runtime-provenance.json")["status"] == "PASS")
    queues = read("load-queue-review.json")
    check("queues_accounted", queues["status"] == "PASS_ACCOUNTED_BACKLOG")
    render_performance()
    resources = read("resource-review.json")
    for phase in ["soak", "events", "events-streaming", "response", "verification", "ai"]:
        row = resources[phase]
        check(
            "resources_" + phase,
            row["samples"] > 0
            and row["all_observed_running"]
            and not row["oom_observed"]
            and row["restart_counts_observed"] == [0]
            and row["metrics_errors"] == 0,
        )
    state = json.loads((ROOT.parent / ".work/m6-load-state.json").read_text())
    secrets = [
        state["token"],
        state["password"],
        Path(state["env"]["ZHIYU_MODEL_KEY_FILE"]).read_text().strip(),
    ]
    for path in DIRECTORY.rglob("*"):
        if path.is_file():
            content = path.read_bytes()
            assert all(value.encode() not in content for value in secrets if value), path.name
    check("known_private_credentials_absent", True)
    summary = {
        "gate": "D",
        "status": "PASS_CONTROLLED_LAB",
        "reviewed_at": datetime.now(UTC).isoformat(),
        "source_digest": source,
        "checks": checks,
        "event_levels": [1000, 10000, 100000],
        "loads": load_totals,
        "soak_seconds": soak["elapsed_seconds"],
        "provider_calls": 16,
        "queue_review": "gate-d-001/load-queue-review.json",
        "final_audit_chains": len(database["audit_chains"]),
        "high_risk_automatic_actions": 0,
        "limitations": [
            "Synthetic workload, real PostgreSQL/read-only executors/HTTP/local model; no production SLA.",
            "Response monitor stopped before final workload completion; uncovered tail explicitly retained.",
            "Exact model queue delay not separately measured; provider time includes queue and inference.",
            "No Outbox consumer; durable backlog and intentional tail/replan tasks are not hidden.",
            "Single-host bounded load; 30-minute soak does not establish long-term leak freedom.",
            "Initial 66k budget stop, late 73k continuation and pilot credential failure retained.",
        ],
    }
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report = read("result.json")
    report.update(status="PASS_CONTROLLED_LAB", finished_at=summary["reviewed_at"], acceptance=output.name)
    (DIRECTORY / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    render_performance()
    paths = sorted(p for p in DIRECTORY.rglob("*") if p.is_file()) + [output]
    hashes = {
        p.relative_to(DIRECTORY.parent).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
    }
    (DIRECTORY.parent / "gate-d-evidence-sha256.json").write_text(
        json.dumps(hashes, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": summary["status"], "evidence_files": len(hashes)}))


if __name__ == "__main__":
    main()
