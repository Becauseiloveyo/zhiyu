"""Read-only acceptance digest of persisted runs, canonical rows and pinned artifacts."""

import hashlib
import json
from datetime import UTC, datetime

from m9_demo import load
from m9_lab_adapter import EVIDENCE, ROOT
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.db.demo_control import DemoRunRow, DemoStepRow
from zhiyu.db.models import ActionRow, AuthorizationDecisionRow, EventRow, ModelRunRow, VerificationResultRow
from zhiyu.product.demo_contracts import TEMPLATES, source_environment
from zhiyu.product.snapshots import digest


def main():
    engine, _, config = load()
    results = []
    with Session(engine) as db:
        for run in db.scalars(select(DemoRunRow).order_by(DemoRunRow.created_at)):
            env = source_environment(run.run_id)
            folder = EVIDENCE / run.run_id
            counts = {
                name: db.scalar(select(func.count()).select_from(model).where(model.environment_id == env))
                for name, model in (
                    ("events", EventRow),
                    ("actions", ActionRow),
                    ("model_runs", ModelRunRow),
                    ("verifications", VerificationResultRow),
                )
            }
            high_risk = db.scalar(
                select(func.count())
                .select_from(AuthorizationDecisionRow)
                .join(ActionRow, ActionRow.action_id == AuthorizationDecisionRow.action_id)
                .where(
                    ActionRow.environment_id == env,
                    AuthorizationDecisionRow.outcome == "ALLOW",
                    AuthorizationDecisionRow.assessed_risk > "R2",
                )
            )
            checks = {
                "completed": run.status == "COMPLETED",
                "expected_outcome": run.actual_outcome == TEMPLATES[run.scenario_id]["expected"],
                "real_sensor_events": counts["events"] > 0,
                "high_risk_autonomous_execution_zero": high_risk == 0,
            }
            step = db.get(DemoStepRow, (run.run_id, 3))
            archive = ROOT / "artifacts/v0.9/recordings" / (run.run_id + ".json")
            checks["pinned_archive"] = bool(
                step
                and step.status == "COMPLETED"
                and archive.exists()
                and hashlib.sha256(archive.read_bytes()).hexdigest() == step.output.get("artifact_sha256")
            )
            if checks["pinned_archive"]:
                snapshot = json.loads(archive.read_bytes())
                checks["snapshot_facts_hash"] = digest(snapshot["facts"]) == snapshot["content_sha256"]
            if run.scenario_id == "B":
                checks["rejected_has_no_action"] = counts["actions"] == 0
            elif run.scenario_id == "A":
                ai = (
                    json.loads((folder / "analyze.json").read_text())
                    if (folder / "analyze.json").exists()
                    else {}
                )
                checks["real_model_grounded_shadow_proposal"] = (
                    run.model_source == "REAL_LOCAL_MODEL"
                    and ai.get("analysis", {}).get("status") == "REFERENCE_GROUNDED"
                    and ai.get("proposal", {}).get("status") == "SHADOW"
                )
            if run.scenario_id == "D":
                verified = (
                    json.loads((folder / "verify.json").read_text())
                    if (folder / "verify.json").exists()
                    else {}
                )
                checks["bounded_replan"] = (
                    verified.get("replan", {}).get("status") == "CREATED"
                    and verified.get("replan", {}).get("replan_count") == 1
                )
            clean = (
                json.loads((folder / "cleanup.json").read_text())
                if (folder / "cleanup.json").exists()
                else None
            )
            results.append(
                {
                    "run_id": run.run_id,
                    "scenario": run.scenario_id,
                    "status": run.status,
                    "actual_outcome": run.actual_outcome,
                    "model_source": run.model_source,
                    "counts": counts,
                    "checks": checks,
                    "scenario_acceptance": "PASS" if all(checks.values()) else "NOT_PASS",
                    "cleanup_status": run.cleanup_status,
                    "zero_owned_residual": bool(clean is not None and not any(clean["after"].values())),
                    "predecessor_id": run.predecessor_id,
                }
            )
    passed = sorted({r["scenario"] for r in results if r["scenario_acceptance"] == "PASS"})
    report = {
        "as_of": datetime.now(UTC).isoformat(),
        "scope": "CONTROLLED_LAB",
        "passed_scenarios": passed,
        "all_A_to_E_pass": passed == list("ABCDE"),
        "milestone": "NOT PASS",
        "runs": results,
        "note": "Scenario checks do not replace browser/reset/full-regression/package acceptance.",
    }
    (ROOT / "artifacts/v0.9/demo-live-evidence.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({"passed_scenarios": passed, "runs": len(results), "milestone": report["milestone"]}))


if __name__ == "__main__":
    main()
