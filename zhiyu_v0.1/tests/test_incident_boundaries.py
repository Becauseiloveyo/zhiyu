from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_adapters import NOW
from test_event_intelligence import auth_event, process, save
from test_incident_engine import advance, chain, promote

from zhiyu.core.errors import ConflictError
from zhiyu.core.incident_config import IncidentConfig
from zhiyu.db.incident_intelligence import IncidentEventRow
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import EventRow, EvidenceRow, IncidentRow
from zhiyu.domain.contracts import SecurityIncident
from zhiyu.services.incident_policy import IncidentPromotionPolicy, IncidentRiskCalculator


def test_known_validation_production_synthetic_and_ot_profile_policies():
    events = [auth_event(str(i)) for i in range(5)]
    risk = IncidentRiskCalculator(IncidentConfig()).calculate(events, verified_count=5, validation=False)
    group = SimpleNamespace(
        first_seen_at=events[0].source_timestamp,
        last_seen_at=events[0].source_timestamp,
        grouping_keys={"activity": "authentication"},
    )
    state = SimpleNamespace(disposition="TIMELY")
    policy = IncidentPromotionPolicy(IncidentConfig())
    for environment, changed, reason in [
        (
            SimpleNamespace(deployment_stage="PRODUCTION", asset_domain="IT"),
            events,
            "synthetic_in_production",
        ),
        (
            SimpleNamespace(deployment_stage="LAB", asset_domain="OT"),
            events,
            "ot_profile_requires_corroboration",
        ),
        (
            SimpleNamespace(deployment_stage="LAB", asset_domain="IT"),
            [e.model_copy(update={"validation_run_id": "registered"}) for e in events],
            "registered_validation_context",
        ),
    ]:
        result, reasons = policy.evaluate(
            group, state, changed, risk, environment, NOW + timedelta(seconds=90)
        )
        assert result is False and reason in reasons


@pytest.mark.postgres
def test_raw_reference_alone_does_not_verify_a_forged_normalized_assertion(bootstrapped):
    chain(bootstrapped, unrelated=False)
    with Session(bootstrapped) as db:
        raw_ref = db.scalars(select(EventRow.raw_ref)).first()
    forged = [
        auth_event("forged" + str(i), user="untrusted").model_copy(
            update={"raw_ref": raw_ref, "severity_signal": 10}
        )
        for i in range(5)
    ]
    save(bootstrapped, forged)
    process(bootstrapped)
    promote(bootstrapped)
    with Session(bootstrapped) as db:
        evidence = db.scalar(select(EvidenceRow).where(EvidenceRow.trust_status == "UNVERIFIED_ORIGIN"))
        assert evidence is not None and evidence.content_ref.startswith("db://normalized_events/")
        identifier = evidence.incident_id
    with pytest.raises(ConflictError, match="origin"):
        advance(bootstrapped, identifier, "TRIAGED", 1)


@pytest.mark.postgres
def test_evidence_cannot_be_linked_to_another_incident(bootstrapped):
    chain(bootstrapped, unrelated=False)
    process(bootstrapped)
    promote(bootstrapped)
    with Session(bootstrapped) as db, db.begin():
        original = db.scalars(select(IncidentRow)).one()
        copied = contract_from(original, SecurityIncident).model_copy(
            update={"incident_id": "other-incident"}
        )
        db.add(IncidentRow(**values_for(copied, IncidentRow)))
    with Session(bootstrapped) as db, pytest.raises(IntegrityError), db.begin():
        relation = db.scalars(select(IncidentEventRow)).first()
        db.add(
            IncidentEventRow(
                environment_id=relation.environment_id,
                incident_id="other-incident",
                event_id=relation.event_id,
                evidence_id=relation.evidence_id,
            )
        )
