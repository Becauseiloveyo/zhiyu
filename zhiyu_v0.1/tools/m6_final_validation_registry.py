"""Recorded Gate E procedure; isolated PostgreSQL schema, frozen synthetic inputs."""

import json
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from zhiyu.core.errors import AccessDenied
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import values_for
from zhiyu.db.models import EventRow, ValidationRunRow, ValidationScenarioRow, VerificationSpecRow
from zhiyu.db.session import get_engine
from zhiyu.domain.contracts import NormalizedEvent, ValidationRun, ValidationScenario, VerificationSpec
from zhiyu.repositories.audit import AuditRepository
from zhiyu.services.bootstrap import BootstrapBundle, BootstrapService
from zhiyu.services.event_ingest import EventIngestService

root = Path("/safety-output")
objects = json.loads(Path("/app/config/m6-validation-fixtures.json").read_text())
schema = "m6_a12_" + uuid4().hex
base = get_engine()
with base.begin() as c:
    c.execute(CreateSchema(schema))
engine = create_engine(base.url, connect_args={"options": "-c search_path=" + schema + " -c timezone=UTC"})
result = {
    "status": "RUNNING",
    "schema": schema,
    "data_origin": "SYNTHETIC",
    "source": "Frozen ai.5 fixtures; trusted registry seeded by test administrator, not an unauthenticated API registration.",
}
try:
    with engine.begin() as c:
        cfg = Config("/app/alembic.ini")
        cfg.attributes["connection"] = c
        command.upgrade(cfg, "head")
    with Session(engine) as db:
        BootstrapService(db).apply(
            BootstrapBundle.model_validate_json(Path("/app/config/bootstrap.lab.json").read_text()),
            actor_id="gate-e-a12",
        )
    with Session(engine) as db, db.begin():
        for kind, row in [
            (VerificationSpec, VerificationSpecRow),
            (ValidationScenario, ValidationScenarioRow),
            (ValidationRun, ValidationRunRow),
        ]:
            obj = kind.model_validate(next(o for o in objects if o.get("object_type") == kind.__name__))
            db.add(row(**values_for(obj, row)))
            db.flush()
        db.flush()
    event = NormalizedEvent.model_validate(next(o for o in objects if o.get("event_id") == "evt-net"))
    principal = ServicePrincipal(
        principal_id="gate-e-a12",
        environment_ids={event.environment_id},
        collector_ids={event.collector_id},
        source_types={event.source_type},
        permissions={"events:write"},
    )
    with Session(engine) as db:
        receipt = EventIngestService(db).ingest([event], principal=principal)
        assert receipt.accepted == 1
    rejected = {}
    for name, updates in {
        "forged": {"validation_run_id": "not-a-registered-run"},
        "out-of-source-scope": {"source_resource_ids": ["target-a"]},
        "expired-run": {"source_timestamp": event.source_timestamp + timedelta(hours=1)},
        "origin-mismatch": {"data_origin": "OBSERVED"},
    }.items():
        changed = event.model_copy(
            update={**updates, "event_id": "evt-a12-" + name, "origin_event_id": "origin-a12-" + name}
        )
        with Session(engine) as db:
            try:
                EventIngestService(db).ingest([changed], principal=principal)
            except AccessDenied as error:
                rejected[name] = str(error)
            else:
                raise AssertionError(name + " was accepted")
    with Session(engine) as db:
        actual = db.scalar(select(EventRow))
        assert actual.validation_run_id == event.validation_run_id
        assert db.scalar(select(func.count()).select_from(EventRow)) == 1
        assert AuditRepository(db).verify_chain(event.environment_id)
        result.update(
            status="PASS",
            event_id=actual.event_id,
            validation_run_id=actual.validation_run_id,
            environment_id=actual.environment_id,
            rejected=rejected,
            normalized_event_count=1,
            audit_valid=True,
            external_actions=0,
        )
finally:
    engine.dispose()
    with base.begin() as c:
        c.execute(DropSchema(schema, cascade=True))
    result["schema_removed"] = True
    (root / "a12-registry-result.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result))
