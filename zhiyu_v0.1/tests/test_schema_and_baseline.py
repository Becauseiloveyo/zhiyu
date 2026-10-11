import copy
import json

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from conftest import ROOT, fixture_objects, migration_config
from jsonschema import Draft202012Validator
from pydantic import ValidationError
from sqlalchemy import CheckConstraint, inspect, select, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zhiyu.db import infrastructure  # noqa: F401
from zhiyu.db.base import Base
from zhiyu.db.contract_rows import CONTRACT_ROWS
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import EnvironmentRow, IncidentRow, ResourceRow
from zhiyu.domain.contracts import (
    CONTRACTS,
    ActionRequest,
    AuthorizationDecision,
    VerificationResult,
    action_digest,
)
from zhiyu.services.health import readiness


def test_frozen_contract_is_byte_identical():
    assert (ROOT / "baseline/ai5/models.py").read_bytes() == (
        ROOT / "src/zhiyu/domain/contracts.py"
    ).read_bytes()


def test_all_contracts_fields_have_typed_columns_and_roundtrip():
    assert len(CONTRACT_ROWS) == len(CONTRACTS) == 30
    for contract, row in CONTRACT_ROWS.items():
        assert set(contract.model_fields) - {"object_type"} <= set(row.__table__.c.keys())
        for col in row.__table__.c:
            if col.type.__class__.__name__ in {"JSON", "JSONB"}:
                assert isinstance(col.type, JSONB)
    for obj in fixture_objects():
        contract = CONTRACTS[obj["object_type"]].model_validate(obj)
        row_type = CONTRACT_ROWS[type(contract)]
        row = row_type(**values_for(contract, row_type))
        assert contract_from(row, type(contract)) == contract


def test_json_schema_and_every_golden_object():
    schema = json.loads((ROOT / "baseline/ai5/zhiyu.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for obj in fixture_objects():
        validator.validate(obj)
    # Every generated definition must still match the frozen schema, not just the examples.
    definitions = {}
    for name, cls in CONTRACTS.items():
        generated = cls.model_json_schema()
        definitions.update(generated.pop("$defs", {}))
        definitions[name] = generated
    assert definitions == schema["$defs"]


def test_verification_counterfactuals_and_authorization_mutation():
    objects = fixture_objects()
    verdicts = {}
    for obj in objects:
        if obj["object_type"] == "VerificationResult":
            verified = VerificationResult.model_validate(obj)
            verdicts[verified.verification_id] = verified.status.value
    assert set(verdicts.values()) == {"PASS", "FAIL", "INCONCLUSIVE"}
    action = ActionRequest.model_validate(next(o for o in objects if o["object_type"] == "ActionRequest"))
    changed = action.model_copy(deep=True)
    changed.target.locator["port"] += 1
    assert action_digest(action) != action_digest(changed)
    decision = copy.deepcopy(next(o for o in objects if o["object_type"] == "AuthorizationDecision"))
    decision["business_impact"] = "HIGH"
    with pytest.raises(ValidationError):
        AuthorizationDecision.model_validate(decision)
    gap = copy.deepcopy(next(o for o in objects if o.get("verification_id") == "verify-observation-gap"))
    gap["status"] = "PASS"
    with pytest.raises(ValidationError):
        VerificationResult.model_validate(gap)


@pytest.mark.postgres
def test_migration_roundtrip_and_no_metadata_drift(pg_engine):
    with pg_engine.begin() as connection:
        before = set(inspect(connection).get_table_names())
        assert len(before) == 72  # 30 frozen contracts + 41 internal tables + Alembic version.
        diff = compare_metadata(
            MigrationContext.configure(connection, opts={"compare_server_default": True}), Base.metadata
        )
        assert diff == []
        # Alembic's default diff does not compare CHECK definitions; verify their presence too.
        for table in Base.metadata.tables.values():
            expected = {
                connection.dialect.identifier_preparer.format_constraint(constraint).strip('"')
                for constraint in table.constraints
                if isinstance(constraint, CheckConstraint)
            }
            actual = {
                constraint["name"] for constraint in inspect(connection).get_check_constraints(table.name)
            }
            assert actual == expected, table.name
        command.downgrade(migration_config(connection), "base")
        assert set(inspect(connection).get_table_names()) == {"alembic_version"}
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM pg_proc WHERE proname = 'zhiyu_reject_mutation' AND pronamespace = current_schema()::regnamespace"
                )
            )
            == 0
        )
        command.upgrade(migration_config(connection), "head")
        assert set(inspect(connection).get_table_names()) == before
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    assert readiness(pg_engine)["status"] == "ready"


@pytest.mark.postgres
def test_db_checks_reject_invalid_resources_and_environment(bootstrapped):
    with Session(bootstrapped) as db, pytest.raises(IntegrityError):
        with db.begin():
            db.execute(update(ResourceRow).values(binding_version=0))
    with Session(bootstrapped) as db, pytest.raises(IntegrityError):
        with db.begin():
            db.execute(update(EnvironmentRow).values(max_auto_risk="R5"))


@pytest.mark.postgres
def test_incident_lifecycle_and_db_enum_checks(bootstrapped):
    obj = next(o for o in fixture_objects() if o["object_type"] == "SecurityIncident")
    from zhiyu.domain.contracts import SecurityIncident

    with Session(bootstrapped) as db, db.begin():
        db.add(IncidentRow(**values_for(SecurityIncident.model_validate(obj), IncidentRow)))
    with Session(bootstrapped) as db:
        row = db.scalars(select(IncidentRow)).one()
        assert row.triaged_at and row.contained_at and row.resolved_at is None
        assert contract_from(row, SecurityIncident) == SecurityIncident.model_validate(obj)
    for update_values in ({"status": "INVENTED"}, {"status": "CLOSED"}, {"state_version": 0}):
        with Session(bootstrapped) as db, pytest.raises(IntegrityError), db.begin():
            db.execute(update(IncidentRow).values(**update_values))
