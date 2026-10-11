"""DB binding tests only: no policy runtime, scheduler, probe or action is executed."""

import pytest
from conftest import fixture_objects
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zhiyu.db.mapping import values_for
from zhiyu.db.models import (
    ActionRow,
    AuthorizationContextRow,
    CapabilityRow,
    ContextRow,
    IncidentRow,
    TaskRow,
    ValidationRunRow,
    ValidationScenarioRow,
    VerificationResultRow,
    VerificationSpecRow,
)
from zhiyu.domain.contracts import (
    ActionRequest,
    AuthorizationContext,
    CapabilityManifest,
    ContextBundle,
    SecurityIncident,
    Task,
    ValidationRun,
    ValidationScenario,
    VerificationResult,
    VerificationSpec,
    action_digest,
)

pytestmark = pytest.mark.postgres


@pytest.fixture
def action_graph(bootstrapped):
    objects = fixture_objects()

    def first(kind):
        return next(o for o in objects if o["object_type"] == kind)

    with Session(bootstrapped) as db, db.begin():
        for obj in objects:
            if obj["object_type"] == "CapabilityManifest":
                db.add(CapabilityRow(**values_for(CapabilityManifest.model_validate(obj), CapabilityRow)))
        db.add(
            IncidentRow(**values_for(SecurityIncident.model_validate(first("SecurityIncident")), IncidentRow))
        )
        db.flush()
        obj = next(o for o in objects if o.get("task_id") == "task-block" and o["object_type"] == "Task")
        db.add(TaskRow(**values_for(Task.model_validate(obj), TaskRow)))
        db.flush()
        action = ActionRequest.model_validate(first("ActionRequest"))
        db.add(ActionRow(**values_for(action, ActionRow), action_digest=action_digest(action)))
        db.flush()
    return bootstrapped, action


def test_action_idempotency_and_digest_are_database_bound(action_graph):
    engine, action = action_graph
    duplicate = action.model_copy(update={"action_id": "another-action"})
    with Session(engine) as db, pytest.raises(IntegrityError), db.begin():
        db.add(ActionRow(**values_for(duplicate, ActionRow), action_digest=action_digest(duplicate)))
    context = AuthorizationContext.model_validate(
        next(o for o in fixture_objects() if o["object_type"] == "AuthorizationContext")
    )
    context.action_digest = "0" * 64
    with Session(engine) as db, pytest.raises(IntegrityError), db.begin():
        db.add(AuthorizationContextRow(**values_for(context, AuthorizationContextRow)))
    with Session(engine) as db, pytest.raises(IntegrityError), db.begin():
        db.execute(update(ActionRow).values(parameters={"mutated": True}))


def test_context_cannot_reference_incident_in_another_environment(action_graph):
    engine, action = action_graph
    context = ContextBundle.model_validate(
        next(o for o in fixture_objects() if o["object_type"] == "ContextBundle")
    )
    context.environment_id = "outside"
    with Session(engine) as db, pytest.raises(IntegrityError), db.begin():
        db.add(ContextRow(**values_for(context, ContextRow)))


def test_cyclic_scenario_spec_and_three_check_db_guard(action_graph):
    engine, action = action_graph
    objects = fixture_objects()
    with Session(engine) as db, db.begin():
        for contract_type, row_type in (
            (ValidationScenario, ValidationScenarioRow),
            (VerificationSpec, VerificationSpecRow),
        ):
            obj = next(o for o in objects if o["object_type"] == contract_type.__name__)
            db.add(row_type(**values_for(contract_type.model_validate(obj), row_type)))
        db.flush()
        run = ValidationRun.model_validate(next(o for o in objects if o["object_type"] == "ValidationRun"))
        db.add(ValidationRunRow(**values_for(run, ValidationRunRow)))
        db.flush()
        result = VerificationResult.model_validate(
            next(o for o in objects if o.get("verification_id") == "verify-containment-pass")
        )
        db.add(VerificationResultRow(**values_for(result, VerificationResultRow)))
    with Session(engine) as db, pytest.raises(IntegrityError), db.begin():
        db.execute(update(VerificationResultRow).values(observation_status="INCONCLUSIVE", status="PASS"))
    with Session(engine) as db, pytest.raises(IntegrityError), db.begin():
        db.execute(update(VerificationSpecRow).values(aggregation_rule="RELAXED"))
