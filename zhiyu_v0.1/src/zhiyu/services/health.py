from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

SCHEMA_REVISION = "0016_lab_remediation"


def readiness(engine: Engine) -> dict[str, Any]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            versions = list(connection.scalars(text("SELECT version_num FROM alembic_version")))
            if versions != [SCHEMA_REVISION]:
                return {"status": "not_ready", "database": "reachable", "schema": "migration_required"}
            connection.execute(text("SELECT event_id FROM normalized_events LIMIT 0"))
            connection.execute(text("SELECT message_id FROM outbox LIMIT 0"))
            connection.execute(text("SELECT audit_id FROM audit_entries LIMIT 0"))
            return {"status": "ready", "database": "ok", "schema": SCHEMA_REVISION}
    except SQLAlchemyError:
        return {"status": "not_ready", "database": "unavailable_or_unmigrated", "schema": "unchecked"}
