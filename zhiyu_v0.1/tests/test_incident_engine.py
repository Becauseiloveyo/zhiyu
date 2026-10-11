import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from conftest import ROOT
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from test_adapters import NOW
from test_event_intelligence import auth_event, process, save
from test_raw_ingest import sensor_principal

from zhiyu.core.errors import ConflictError, StaleVersionError
from zhiyu.core.incident_config import IncidentConfig
from zhiyu.db.incident_intelligence import (
    IncidentAnalysisRow,
    IncidentEventRow,
    IncidentGroupRow,
    PromotionRecordRow,
)
from zhiyu.db.infrastructure import RawRecordRow
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import (
    EnvironmentRow,
    EventRow,
    EvidenceRow,
    IncidentRow,
    OutboxRow,
)
from zhiyu.domain.contracts import SecurityIncident
from zhiyu.repositories.audit import AuditRepository
from zhiyu.services.incident_engine import IncidentEngine
from zhiyu.services.incident_lifecycle import transition
from zhiyu.services.incident_policy import IncidentRiskCalculator
from zhiyu.services.raw_ingest import RawIngestService, RawInput


def chain(engine, *, offset=0, prefix="a", unrelated=True):
    fixture = json.loads((ROOT / "tests/fixtures/golden_chain_m2.json").read_text(encoding="utf-8"))
    results = []
    for source in ("suricata", "wazuh"):
        records = []
        for record in fixture["records"]:
            if record["source_type"] != source or (record.get("unrelated") and not unrelated):
                continue
            raw = copy.deepcopy(record["raw"])
            raw["timestamp"] = (NOW + timedelta(seconds=offset + record["offset_seconds"])).isoformat()
            records.append(RawInput(json.dumps(raw), prefix + "/" + record["origin"]))
        with Session(engine) as db:
            results.append(
                RawIngestService(db).ingest(
                    records,
                    environment_id="lab-zhiyu-01",
                    collector_id="sensor-" + source,
                    source_type=source,
                    principal=sensor_principal(),
                    data_origin="SYNTHETIC",
                    received_at=NOW + timedelta(seconds=offset + 60),
                )
            )
    return results


def promote(engine, *, offset=0, config=None):
    with Session(engine) as db:
        service = IncidentEngine(db, config) if config else IncidentEngine(db)
        return service.promote(
            "lab-zhiyu-01", principal=sensor_principal(), now=NOW + timedelta(seconds=offset + 90)
        )


def incident_id(engine):
    with Session(engine) as db:
        return db.scalars(select(IncidentRow.incident_id)).first()


def advance(engine, incident, target, version, seconds=100):
    with Session(engine) as db:
        return transition(
            db,
            environment_id="lab-zhiyu-01",
            incident_id=incident,
            target=target,
            expected_version=version,
            principal=sensor_principal(),
            now=NOW + timedelta(seconds=seconds),
        )


def test_risk_is_multifactor_and_explained():
    config = IncidentConfig()
    calculator = IncidentRiskCalculator(config)
    first = auth_event("a")
    single = calculator.calculate([first], verified_count=1, validation=False)
    several = calculator.calculate(
        [first, auth_event("b", "suricata"), auth_event("c")], verified_count=3, validation=False
    )
    assert single.score < several.score and several.score == 62
    assert several.factors["components"]["independent_sources"] == 10
    assert calculator.calculate([first], verified_count=0, validation=True).score < single.score
    critical = IncidentRiskCalculator(IncidentConfig(asset_criticality={"lab-zhiyu-01/target-a": 5}))
    assert critical.calculate([first], verified_count=1, validation=False).score > single.score


@pytest.mark.postgres
def test_golden_chain_risk_evidence_lineage_and_idempotence(bootstrapped):
    ingests = chain(bootstrapped)
    assert sum(x["accepted"] for x in ingests) == 4
    correlation = process(bootstrapped)
    promoted = promote(bootstrapped)
    assert (correlation["groups_created"], len(correlation["decision_ids"]), promoted["created"]) == (2, 2, 1)
    with Session(bootstrapped) as db:
        incident = db.scalars(select(IncidentRow)).one()
        assert incident.status == "NEW" and incident.state_version == 1 and incident.priority == "P2"
        assert (
            len(incident.related_event_ids) == 3
            and len(incident.evidence_ids) == 3
            and len(incident.event_group_ids) == 1
        )
        analysis = db.scalars(select(IncidentAnalysisRow)).one()
        assert analysis.score == 62
        assert analysis.factors["components"] == {
            "severity": 24,
            "independent_sources": 10,
            "asset_criticality": 4,
            "repeated_behavior": 4,
            "activity": 10,
            "evidence_quality": 10,
            "validation_context": 0,
        }
        for evidence in db.scalars(select(EvidenceRow)):
            event = db.get(EventRow, evidence.source_event_ids[0])
            raw = db.get(RawRecordRow, event.raw_ref.removeprefix("db://raw_records/"))
            assert (
                evidence.content_ref == event.raw_ref and evidence.provenance_group == event.provenance_group
            )
            assert evidence.integrity_hash == hashlib.sha256(raw.content).hexdigest()
            assert evidence.trust_status == "VERIFIED_ORIGIN"
        assert db.scalar(select(func.count()).select_from(IncidentEventRow)) == 3
        assert db.scalar(select(func.count()).select_from(IncidentGroupRow)) == 1
        assert db.scalar(select(func.count()).select_from(PromotionRecordRow)) == 2
        assert AuditRepository(db).verify_chain("lab-zhiyu-01")
        assert (
            db.scalar(
                select(func.count()).select_from(OutboxRow).where(OutboxRow.event_type == "IncidentCreated")
            )
            == 1
        )
    assert sum(x["duplicates"] for x in chain(bootstrapped)) == 4
    assert process(bootstrapped)["processed"] == promote(bootstrapped)["evaluated"] == 0


