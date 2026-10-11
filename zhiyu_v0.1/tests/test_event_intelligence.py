import copy
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_adapters import NOW, context, normalize, raw
from test_raw_ingest import sensor_principal

from zhiyu.core.intelligence_config import IntelligenceConfig
from zhiyu.db.intelligence import DecisionInputRow, GroupMemberRow, GroupStateRow
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import CorrelationDecisionRow, EventGroupRow, EventRow, OutboxRow
from zhiyu.domain.contracts import EventGroup
from zhiyu.repositories.audit import AuditRepository
from zhiyu.services.correlation_keys import CorrelationKeyBuilder
from zhiyu.services.event_ingest import EventIngestService
from zhiyu.services.event_intelligence import EventIntelligenceEngine, group_events
from zhiyu.services.intelligence_metrics import metrics


def auth_event(
    identity,
    source="wazuh",
    seconds=10,
    *,
    user=None,
    target="10.77.20.10",
    source_ip="192.0.2.10",
    received=60,
):
    value = raw(source, "authentication" if source == "suricata" else "ssh")
    value["timestamp"] = (NOW + timedelta(seconds=seconds)).isoformat()
    if source == "wazuh":
        value["id"] = identity
        value["agent"]["ip"] = target
        value["rule"]["level"] = 9
        value["data"] = {"srcip": source_ip, "dstport": 8080, "protocol": "TCP"}
        if user is not None:
            value["data"]["srcuser"] = user
    else:
        value["src_ip"], value["dest_ip"] = source_ip, target
    return normalize(
        value,
        replace(context(source), origin_event_id=identity, ingested_at=NOW + timedelta(seconds=received)),
    )


def save(engine, events, principal=None):
    with Session(engine) as db:
        return EventIngestService(db).ingest(events, principal=principal or sensor_principal())


def process(engine, *, now=NOW + timedelta(seconds=90), limit=1000, principal=None):
    with Session(engine) as db:
        return EventIntelligenceEngine(db).process(
            "lab-zhiyu-01", principal=principal or sensor_principal(), now=now, limit=limit
        )


def test_correlation_key_positive_and_negative_dimensions():
    keys = CorrelationKeyBuilder(IntelligenceConfig())
    base = auth_event("a")
    assert keys.build(base).digest == keys.build(auth_event("b", "suricata")).digest
    variants = [
        auth_event("b", user="alice"),
        auth_event("b", target="10.77.20.11"),
        auth_event("b", source_ip="192.0.2.11"),
        auth_event("b", seconds=610, received=620),
        base.model_copy(update={"environment_id": "other"}),
        base.model_copy(update={"outcome": "SUCCESS"}),
        base.model_copy(update={"data_origin": "OBSERVED"}),
        base.model_copy(update={"validation_run_id": "trusted-run"}),
        base.model_copy(update={"actor_resource_id": "validation-a"}),
    ]
    assert all(keys.build(x).digest != keys.build(base).digest for x in variants)
    assert keys.build(auth_event("a", user="alice")).digest != keys.build(auth_event("b", user="bob")).digest
    assert (
        keys.build(base).digest
        != CorrelationKeyBuilder(IntelligenceConfig(auth_failure_window=60)).build(base).digest
    )


@pytest.mark.postgres
def test_multisource_provenance_exclusion_relations_and_metrics(bootstrapped):
    events = [
        auth_event("a", "suricata"),
        auth_event("b", seconds=12),
        auth_event("c", seconds=14),
        auth_event("unrelated", user="bob"),
    ]
    save(bootstrapped, events)
    result = process(bootstrapped)
    assert (result["processed"], result["groups_created"], len(result["decision_ids"])) == (4, 2, 2)
    with Session(bootstrapped) as db:
        states = list(db.scalars(select(GroupStateRow)))
        state = next(x for x in states if x.summary["event_count"] == 3)
        group = contract_from(db.get(EventGroupRow, state.group_id), EventGroup)
        assert set(group.member_event_ids) == {x.event_id for x in events[:3]}
        assert len(group_events(db, "lab-zhiyu-01", state.group_id)) == 3
        assert state.summary["independent_sources"] == 2
        decision = db.scalar(
            select(CorrelationDecisionRow).where(CorrelationDecisionRow.output_group_id == state.group_id)
        )
        assert events[3].event_id in decision.excluded_event_ids
        assert "user" in json.loads(decision.merge_reason)["excluded"][events[3].event_id]
        assert "cross_source_authentication" in decision.rules_fired
        assert AuditRepository(db).verify_chain("lab-zhiyu-01")
        assert (
            db.scalar(
                select(func.count()).select_from(OutboxRow).where(OutboxRow.event_type == "EventGroupCreated")
            )
            == 2
        )
        assert (
            db.scalar(
                select(func.count()).select_from(DecisionInputRow).where(DecisionInputRow.role == "INPUT")
            )
            == 4
        )
        measured = metrics(db, "lab-zhiyu-01", sensor_principal())
        assert measured["compression_ratio"] == 2 and measured["grouped_event_count"] == 4
        assert measured["correlation_latency_ms"]["samples"] == 1
    assert process(bootstrapped)["processed"] == 0
    assert save(bootstrapped, events).duplicates == 4
    assert process(bootstrapped)["groups_created"] == 0


