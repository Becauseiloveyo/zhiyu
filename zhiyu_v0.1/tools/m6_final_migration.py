"""Final isolated-schema 0015 -> 0016 -> 0015 -> 0016 with retained historical rows."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateSchema, DropSchema

from zhiyu.db import infrastructure, models  # noqa: F401
from zhiyu.db.base import Base
from zhiyu.db.session import get_engine
from zhiyu.services.bootstrap import BootstrapBundle, BootstrapService


def main():
    engine = get_engine()
    schema = "m6_final_migration_" + uuid4().hex
    with engine.begin() as c:
        c.execute(CreateSchema(schema))
    report = {
        "status": "RUNNING",
        "schema": schema,
        "stable_head": "0015_ai_decisions",
        "roundtrip": [
            "0015_ai_decisions",
            "0016_lab_remediation",
            "0015_ai_decisions",
            "0016_lab_remediation",
        ],
        "limit": "0016 changes an internal receipt CHECK only. Downgrade refuses LAB_PATH receipts; it never deletes immutable evidence. This roundtrip contains historical rows without Lab receipts.",
    }
    try:
        with engine.connect() as c:
            c.execute(text('SET search_path TO "' + schema + '"'))
            cfg = Config("alembic.ini")
            cfg.attributes["connection"] = c
            command.upgrade(cfg, "0015_ai_decisions")
            c.commit()
            # Seed frozen baseline rows through the same service on this isolated connection.
            from sqlalchemy.orm import Session

            bundle = BootstrapBundle.model_validate_json(Path("config/bootstrap.lab.json").read_text())
            with Session(bind=c) as db:
                BootstrapService(db).apply(bundle, actor_id="m6-final-migration")
            c.commit()
            names = set(inspect(c).get_table_names(schema=schema)) - {"alembic_version"}

            def snapshot():
                return {
                    n: {"count": len(rows), "sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest()}
                    for n in sorted(names)
                    for rows in [
                        c.scalars(
                            text(
                                'SELECT row_to_json(r)::text FROM "' + n + '" r ORDER BY row_to_json(r)::text'
                            )
                        ).all()
                    ]
                }

            before = snapshot()
            assert before["environments"]["count"] > 0
            command.upgrade(cfg, "head")
            assert snapshot() == before
            command.downgrade(cfg, "0015_ai_decisions")
            middle = snapshot()
            assert middle == before
            command.upgrade(cfg, "head")
            after = snapshot()
            assert after == before
            differences = compare_metadata(MigrationContext.configure(c), Base.metadata)
            assert differences == [], repr(differences)
            report.update(
                status="PASS",
                before=before,
                after_downgrade=middle,
                after_upgrade=after,
                metadata_drift=[],
                table_count=len(inspect(c).get_table_names(schema=schema)),
            )
    finally:
        with engine.begin() as c:
            c.execute(DropSchema(schema, cascade=True))
        report["isolated_schema_removed"] = True
        Path("/safety-output/final-migration.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "table_count": report["table_count"]}))


if __name__ == "__main__":
    main()
