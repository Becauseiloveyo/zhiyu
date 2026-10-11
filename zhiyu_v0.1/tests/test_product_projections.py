from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from zhiyu.product import projections, snapshots
from zhiyu.product.contracts import Fact, Query, Snapshot
from zhiyu.product.registry import fact


def material(facts):
    now = datetime.now(UTC)
    return Snapshot(
        environment_id="env",
        scope_id="scope",
        access_policy_version="1",
        as_of=now,
        consistency="IMMUTABLE_SNAPSHOT",
        snapshot_id="test",
        expires_at=now + timedelta(minutes=5),
        content_sha256=snapshots.digest([f.model_dump(mode="json") for f in facts]),
        incident_id="incident",
        facts=facts,
        truncated=False,
        omitted_count=0,
        limits={},
    )


def node(kind, identifier, **fields):
    return Fact(
        ref=f"{kind}:env:{identifier}",
        kind=kind,
        id=identifier,
        fields=fields,
        basis="DERIVED",
        freshness="UNKNOWN",
    )


def test_timeline_true_instants_ties_missing_stages_and_provenance():
    snapshot = material(
        [
            node(
                "event",
                "b",
                source_timestamp="2026-10-01T08:00:00+08:00",
                ingested_at="2026-10-01T00:00:02+00:00",
                provenance_group="p",
                clock_status="SKEWED",
            ),
            node("event", "a", source_timestamp="2026-10-01T00:00:00+00:00"),
            node("action", "no_time", status="UNKNOWN"),
        ]
    )
    rows = projections.timeline(snapshot)["entries"]
    assert [r["source_ref"] for r in rows] == ["event:env:a", "event:env:b", "event:env:b"]
    assert rows[1]["clock_status"] == "SKEWED" and rows[1]["provenance_group"] == "p"
    assert rows[-1]["time_semantics"] == "ingested_at"
    assert all(r["causal_order"] == "NOT_ESTABLISHED" for r in rows)


def test_graph_requires_actual_references_and_does_not_make_attack_edges():
    snapshot = material(
        [
            node("incident", "incident", affected_asset_ids=["host"]),
            node("resource", "host"),
            node("event", "e", source_resource_ids=["host"], target_resource_ids=["host"]),
            node("event_resource", "e:TARGET:host", resource_id="host", role="TARGET"),
            node("proposal", "rejected", status="REJECTED", plan_id=None),
            node("evidence", "ev", source_event_ids=["e", "absent"]),
        ]
    )
    graph = projections.graph(snapshot)
    assert graph["causal_attack_path"] == "NOT_ESTABLISHED"
    assert all(not e["causal"] for e in graph["edges"])
    assert all(e["target"] in {n["id"] for n in graph["nodes"]} for e in graph["edges"])
    assert any(
        e["relation"] == "EVENT_TARGET" and "event_resource:" in e["source_field"] for e in graph["edges"]
    )
    assert graph["unresolved_count"] == 1
    assert not any(e["source"] == "proposal:env:rejected" for e in graph["edges"])


def test_bounded_graph_and_timeline():
    snapshot = material([node("event", str(i), ingested_at="2026-10-01T00:00:00+00:00") for i in range(2100)])
    assert len(projections.graph(snapshot)["nodes"]) == 200
    assert projections.graph(snapshot)["truncated"]
    assert len(projections.timeline(snapshot)["entries"]) == 2000
    assert projections.timeline(snapshot)["truncated"]


def test_cache_rejects_other_reader_and_expires(monkeypatch):
    snapshot = material([node("incident", "incident")])
    snapshots.put(snapshot, "alice")
    with pytest.raises(HTTPException) as exc:
        snapshots.get(snapshot.snapshot_id, "bob")
    assert exc.value.status_code == 404
    assert snapshots.get(snapshot.snapshot_id, "alice") == snapshot
    original = snapshots.time.monotonic()
    monkeypatch.setattr(snapshots.time, "monotonic", lambda: original + 301)
    with pytest.raises(HTTPException) as exc:
        snapshots.get(snapshot.snapshot_id, "alice")
    assert exc.value.status_code == 410


def test_expired_pass_and_model_inference_are_not_promoted_to_current_observation():
    now = datetime.now(UTC)
    result = fact(
        "verification",
        {"verification_id": "v", "status": "PASS", "valid_until": now - timedelta(seconds=1)},
        "env",
        now,
    )
    assert result.fields["status"] == "PASS" and result.freshness == "EXPIRED"
    result = fact(
        "state",
        {"entity_id": "s", "entity_type": "AI_SITUATION_ANALYSIS", "claim_kind": "INFERENCE"},
        "env",
        now,
    )
    assert result.basis == "MODEL_INFERENCE"
    result = fact("evidence", {"evidence_id": "e", "claim_kind": "SOURCE_ASSERTION"}, "env", now)
    assert result.basis == "UNKNOWN"


@pytest.mark.parametrize("params", [{"hours": 0}, {"hours": 169}, {"search": "x" * 121}, {"sort": "risk"}])
def test_request_bounds(params):
    with pytest.raises(ValueError):
        Query(environment_id="env", **params)


def test_response_byte_budget():
    from zhiyu.product.budgets import response_budget
    assert response_budget({"count": 0}) == {"count": 0}
    with pytest.raises(HTTPException) as exc:
        response_budget({"text": "中" * 100}, maximum=250)
    assert exc.value.status_code == 413
