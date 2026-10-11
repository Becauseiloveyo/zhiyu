"""Fixed container phases for the registered disposable Lab. No browser execution inputs.

Uses the existing M6 ingestion, authorization, gateway and verification implementations.
The host owns work files; the runner mounts them read-only and fences each action in PostgreSQL.
"""

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from m6_lab_acceptance import LabAcceptance
from m6_sensor_ingest import ingest
from m6_sensor_verification import record_health, verify
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.ai.analysis import AISituationAnalyzer
from zhiyu.ai.brain import DecisionBrain
from zhiyu.ai.context import ContextManager
from zhiyu.ai.context_policy import ContextBudget, ContextPolicy
from zhiyu.ai.gateway import ModelGateway
from zhiyu.ai.planner import AIPlanner
from zhiyu.ai.policy import AIPolicy
from zhiyu.ai.provider import ProviderConfig
from zhiyu.db.demo_control import DemoRunRow, DemoStepRow
from zhiyu.db.models import ActionRow, EnvironmentRow, ModelRunRow, PlanRow
from zhiyu.product.demo_contracts import WorkItem, source_environment, template_hash
from zhiyu.response.admin import ControlRequest, configure
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.planner import DeterministicResponsePlanner, PlannerPolicy
from zhiyu.response.registry import CapabilityRegistry
from zhiyu.services.incident_lifecycle import transition
from zhiyu.verification.replan import DeterministicReplanner, ReplanBudget, activate

PHASES = {
    "TRIGGER": {"prepare", "analyze", "health", "traffic"},
    "VERIFY": {"health", "traffic", "execute", "verify"},
}