@pytest.mark.postgres
def test_merge_and_same_group_update(bootstrapped):
    chain(bootstrapped, unrelated=False)
    process(bootstrapped)
    promote(bootstrapped)
    original = incident_id(bootstrapped)
    chain(bootstrapped, unrelated=False, prefix="b")
    process(bootstrapped)
    assert promote(bootstrapped)["updated"] == 1
    chain(bootstrapped, offset=300, prefix="c", unrelated=False)
    process(bootstrapped, now=NOW + timedelta(seconds=390))
    result = promote(bootstrapped, offset=300)
    assert result["created"] == 0 and result["updated"] == 1 and result["results"][0]["outcome"] == "MERGED"
    with Session(bootstrapped) as db:
        incident = db.scalars(select(IncidentRow)).one()
        assert incident.incident_id == original and len(incident.related_event_ids) == 9
        assert len(incident.event_group_ids) == 2 and incident.state_version == 3


@pytest.mark.postgres
@pytest.mark.parametrize("reason", ["closed", "horizon", "policy"])
def test_no_merge_closed_distant_or_different_policy(bootstrapped, reason):
    chain(bootstrapped, unrelated=False)
    process(bootstrapped)
    promote(bootstrapped)
    offset = 1800 if reason == "horizon" else 300
    if reason == "closed":
        with Session(bootstrapped) as db, db.begin():
            incident = db.scalars(select(IncidentRow)).one()
            incident.status = "CLOSED"
            incident.closure_type = "CLOSED_ACCEPTED_RISK"
            incident.closure_evidence_ids = incident.evidence_ids
            incident.closed_at = NOW + timedelta(seconds=100)
            contract_from(incident, SecurityIncident)
    chain(bootstrapped, offset=offset, prefix="b", unrelated=False)
    process(bootstrapped, now=NOW + timedelta(seconds=offset + 90))
    config = IncidentConfig(merge_version="incident-merge/changed") if reason == "policy" else None
    assert promote(bootstrapped, offset=offset, config=config)["created"] == 1


@pytest.mark.postgres
def test_lifecycle_guards_cas_and_retry(bootstrapped):
    chain(bootstrapped)
    process(bootstrapped)
    promote(bootstrapped)
    identifier = incident_id(bootstrapped)
    with pytest.raises(ConflictError):
        advance(bootstrapped, identifier, "INVESTIGATING", 1)
    triaged = advance(bootstrapped, identifier, "TRIAGED", 1)
    assert triaged.state_version == 2 and triaged.triaged_at is not None
    assert advance(bootstrapped, identifier, "TRIAGED", 1).state_version == 2
    with pytest.raises(StaleVersionError):
        advance(bootstrapped, identifier, "INVESTIGATING", 1)
    investigated = advance(bootstrapped, identifier, "INVESTIGATING", 2, 110)
    assert investigated.state_version == 3 and investigated.investigation_started_at is not None
    with pytest.raises(ConflictError):
        advance(bootstrapped, identifier, "CLOSED", 3)


@pytest.mark.postgres
def test_scope_and_evidence_freshness_guards(bootstrapped):
    chain(bootstrapped)
    process(bootstrapped)
    promote(bootstrapped)
    identifier = incident_id(bootstrapped)
    with pytest.raises(ConflictError, match="freshness"):
        advance(bootstrapped, identifier, "TRIAGED", 1, 90000)
    advance(bootstrapped, identifier, "TRIAGED", 1)
    with Session(bootstrapped) as db, db.begin():
        db.execute(update(EnvironmentRow).values(scope_ids=[]))
    with pytest.raises(ConflictError, match="scope-bound"):
        advance(bootstrapped, identifier, "INVESTIGATING", 2)


@pytest.mark.postgres
def test_promotion_concurrency_crash_retry_and_restart(bootstrapped, monkeypatch):
    chain(bootstrapped)
    process(bootstrapped)
    original = __import__("zhiyu.services.incident_engine", fromlist=["publish_change"]).publish_change

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("crash before promotion commit")

    monkeypatch.setattr("zhiyu.services.incident_engine.publish_change", fail)
    with pytest.raises(RuntimeError, match="crash"):
        promote(bootstrapped)
    with Session(bootstrapped) as db:
        for row in (IncidentRow, EvidenceRow, IncidentEventRow, IncidentGroupRow, PromotionRecordRow):
            assert db.scalar(select(func.count()).select_from(row)) == 0
    monkeypatch.setattr("zhiyu.services.incident_engine.publish_change", original)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: promote(bootstrapped), range(2)))
    assert sum(x["created"] for x in results) == 1
    bootstrapped.dispose()
    assert promote(bootstrapped)["evaluated"] == 0


@pytest.mark.postgres
def test_no_promotion_without_bound_assets_or_with_late_data(bootstrapped):
    events = [auth_event(str(i)).model_copy(update={"target_resource_ids": []}) for i in range(5)]
    events += [auth_event("late" + str(i), received=1000) for i in range(3)]
    save(bootstrapped, events)
    process(bootstrapped)
    result = promote(bootstrapped)
    assert result["created"] == 0 and all(x["outcome"] == "NOT_PROMOTED" for x in result["results"])
