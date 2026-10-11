"""Host coordination for bounded real-target remediation acceptance; all evidence retained."""

import json
import time
from datetime import UTC, datetime

from m6_lab_proof import collect_paths
from runtime_acceptance import ROOT


def run(acceptance, capture, command, directory):
    directory.mkdir()
    report = {
        "status": "RUNNING",
        "source_digest": acceptance.rc["source_digest"],
        "scope": "CONTROLLED_LAB_REAL_HTTP_POSTGRES_SURICATA_WAZUH",
        "checks": {},
        "phases": [],
    }

    def save():
        (directory / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    def phase(name, data=None, *, expected=0, timeout=120):
        completed = acceptance.docker(
            *command[1:],
            "run",
            "--rm",
            "--no-deps",
            "runner",
            "python",
            "tools/m6_lab_acceptance.py",
            capture.relative_to(ROOT).as_posix(),
            name,
            "--data",
            json.dumps(data or {}),
            expected=expected,
            timeout=timeout,
        )
        value = json.loads(completed.stdout)
        index = len(report["phases"])
        path = f"phase-{index:03d}-{name}.json"
        (directory / path).write_text(json.dumps(value, indent=2), encoding="utf-8")
        report["phases"].append(
            {"phase": name, "data": data or {}, "exit_code": completed.returncode, "result": path}
        )
        save()
        return value

    def check(name, condition, detail):
        report["checks"][name] = {"status": "PASS" if condition else "FAIL", "detail": detail}
        save()
        assert condition, name

    proof_number = 0

    def proof(start, *, offline=False):
        nonlocal proof_number
        deadline = time.monotonic() + 45
        while True:
            phase("traffic")
            time.sleep(6)
            folder = directory / f"path-proof-{proof_number:03d}"
            proof_number += 1
            measured = collect_paths(folder, start)
            if offline:
                return (folder / "proof.json").relative_to(ROOT).as_posix()
            stats = measured["suricata"]["stats"] or {}
            detail = (measured["wazuh"]["agent_status"] or {}).get("data", {})
            after = datetime.fromisoformat(start).timestamp() + 1
            if (
                all(measured["path_coverage"].values())
                and all(p["running"] for p in measured["processes"].values())
                and datetime.fromisoformat(stats.get("timestamp", start)).timestamp() >= after
                and int(detail.get("lastKeepAlive", 0)) >= after
            ):
                return (folder / "proof.json").relative_to(ROOT).as_posix()
            if time.monotonic() > deadline:
                raise AssertionError("real path/sensor coverage unavailable; no synthetic replacement")

    def health():
        path = proof(datetime.now(UTC).isoformat())
        samples = phase("health", {"proof": path})
        assert all(s["status"] == "HEALTHY" for s in samples)
        return path

    def apply(case, prior=None, before=None, ttl=60):
        phase("plan", {"case": case, "prior": prior, "before": before, "ttl": ttl})
        value = phase("execute")
        assert value["receipt"]["execution_outcome"] == "EXECUTION_SUCCESS", value
        return value

    def verify(action, case, *, offline=False, existing=None):
        started = existing or phase("verify-start", {"action_id": action, "case": case})
        measured = proof(started["window_start"], offline=offline)
        return phase("verify-finish", {**started, "proof": measured})

    def release(action, case):
        state = phase("target")["state"]
        if state["owner"] == "zhiyu-lab:" + action:
            return apply(case, prior=action)
        assert not state["restricted"], "foreign owner must be preserved"
        return None

    save()
    try:
        phase("init")
        health()
        initial = phase("target")
        phase("plan", {"case": "a05-loss", "ttl": 60})
        lost = phase("execute", {"crash": True}, expected=71)
        changed = phase("target")
        check(
            "a05_real_mutation_before_receipt_commit",
            changed["state"]["restricted"] and changed["mutations"] == initial["mutations"] + 1,
            {"process_exit": lost, "target": changed},
        )
        remaining = (datetime.fromisoformat(lost["lease"]["expires_at"]) - datetime.now(UTC)).total_seconds()
        if remaining > 0:
            time.sleep(remaining + 0.1)
        reconciled = phase("reconcile", {"attempt_id": lost["attempt_id"]})
        receipt = reconciled["receipt"]
        check(
            "A05",
            receipt["execution_outcome"] == "EXECUTION_SUCCESS"
            and receipt["output"]["reconciliation"] == "CONFIRMED_APPLIED"
            and not receipt["output"]["mutation_replayed"]
            and reconciled["target"]["mutations"] == changed["mutations"],
            reconciled,
        )
        duplicate = phase("duplicate", {"action_id": receipt["action_id"]})
        stale_worker = phase(
            "stale-worker",
            {
                "attempt_id": lost["attempt_id"],
                "generation": lost["lease"]["generation"],
            },
        )
        check("a06_stale_worker_fenced", stale_worker["stale_ack"] == "FENCED", stale_worker)
        check(
            "a06_duplicate_no_second_mutation",
            duplicate["target"]["mutations"] == changed["mutations"],
            duplicate,
        )
        old_owned = changed["state"]
        release(receipt["action_id"], "a06-legitimate-compensation")
        owner_b = apply("a06-other-owner")
        phase("plan", {"case": "a06-stale-compensation", "prior": receipt["action_id"], "before": old_owned})
        refused = phase("execute")
        check(
            "A06",
            refused["receipt"]["execution_outcome"] == "EXECUTION_UNKNOWN"
            and refused["target"]["mutations"] == owner_b["target"]["mutations"]
            and refused["target"]["state"]["owner"] == owner_b["target"]["state"]["owner"],
            refused,
        )
        # A failed ownership comparison is deliberately left for reconciliation. It cannot change state.
        time.sleep(21)
        release(owner_b["receipt"]["action_id"], "a06-release-owner-b")
        health()
        active = apply("a07-active")
        action = active["receipt"]["action_id"]
        positive = verify(action, "a07-contained")
        check(
            "a07_all_three_dimensions",
            positive["verification"]["status"] == "PASS"
            and positive["verification"]["objective_type"] == "CONTAINMENT",
            positive,
        )
        release(action, "a07-positive-cleanup")
        health()
        action = apply("a07-business-control")["receipt"]["action_id"]
        acceptance.docker(
            *command[1:],
            "exec",
            "-T",
            "containment-target",
            "python",
            "-c",
            "from pathlib import Path; Path('/tmp/business-down').touch()",
        )
        business = verify(action, "a07-business-outage")
        acceptance.docker(
            *command[1:],
            "exec",
            "-T",
            "containment-target",
            "python",
            "-c",
            "from pathlib import Path; Path('/tmp/business-down').unlink()",
        )
        check(
            "a07_business_unavailable",
            business["verification"]["status"] == "FAIL"
            and business["verification"]["business_status"] == "FAIL",
            business,
        )
        release(action, "a07-business-cleanup")
        health()
        action = apply("a07-reachable-control")["receipt"]["action_id"]
        release(action, "a07-remove-control")
        reachable = verify(action, "a07-attack-reachable")
        check(
            "a07_attack_still_reachable",
            reachable["verification"]["status"] == "FAIL"
            and reachable["verification"]["security_status"] == "FAIL",
            reachable,
        )
        health()
        action = apply("a07-offline-control")["receipt"]["action_id"]
        acceptance.docker(*command[1:], "stop", "wazuh-agent")
        missing = verify(action, "a07-sensor-offline", offline=True)
        acceptance.docker(*command[1:], "start", "wazuh-agent")
        check("a07_sensor_offline", missing["verification"]["status"] == "INCONCLUSIVE", missing)
        check(
            "A07",
            True,
            {
                "positive": "a07_all_three_dimensions",
                "negative": ["a07_business_unavailable", "a07_attack_still_reachable", "a07_sensor_offline"],
            },
        )
        health()
        release(action, "a07-offline-cleanup")
        temporary = apply("a09-ttl")
        action = temporary["receipt"]["action_id"]
        reviews = phase("ttl-reviews", {"action_id": action})
        active_review = next(r for r in reviews if r["policy"]["start_after_seconds"] == 0)
        expiry_review = next(r for r in reviews if r["policy"]["start_after_seconds"] > 0)
        before = verify(action, "a09-active", existing=active_review)
        assert before["verification"]["status"] == "PASS"
        # Target native expiry must work while the controller database is physically stopped.
        acceptance.docker(*command[1:], "stop", "postgres")
        stopped = json.loads(
            acceptance.docker(*command[1:], "ps", "--all", "--format", "json", "postgres").stdout
        )
        assert stopped["State"] == "exited"
        deadline = datetime.fromisoformat(expiry_review["window_start"])
        while datetime.now(UTC) < deadline:
            time.sleep(min(5, max(0.1, (deadline - datetime.now(UTC)).total_seconds())))
        expired = phase("target")
        still_stopped = json.loads(
            acceptance.docker(*command[1:], "ps", "--all", "--format", "json", "postgres").stdout
        )
        assert still_stopped["State"] == "exited"
        acceptance.docker(*command[1:], "start", "postgres")
        for _ in range(30):
            status = json.loads(acceptance.docker(*command[1:], "ps", "--format", "json", "postgres").stdout)
            if status.get("Health") == "healthy":
                break
            time.sleep(2)
        else:
            raise AssertionError("database did not recover")
        after = verify(action, "a09-expired", existing=expiry_review)
        check(
            "A09",
            not expired["state"]["restricted"]
            and expired["expirations"] > temporary["target"]["expirations"]
            and after["verification"]["status"] == "FAIL"
            and after["incident_status"] != "CLOSED"
            and set(before["verification"]["evidence_ids"]).isdisjoint(after["verification"]["evidence_ids"]),
            {"native_expiry_database_stopped": expired, "before": before, "after": after},
        )
        health()
        detection_prepared = phase("critical-detection-prepare")
        background = phase("background", timeout=600)
        saturation_proof = health()
        detection = phase("critical-detection-finish", {"proof": saturation_proof})
        critical = apply("a11-critical")
        started = time.monotonic()
        recovery = verify(critical["receipt"]["action_id"], "a11-recovery")
        final = phase("snapshot")
        check(
            "A11",
            background["queue"]["classes"]["BACKGROUND"]["queue_depth"] >= 1000
            and recovery["verification"]["status"] == "PASS"
            and final["valid_running_leases"].get("BACKGROUND", 0) >= 1
            and detection["real_alert_ingest"]["accepted"] > 0
            and detection["grouped"]["processed"] > 0
            and final["queue"]["classes"]["SECURITY_CRITICAL"]["completed"] > 0
            and final["queue"]["dropped"] == 0,
            {
                "background": background,
                "critical_detection_prepared": detection_prepared,
                "critical_detection": detection,
                "critical": critical,
                "recovery": recovery,
                "recovery_latency_seconds": time.monotonic() - started,
                "final": final,
            },
        )
        release(critical["receipt"]["action_id"], "a11-cleanup")
        final = phase("snapshot")
        check("audit_integrity", final["audit_valid"], final)
        database = phase("database-snapshot")
        check("high_risk_autonomous_execution_zero", database["high_risk_automatic_actions"] == 0, database)
        report["high_risk_automatic_actions"] = database["high_risk_automatic_actions"]
        report["status"] = "PASS"
    except Exception as error:
        report["status"], report["error"] = "FAIL", acceptance.sanitize(str(error))
        raise
    finally:
        save()
    return report