class Phase:
    def __init__(self, work):
        self.work = work
        self.folder = Path("/evidence")
        self.lab = LabAcceptance(self.folder / work.run_id)
        self.engine, self.env = self.lab.engine, source_environment(work.run_id)
        self.actor = self.lab.operator.model_copy(
            update={
                "permissions": self.lab.operator.permissions
                | {"ai:context", "ai:analyze", "ai:plan", "ai:read"}
            }
        )

    def guard(self):
        with Session(self.engine) as db:
            now = db.scalar(select(func.clock_timestamp()))
            run = db.get(DemoRunRow, self.work.run_id)
            step = db.get(DemoStepRow, (self.work.run_id, self.work.position))
            if (
                not run
                or not step
                or run.cancel_requested
                or run.status != "RUNNING"
                or (
                    run.lease_owner != self.work.lease_owner
                    or run.lease_until <= now
                    or run.deadline <= now
                    or step.generation != self.work.generation
                    or step.status != "STARTED"
                    or run.template_sha256 != template_hash(self.work.scenario_id)
                )
            ):
                raise RuntimeError("demo_phase_fenced")

    def read(self, name):
        return json.loads((self.folder / (name + ".json")).read_text())

    def prepare(self):
        self.guard()
        data = ingest(self.engine, self.env, self.lab.capture)
        if data["status"] != "PASS":
            raise RuntimeError("real_ingest_failed")
        groups = {g["group_id"] for g in data["cross_source_groups"]}
        incident = next(
            i for i in data["snapshot"]["rows"]["incidents"] if groups & set(i["event_group_ids"])
        )
        with Session(self.engine) as db:
            CapabilityRegistry(db).install(self.env, self.actor)
        now = datetime.now(UTC)
        with Session(self.engine) as db, db.begin():
            env = db.get(EnvironmentRow, self.env)
            if env.owner_id != "CONTROLLED-REAL-SENSOR-LAB" or env.deployment_stage != "LAB":
                raise RuntimeError("controlled_lab_identity_required")
            env.autonomy_mode, env.max_auto_risk, env.active_validation = (
                "CONTROLLED_AUTONOMY",
                "R2",
                "ISOLATED_ONLY",
            )
            policy = env.policy_version
        self.guard()
        with Session(self.engine) as db:
            configure(
                db,
                ControlRequest(
                    environment_id=self.env,
                    expected_version=0,
                    policy_version=policy,
                    enabled=True,
                    configuration=ResponsePolicy(worker_sources={self.actor.principal_id: "validation-a"}),
                    valid_from=now - timedelta(seconds=1),
                    valid_until=now + timedelta(hours=1),
                ),
                self.actor,
            )
        with Session(self.engine) as db:
            transition(
                db,
                environment_id=self.env,
                incident_id=incident["incident_id"],
                target="TRIAGED",
                expected_version=incident["state_version"],
                principal=self.actor,
            )
        record_health(self.engine, self.env, self.folder / "initial-health/proof.json", self.actor)
        self.lab.initialize()
        return {
            "incident_id": incident["incident_id"],
            "data_origin": "OBSERVED",
            "cross_source_groups": len(groups),
            "counts": data["snapshot"]["counts"],
        }

    def analyze(self):
        self.guard()
        scenario = self.work.scenario_id
        if scenario == "C":
            return {"model_source": "NONE", "status": "NOT_REQUESTED"}
        scripted = scenario in {"B", "D"}
        os.environ["ZHIYU_LOCAL_MODEL_KEY"] = Path("/run/secrets/model-key").read_text().strip()
        provider = ProviderConfig(
            provider="demo",
            location="LOCAL",
            endpoint="http://model-fault-fixture:8080/v1" if scripted else "http://local-model:8080/v1",
            model=("SCRIPTED_HALLUCINATION" if scenario == "B" else "SCRIPTED_CLAIMS_SUCCESS")
            if scripted
            else "zhiyu-qwen2.5-1.5b",
            revision="CONTROLLED_FAULT_NOT_AI"
            if scripted
            else "gguf-sha256:6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e",
            timeout_seconds=3 if scripted or scenario == "E" else 110,
            max_output_tokens=2400 if scenario == "A" else 1200,
            structured_format="JSON_OBJECT_SCHEMA",
            api_key_env=None if scripted else "ZHIYU_LOCAL_MODEL_KEY",
        )
        gateway = ModelGateway(
            self.engine, AIPolicy(enabled=True, mode="SHADOW", provider_id="demo"), provider
        )
        context = ContextManager(
            self.engine,
            ContextPolicy(
                budget=ContextBudget(
                    context_ttl_seconds=300,
                    max_events=3,
                    max_evidence=3,
                    max_timeline_entries=4,
                    max_chars=16000,
                )
            ),
        ).build(self.env, self.read("prepare")["incident_id"], "scope-lab-web", self.actor)
        if scenario == "E":
            result = DecisionBrain(self.engine, gateway).decide(self.env, context["context_id"], self.actor)
            if result["status"] != "DETERMINISTIC_FALLBACK":
                raise RuntimeError("model_failure_did_not_fallback")
        else:
            analysis = AISituationAnalyzer(self.engine, gateway).analyze(
                self.env, context["context_id"], self.actor
            )
            self.guard()
            proposal = AIPlanner(self.engine, gateway).propose(self.env, analysis["analysis_id"], self.actor)
            result = {"analysis": analysis, "proposal": proposal}
            if scenario == "B" and proposal["status"] != "REJECTED":
                raise RuntimeError("invalid_proposal_not_rejected")
        with Session(self.engine) as db:
            runs = list(db.scalars(select(ModelRunRow.run_id).where(ModelRunRow.environment_id == self.env)))
        return {
            **result,
            "context_id": context["context_id"],
            "model_run_ids": runs,
            "model_source": "SCRIPTED_NOT_AI" if scripted else "REAL_LOCAL_MODEL",
        }

    def execute(self):
        self.guard()
        if self.work.scenario_id == "A":
            ai = self.read("analyze")
            if (
                ai.get("analysis", {}).get("status") != "REFERENCE_GROUNDED"
                or ai.get("proposal", {}).get("status") != "SHADOW"
            ):
                raise RuntimeError("normal_scenario_requires_grounded_real_model_and_valid_shadow_proposal")
        if self.work.scenario_id == "B":
            with Session(self.engine) as db:
                count = db.scalar(
                    select(func.count()).select_from(ActionRow).where(ActionRow.environment_id == self.env)
                )
            if count != 0:
                raise RuntimeError("rejected_proposal_has_actions")
            return {"outcome": "REJECTED", "action_count": 0}
        if self.work.scenario_id == "E":
            ai = self.read("analyze")
            # Existing capacity reservations bind read-only fallback work to the BACKGROUND worker.
            self.lab.operator = self.lab.background
            with Session(self.engine) as db:
                plan = db.get(PlanRow, ai["plan_id"])
                count = len(plan.tasks)
            receipts = []
            for _ in range(count):
                self.guard()
                value = self.lab.execute({})
                if value["receipt"]["execution_outcome"] != "EXECUTION_SUCCESS":
                    raise RuntimeError("fallback_execution_failed")
                receipts.append(value)
            return {"plan_id": ai["plan_id"], "receipts": receipts}
        before = self.lab.target()["state"]
        incident, version = self.lab.incident()
        with Session(self.engine) as db:
            planned = DeterministicResponsePlanner(
                db,
                PlannerPolicy(
                    max_replans=1,
                    policy_version="v09-fixed-lab/" + self.work.scenario_id,
                    lab_target="target-a",
                    lab_parameters={
                        "operation": "contain",
                        "epoch": before["epoch"],
                        "expected_generation": before["generation"],
                        "before_digest": before["digest"],
                        "ttl_seconds": 60,
                        "prior_action_id": None,
                    },
                ),
            ).create(
                self.env, incident, expected_version=version, scope_id="scope-lab-web", principal=self.actor
            )
        plan = {"plan_id": planned.plan_id, "task_id": planned.tasks[0].task_id}
        activate(self.engine, self.env, plan["plan_id"], self.actor, ReplanBudget(max_replans=1))
        self.guard()
        action = self.lab.execute({})
        if action["receipt"]["execution_outcome"] != "EXECUTION_SUCCESS":
            raise RuntimeError("controlled_action_failed")
        started = self.lab.verify_start(
            {"action_id": action["receipt"]["action_id"], "case": "v09-" + self.work.scenario_id}
        )
        return {**plan, **action, **started}

    def verify(self):
        self.guard()
        scenario = self.work.scenario_id
        if scenario == "B":
            return self.execute()
        if scenario == "E":
            value = verify(self.engine, self.env, self.lab.verifier, "v09-E")
            if value["verification"]["status"] != "PASS":
                raise RuntimeError("fallback_verification_not_pass")
            return {**value, "outcome": "FALLBACK"}
        execution = self.read("execute")
        value = self.lab.verify_finish(
            {"spec_id": execution["spec_id"], "proof": str(self.folder / "verification-proof.json")}
        )
        expected = {"A": "PASS", "C": "INCONCLUSIVE", "D": "FAIL"}[scenario]
        verdict = value["verification"]["status"]
        if verdict != expected:
            raise RuntimeError("independent_verification_unexpected_" + verdict)
        self.guard()
        replan = DeterministicReplanner(self.engine).handle(
            self.env, value["verification"]["verification_id"], self.actor
        )
        if scenario == "D" and replan["status"] != "CREATED":
            raise RuntimeError("bounded_replan_missing")
        return {**value, "replan": replan, "outcome": verdict}

    def run(self, name):
        if name not in PHASES.get(self.work.operation, set()):
            raise ValueError("phase_not_allowed_for_committed_step")
        self.guard()
        if name == "traffic":
            return self.lab.traffic()
        if name == "health":
            return self.lab.health(self.folder / "fresh-proof.json")
        return getattr(self, name)()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=sorted(set.union(*PHASES.values())))
    args = parser.parse_args()
    work = WorkItem.model_validate_json(Path("/evidence/work.json").read_text())
    result = Phase(work).run(args.phase)
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
