"""Isolated Docker fault injections over the same synthetic Incident -> Action chain."""

import json
from datetime import timedelta

from response_fixture import SCOPE, fixture_principal, prepare
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import DomainError
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import CapabilityHealthRow, CapabilityRow, ResourceRow, WorkerLeaseRow
from zhiyu.db.response_authority import CapabilityConfigRow
from zhiyu.db.session import get_engine
from zhiyu.domain.contracts import CapabilityManifest
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.executors import ExecutorRegistry
from zhiyu.response.gateway import ActionGateway
from zhiyu.response.planner import DeterministicResponsePlanner
from zhiyu.response.scheduler import TaskScheduler


class ObservedRegistry(ExecutorRegistry):
    calls = 0

    def resolve(self, action):
        original, owner = super().resolve(action), self

        class Observed:
            version = original.version

            def execute(self, value):
                owner.calls += 1
                return original.execute(value)

        return Observed()


def run():
    engine = get_engine()
    reports = {}
    for case in (
        "correct_scope",
        "wrong_target",
        "wrong_environment",
        "mutated_digest",
        "offline_capability",
        "r3_risk",
        "expired_worker",
        "duplicate_action",
    ):
        env = "m3-negative-" + case
        principal = fixture_principal(env)
        fixture = prepare(engine, env, principal)
        with Session(engine) as db:
            DeterministicResponsePlanner(db).create(
                env, fixture["incident_id"], expected_version=2, scope_id=SCOPE, principal=principal
            )
        with Session(engine) as db:
            lease = TaskScheduler(db).claim(env, principal)
        task_id = lease["task_id"]
        with Session(engine) as db:
            decision = AuthorizationService(db).authorize_task(
                env, task_id, generation=1, principal=principal
            )
        assert decision.outcome == "ALLOW"
        saved_risk = None
        with Session(engine) as db, db.begin():
            if case == "wrong_target":
                db.get(ResourceRow, ("target-a", env)).binding_version += 1
            elif case == "offline_capability":
                db.get(
                    CapabilityHealthRow, ("collect_resource_context", "1.0.0", env, "response")
                ).status = "OFFLINE"
            elif case == "expired_worker":
                row = db.get(WorkerLeaseRow, lease["lease_id"])
                row.expires_at = row.acquired_at + timedelta(microseconds=1)
            elif case == "r3_risk":
                # Fault injection in this fresh acceptance database only. No high-risk executor exists.
                row = db.get(CapabilityRow, ("collect_resource_context", "1.0.0"))
                config = db.get(CapabilityConfigRow, (row.capability_id, row.version))
                saved_risk = row.base_risk, config.definition_hash
                row.base_risk = "R3"
                config.definition_hash = canonical_hash(
                    contract_from(row, CapabilityManifest).model_dump(mode="json")
                )
        registry = ObservedRegistry(engine)
        service = ActionGateway(engine, registry)
        try:
            try:
                result = service.dispatch(
                    "wrong-environment" if case == "wrong_environment" else env,
                    task_id,
                    1,
                    decision.authorization_id,
                    principal,
                    submitted_digest="f" * 64 if case == "mutated_digest" else decision.action_digest,
                )
            except DomainError as error:
                result = {"execution_outcome": "REJECTED", "error_code": error.code}
            if case == "duplicate_action":
                repeat = service.dispatch(
                    env,
                    task_id,
                    1,
                    decision.authorization_id,
                    principal,
                    submitted_digest=decision.action_digest,
                )
                assert repeat["disposition"] == "DUPLICATE" and repeat["attempt_id"] == result["attempt_id"]
                result["replay_disposition"] = repeat["disposition"]
            expected_calls = 1 if case in {"correct_scope", "duplicate_action"} else 0
            assert registry.calls == expected_calls, (case, registry.calls)
            assert result["execution_outcome"] in (
                {"EXECUTION_SUCCESS"} if expected_calls else {"DENIED", "REJECTED", "STALE"}
            ), (case, result)
            reports[case] = {"status": "PASS", "executor_calls": registry.calls, "result": result}
        finally:
            if saved_risk:
                with Session(engine) as db, db.begin():
                    db.get(CapabilityRow, ("collect_resource_context", "1.0.0")).base_risk = saved_risk[0]
                    db.get(
                        CapabilityConfigRow, ("collect_resource_context", "1.0.0")
                    ).definition_hash = saved_risk[1]
    print(json.dumps(reports))


if __name__ == "__main__":
    run()
