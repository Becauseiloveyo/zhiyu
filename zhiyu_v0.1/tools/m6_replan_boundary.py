"""Two actual independent verification rounds: repeated observations stop replanning."""

import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from ai_fixture import snapshot
from m6_ai_evaluation import save
from response_fixture import prepare
from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.core.config import settings
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import ActionRow, IncidentRow, PlanRow, SensorHealthRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.session import get_engine
from zhiyu.db.verification_replan import ReplanDecisionRow
from zhiyu.domain.contracts import ActionRequest
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy
from zhiyu.response.worker import ResponseWorker
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.replan import DeterministicReplanner, ReplanBudget, activate
from zhiyu.verification.runtime import VerificationService, default_spec


def run(target, source):
    engine = get_engine()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    env = "m3-m6-no-new-evidence-" + stamp.lower()
    destination = Path("/safety-output") / ("replan-" + stamp + ".json")
    principal = next(p for p in settings.service_tokens.values() if p.principal_id == "compose-smoke")
    principal = principal.model_copy(update={"environment_ids": principal.environment_ids | {env}})
    seed = prepare(engine, env, principal, target=target, source=source, port=8081)
    with Session(engine) as db:
        plan = DeterministicResponsePlanner(db, PlannerPolicy(max_replans=2)).create(
            env, seed["incident_id"], expected_version=2, scope_id="scope-lab-web", principal=principal
        )
    activate(engine, env, plan.plan_id, principal, ReplanBudget(max_replans=2))
    current_plan = plan.plan_id
    rounds = []
    for index in range(2):
        with Session(engine) as db:
            row = db.get(PlanRow, current_plan)
            task_ids = [task["task_id"] for task in row.tasks]
        executions = [ResponseWorker(engine).tick(env, principal) for _ in task_ids]
        assert all(r["result"]["execution_outcome"] == "EXECUTION_SUCCESS" for r in executions)
        with Session(engine) as db:
            action = db.scalar(
                select(ActionRow)
                .where(ActionRow.environment_id == env, ActionRow.task_id.in_(task_ids))
                .order_by(ActionRow.created_at)
            )
            receipt = db.scalar(
                select(ActionResultRow)
                .join(ActionDispatchRow)
                .where(ActionDispatchRow.action_id == action.action_id)
            )
            sensor_ids = list(
                db.scalars(select(SensorHealthRow.sensor_id).where(SensorHealthRow.environment_id == env))
            )
            specification = default_spec(contract_from(action, ActionRequest), sensor_ids)
            specification.checks[1].assertions[0].expected = 201
            result_id = receipt.attempt_id
        time.sleep(1.1)  # Honour the actual scope's 1 Hz probe budget.
        service = VerificationService(engine)
        identifier = service.create(env, result_id, specification, principal)
        observations = [
            service.run_claim(env, service.claim(env, principal, spec_id=identifier), principal)
            for _ in range(3)
        ]
        result = VerificationEngine(engine).decide(env, identifier, principal)
        assert result.status == "FAIL"
        decision = DeterministicReplanner(engine).handle(env, result.verification_id, principal)
        rounds.append(
            {
                "round": index + 1,
                "plan_id": current_plan,
                "executions": executions,
                "observations": observations,
                "verification": result.model_dump(mode="json"),
                "replan": decision,
            }
        )
        save(destination, {"status": "RUNNING", "environment": env, "rounds": rounds})
        if index == 0:
            assert decision["status"] == "CREATED"
            current_plan = decision["new_plan_id"]
        else:
            assert (
                decision["status"] == "REPLAN_EXHAUSTED" and "no new semantic evidence" in decision["reason"]
            )
            assert decision["new_plan_id"] is None
    final = snapshot(engine, env)
    with Session(engine) as db:
        assert db.get(IncidentRow, seed["incident_id"]).status == "HUMAN_REVIEW"
        fingerprints = [
            db.get(ReplanDecisionRow, r["verification"]["verification_id"]).evidence_fingerprint
            for r in rounds
        ]
    assert fingerprints[0] == fingerprints[1]
    assert final["high_risk_executions"] == 0 and final["audit_valid"]
    save(
        destination,
        {
            "status": "PASS",
            "environment": env,
            "data_origin": "SYNTHETIC_AUTHENTICATED_LAB",
            "actual_http_rounds": 2,
            "scope": "HTTP 200 fails required 201; actual read-only checks, not an outage",
            "rounds": rounds,
            "semantic_evidence_fingerprints": fingerprints,
            "snapshot": final,
        },
    )
    print("PASS: actual two-round no-new-evidence replan boundary", flush=True)


if __name__ == "__main__":
    run(*sys.argv[1:3])