@pytest.mark.postgres
def test_out_of_order_window_close_late_expired_future(bootstrapped):
    first = auth_event("a", seconds=40)
    save(bootstrapped, [first])
    initial = process(bootstrapped)
    save(bootstrapped, [auth_event("earlier", seconds=20)])
    assert process(bootstrapped)["groups_created"] == 0
    process(bootstrapped, now=NOW + timedelta(seconds=421))
    save(
        bootstrapped,
        [
            auth_event("late", seconds=30, received=430),
            auth_event("expired", received=90000),
            auth_event("future", seconds=1000, received=0),
        ],
    )
    assert process(bootstrapped, now=NOW + timedelta(seconds=90100))["groups_created"] == 3
    with Session(bootstrapped) as db:
        original = db.get(EventGroupRow, initial["group_ids"][0])
        assert len(original.member_event_ids) == 2 and original.first_seen_at == NOW + timedelta(seconds=20)
        assert set(db.scalars(select(GroupStateRow.disposition))) == {"TIMELY", "LATE", "EXPIRED", "FUTURE"}


@pytest.mark.postgres
def test_same_fingerprint_independent_provenance_kept_and_forwarding_not_double_counted(bootstrapped):
    first = auth_event("a")
    second = first.model_copy(
        update={
            "event_id": "independent",
            "origin_event_id": "b",
            "collector_id": "sensor-suricata",
            "source_type": "suricata",
            "provenance_group": "independent",
        }
    )
    third = second.model_copy(
        update={"event_id": "forwarded", "origin_event_id": "c", "provenance_group": first.provenance_group}
    )
    assert first.fingerprint == second.fingerprint == third.fingerprint
    save(bootstrapped, [first, second, third])
    process(bootstrapped)
    with Session(bootstrapped) as db:
        assert db.scalar(select(func.count()).select_from(EventRow)) == 3
        state = db.scalars(select(GroupStateRow)).one()
        assert state.summary["event_count"] == 3 and state.summary["independent_sources"] == 2


@pytest.mark.postgres
def test_concurrent_workers_and_restart_no_duplicate_decisions(bootstrapped):
    save(bootstrapped, [auth_event(str(i), seconds=i) for i in range(10)])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: process(bootstrapped), range(2)))
    assert sum(x["processed"] for x in results) == 10
    assert sum(x["groups_created"] for x in results) == 1
    bootstrapped.dispose()
    assert process(bootstrapped)["processed"] == 0
    with Session(bootstrapped) as db:
        assert db.scalar(select(func.count()).select_from(EventGroupRow)) == 1
        assert db.scalar(select(func.count()).select_from(CorrelationDecisionRow)) == 1


@pytest.mark.postgres
def test_worker_crash_before_outbox_commit_rolls_back_and_retries(bootstrapped, monkeypatch):
    save(bootstrapped, [auth_event("a")])
    original = __import__("zhiyu.services.event_intelligence", fromlist=["publish_change"]).publish_change

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        if kwargs["kind"] == "CorrelationDecision":
            raise RuntimeError("crash")

    monkeypatch.setattr("zhiyu.services.event_intelligence.publish_change", fail)
    with pytest.raises(RuntimeError, match="crash"):
        process(bootstrapped)
    with Session(bootstrapped) as db:
        for row in (EventGroupRow, CorrelationDecisionRow, GroupMemberRow):
            assert db.scalar(select(func.count()).select_from(row)) == 0
    monkeypatch.setattr("zhiyu.services.event_intelligence.publish_change", original)
    assert process(bootstrapped)["groups_created"] == 1


@pytest.mark.postgres
def test_backlog_batches_do_not_split_an_already_arrived_window(bootstrapped):
    save(bootstrapped, [auth_event(str(i)) for i in range(5)])
    assert process(bootstrapped, now=NOW + timedelta(hours=1), limit=2)["pending"] == 3
    assert process(bootstrapped, now=NOW + timedelta(hours=1), limit=2)["groups_created"] == 0
    assert process(bootstrapped, now=NOW + timedelta(hours=1), limit=2)["groups_created"] == 0
    with Session(bootstrapped) as db:
        state = db.scalars(select(GroupStateRow)).one()
        assert state.status == "CLOSED" and state.summary["event_count"] == 5


@pytest.mark.postgres
def test_group_membership_fk_unique_and_environment_isolation(bootstrapped, bundle):
    from zhiyu.core.errors import AccessDenied
    from zhiyu.services.bootstrap import BootstrapService

    other = copy.deepcopy(bundle)
    other.environment.environment_id = "other"
    for resource in other.resources:
        resource.environment_id = "other"
    for scope in other.scopes:
        scope.environment_id = "other"
    with Session(bootstrapped) as db:
        BootstrapService(db).apply(other, actor_id="test")
    p = sensor_principal().model_copy(update={"environment_ids": frozenset({"lab-zhiyu-01", "other"})})
    event = auth_event("a")
    other_event = event.model_copy(update={"event_id": "other-event", "environment_id": "other"})
    save(bootstrapped, [event, other_event], p)
    process(bootstrapped)
    with Session(bootstrapped) as db:
        with pytest.raises(AccessDenied):
            EventIntelligenceEngine(db).process("other", principal=sensor_principal(), now=NOW)
        result = EventIntelligenceEngine(db).process("other", principal=p, now=NOW + timedelta(seconds=60))
    with Session(bootstrapped) as db, pytest.raises(IntegrityError), db.begin():
        db.execute(
            update(GroupMemberRow)
            .where(GroupMemberRow.environment_id == "lab-zhiyu-01")
            .values(group_id=result["group_ids"][0])
        )
