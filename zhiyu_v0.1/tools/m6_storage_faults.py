"""PostgreSQL error injection at evidence persistence, never fill the host disk."""

import json
import sys
from pathlib import Path

from ai_fixture import snapshot, spec
from response_fixture import prepare
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from zhiyu.core.config import settings
from zhiyu.db.models import EvidenceRow
from zhiyu.db.session import get_engine
from zhiyu.domain.contracts import VerificationSpec
from zhiyu.response.planner import DeterministicResponsePlanner
from zhiyu.response.worker import ResponseWorker
from zhiyu.verification.runtime import VerificationService


def main():
    engine = get_engine()
    env = "m3-m6-storage"
    principal = next(p for p in settings.service_tokens.values() if p.principal_id == "compose-smoke")
    root = Path("/fault-control/storage")
    root.mkdir(exist_ok=False)

    def save(name, value):
        (root / (name + ".json")).write_text(json.dumps(value, default=str, indent=2))

    seed = prepare(engine, env, principal, target=sys.argv[1], source=sys.argv[2], port=8081)
    with Session(engine) as db:
        DeterministicResponsePlanner(db).create(
            env, seed["incident_id"], expected_version=2, scope_id="scope-lab-web", principal=principal
        )
    for _ in range(3):
        assert (
            ResponseWorker(engine).tick(env, principal)["result"]["execution_outcome"] == "EXECUTION_SUCCESS"
        )
    body = spec(engine, env)
    service = VerificationService(engine)
    identifier = service.create(
        env, body["action_result_id"], VerificationSpec.model_validate(body["spec"]), principal
    )
    lease = service.claim(env, principal, spec_id=identifier)
    before = snapshot(engine, env)
    with Session(engine) as db:
        evidence_before = list(
            db.scalars(select(EvidenceRow.evidence_id).where(EvidenceRow.environment_id == env))
        )
    save("before", before)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE FUNCTION m6_test_evidence_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'controlled M6 evidence storage error' USING ERRCODE='53100'; END $$"
                )
            )
            connection.execute(
                text(
                    "CREATE TRIGGER m6_test_evidence_fault BEFORE INSERT ON evidence FOR EACH ROW WHEN (NEW.environment_id = 'm3-m6-storage') EXECUTE FUNCTION m6_test_evidence_fault()"
                )
            )
        try:
            service.run_claim(env, lease, principal)
        except DBAPIError as error:
            code = getattr(error.orig, "sqlstate", None)
            assert code == "53100"
            save("write-error", {"sqlstate": code, "mode": "DATABASE_ERROR_INJECTION_NOT_ACTUAL_DISK_FULL"})
        else:
            raise AssertionError("evidence write fault did not interrupt persistence")
        after = snapshot(engine, env)
        save("rolled-back", after)
        assert after == before
        with Session(engine) as db:
            assert set(
                db.scalars(select(EvidenceRow.evidence_id).where(EvidenceRow.environment_id == env))
            ) == set(evidence_before)
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP TRIGGER IF EXISTS m6_test_evidence_fault ON evidence"))
            connection.execute(text("DROP FUNCTION IF EXISTS m6_test_evidence_fault()"))
    recovered = service.run_claim(env, lease, principal)
    assert recovered["status"] == "SUCCEEDED" and recovered["assertion"] == "PASS"
    final = snapshot(engine, env)
    assert final["audit_valid"] and final["high_risk_executions"] == 0
    with engine.connect() as connection:
        atomic = connection.scalars(
            text(
                "SELECT o.xmin::text=e.xmin::text FROM verification_observations o JOIN evidence e USING(evidence_id) WHERE e.environment_id=:env"
            ),
            {"env": env},
        ).all()
        assert atomic == [True]
    save("final", final)
    result = {
        "status": "PASS",
        "evidence_write_error_rollback": True,
        "recovery": recovered,
        "observation_evidence_same_transaction": atomic,
        "high_risk_executions": 0,
    }
    save("result", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
