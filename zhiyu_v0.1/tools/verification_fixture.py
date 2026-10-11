"""Synthetic acceptance helpers. Explicitly NOT a production or real-sensor adapter."""

import json
import sys

from response_fixture import prepare
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from zhiyu.core.config import settings
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import ActionRow, SensorHealthRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.session import get_engine
from zhiyu.domain.contracts import ActionRequest
from zhiyu.repositories.audit import AuditRepository
from zhiyu.verification.runtime import default_spec


def spec_body(engine, env, case="pass", version="1"):
    with Session(engine) as db, db.begin():
        action = db.scalar(
            select(ActionRow)
            .where(ActionRow.environment_id == env, ActionRow.capability_id == "collect_resource_context")
            .order_by(ActionRow.created_at)
        )
        result = db.scalar(
            select(ActionResultRow)
            .join(ActionDispatchRow)
            .where(ActionDispatchRow.action_id == action.action_id)
        )
        sensors = list(db.scalars(select(SensorHealthRow).where(SensorHealthRow.environment_id == env)))
        spec = default_spec(contract_from(action, ActionRequest), [s.sensor_id for s in sensors], version)
        if case == "security":
            spec.checks[0].assertions[0].expected = 999
        elif case == "offline":
            sensors[0].status = "OFFLINE"
        return {
            "environment_id": env,
            "action_result_id": result.attempt_id,
            "spec": spec.model_dump(mode="json"),
        }


def snapshot(engine, env):
    tables = {
        "incidents": "environment_id=:env",
        "plans": "environment_id=:env",
        "tasks": "environment_id=:env",
        "action_requests": "environment_id=:env",
        "action_execution_results": "attempt_id IN (SELECT attempt_id FROM action_dispatches WHERE environment_id=:env)",
        "verification_runtime": "environment_id=:env",
        "verification_checks": "environment_id=:env",
        "verification_observations": "spec_id IN (SELECT spec_id FROM verification_runtime WHERE environment_id=:env)",
        "verification_results": "environment_id=:env",
        "replan_decisions": "verification_id IN (SELECT verification_id FROM verification_results WHERE environment_id=:env)",
        "state_entities": "environment_id=:env",
    }
    with engine.connect() as c:
        rows = {
            name: c.scalars(
                text(
                    "SELECT row_to_json(r) FROM "
                    + name
                    + " r WHERE "
                    + where
                    + " ORDER BY row_to_json(r)::text"
                ),
                {"env": env},
            ).all()
            for name, where in tables.items()
        }
        audit = dict(
            c.execute(
                text(
                    "SELECT operation,count(*) FROM audit_entries WHERE environment_id=:env GROUP BY operation"
                ),
                {"env": env},
            ).all()
        )
        outbox = dict(
            c.execute(
                text("SELECT event_type,count(*) FROM outbox WHERE environment_id=:env GROUP BY event_type"),
                {"env": env},
            ).all()
        )
        auth = c.scalars(
            text(
                "SELECT row_to_json(r) FROM authorization_decisions r WHERE action_id IN (SELECT action_id FROM action_requests WHERE environment_id=:env)"
            ),
            {"env": env},
        ).all()
    with engine.connect() as c:
        high_risk = c.scalar(
            text(
                "SELECT count(*) FROM action_requests a JOIN capabilities c ON c.capability_id=a.capability_id AND c.version=a.capability_version JOIN action_dispatches d ON d.action_id=a.action_id JOIN action_execution_results r ON r.attempt_id=d.attempt_id WHERE a.environment_id=:env AND c.base_risk IN ('R3','R4','R5') AND r.executor <> 'NOT_DISPATCHED'"
            ),
            {"env": env},
        )
        atomic = c.scalars(
            text(
                "SELECT o.xmin::text=e.xmin::text FROM verification_observations o JOIN evidence e USING(evidence_id) WHERE e.environment_id=:env"
            ),
            {"env": env},
        ).all()
    with Session(engine) as db:
        valid = AuditRepository(db).verify_chain(env)
    return {
        "counts": {name: len(items) for name, items in rows.items()},
        "rows": rows,
        "audit": audit,
        "outbox": outbox,
        "audit_valid": valid,
        "authorizations": auth,
        "high_risk_executions": high_risk,
        "observation_evidence_atomic": len(atomic) == 3 and all(atomic),
        "real_sensor_runtime": "NOT_RUN",
    }


if __name__ == "__main__":
    verb, env = sys.argv[1:3]
    if not env.startswith("m3-m4-"):
        raise ValueError("isolated synthetic verification environment required")
    engine = get_engine()
    principal = next(p for p in settings.service_tokens.values() if p.principal_id == "compose-smoke")
    principal.require("verification:write", env)
    if verb == "seed":
        result = prepare(engine, env, principal, target=sys.argv[3], source=sys.argv[4], port=8081)
    elif verb == "spec":
        result = spec_body(engine, env, sys.argv[3])
    elif verb == "snapshot":
        result = snapshot(engine, env)
    else:
        raise ValueError("unknown synthetic fixture operation")
    print(json.dumps(result), flush=True)
