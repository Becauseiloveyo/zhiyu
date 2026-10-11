"""Read-only checksums of every table in the dedicated, isolated acceptance DB."""

import hashlib
import json

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from zhiyu.db.session import get_engine
from zhiyu.repositories.audit import AuditRepository


def snapshot(statement_timeout_ms=None):
    engine = get_engine()
    tables = {}
    with engine.connect() as connection:
        if statement_timeout_ms is not None:
            assert 1000 <= statement_timeout_ms <= 300000
            connection.execute(
                text("SELECT set_config('statement_timeout', :value, true)"),
                {"value": str(statement_timeout_ms)},
            )
        names = inspect(engine).get_table_names()
        for name in names:
            # Identifier originates from PostgreSQL's own metadata, quoted by the dialect.
            quoted = engine.dialect.identifier_preparer.quote(name)
            rows = connection.execution_options(stream_results=True, yield_per=256).scalars(
                text("SELECT row_to_json(r)::text FROM " + quoted + " r ORDER BY row_to_json(r)::text")
            )
            digest = hashlib.sha256()
            count = 0
            for row in rows:
                if count:
                    digest.update(b"\n")
                digest.update(row.encode())
                count += 1
            tables[name] = {
                "count": count,
                "sha256": digest.hexdigest(),
            }
        environments = connection.scalars(text("SELECT environment_id FROM environments")).all()
        high_risk = connection.scalar(
            text(
                "SELECT count(*) FROM action_requests a JOIN capabilities c ON c.capability_id=a.capability_id AND c.version=a.capability_version JOIN action_dispatches d ON d.action_id=a.action_id JOIN action_execution_results r ON r.attempt_id=d.attempt_id WHERE c.base_risk IN ('R3','R4','R5') AND r.executor <> 'NOT_DISPATCHED'"
            )
        )
    with Session(engine) as db:
        valid = {env: AuditRepository(db).verify_chain(env) for env in environments}
    return {"tables": tables, "audit_chains": valid, "high_risk_automatic_actions": high_risk}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--statement-timeout-ms", type=int)
    print(json.dumps(snapshot(parser.parse_args().statement_timeout_ms)))
