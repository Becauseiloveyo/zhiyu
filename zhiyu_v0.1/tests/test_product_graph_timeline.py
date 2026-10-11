"""Same-snapshot, bounded graph neighbourhoods and explicit timeline provenance."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from test_product_projections import material, node

from zhiyu.product import projections
from zhiyu.product.registry import fact


def test_two_hop_initial_view_expansion_stays_on_same_material():
    snapshot = material(
        [
            node("incident", "incident"),
            node("task", "t", incident_id="incident"),
            node("action", "a", task_id="t"),
            node("attempt", "p", action_id="a"),
            node("result", "p", execution_outcome="EXECUTION_SUCCESS"),
        ]
    )
    first = projections.graph(snapshot)
    assert {n["kind"] for n in first["nodes"]} == {"incident", "task", "action"}
    assert max(n["distance"] for n in first["nodes"]) == 2
    assert first["frontier"] == [{"node_ref": "action:env:a", "remaining_neighbors": 1}]
    expanded = projections.graph(snapshot, "attempt:env:p")
    assert {n["kind"] for n in expanded["nodes"]} == {"task", "action", "attempt", "result"}
    assert first["snapshot_id"] == expanded["snapshot_id"]
    assert first["content_sha256"] == expanded["content_sha256"]
    assert any(edge["relation"] == "EXECUTION_RECEIPT" for edge in expanded["edges"])


@pytest.mark.parametrize(
    "root,depth,code", [("incident:foreign:incident", 2, 404), ("missing", 2, 404), (None, 3, 422)]
)
def test_expansion_rejects_unavailable_root_or_excessive_depth(root, depth, code):
    with pytest.raises(HTTPException) as raised:
        projections.graph(material([node("incident", "incident")]), root, depth)
    assert raised.value.status_code == code


def test_reference_class_does_not_promote_model_inference_to_observation():
    model = node("analysis", "guess", incident_id="incident", state_entity_id="state").model_copy(
        update={"basis": "MODEL_INFERENCE"}
    )
    result = projections.graph(material([node("incident", "incident"), model, node("state", "state")]))
    assert any(edge["semantic_class"] == "MODEL_INFERENCE" for edge in result["edges"])
    assert all(edge["basis"] == "EXPLICIT_REFERENCE" and not edge["causal"] for edge in result["edges"])
    assert next(n for n in result["nodes"] if n["kind"] == "analysis")["basis"] == "MODEL_INFERENCE"


def test_unknown_relation_retains_source_but_cannot_become_attack_causality():
    snapshot = material(
        [
            node("state", "s"),
            node("state", "t"),
            node(
                "state_relation",
                "r",
                source_entity_id="s",
                destination_entity_id="t",
                relation_type="attacked-with-certainty",
            ),
        ]
    )
    graph = projections.graph(snapshot, "state:env:s")
    relation = next(edge for edge in graph["edges"] if edge["relation"] == "UNKNOWN_STATE_RELATION")
    assert relation["semantic_class"] == "UNKNOWN" and relation["source_ref"] == "state_relation:env:r"
    assert relation["source_field"] == "source_entity_id/destination_entity_id/relation_type"
    assert graph["causal_attack_path"] == "NOT_ESTABLISHED"


def test_event_resource_conflict_is_unresolved_not_a_silent_source_target_swap():
    snapshot = material(
        [
            node("event", "e", source_resource_ids=["host"], target_resource_ids=[]),
            node("event_resource", "e:TARGET:host", role="TARGET", resource_id="host"),
            node("resource", "host"),
        ]
    )
    graph = projections.graph(snapshot)
    assert not graph["edges"] and graph["unresolved_count"] == 1


def test_compound_check_id_is_stable_and_linked_to_real_observation():
    now = datetime.now(UTC)
    checks = [
        fact("check", {"spec_id": spec, "check_id": "security", "status": "SUCCEEDED"}, "env", now)
        for spec in ("one", "two")
    ]
    snapshot = material(
        [*checks, node("observation", "ev", spec_id="two", check_id="security"), node("evidence", "ev")]
    )
    graph = projections.graph(snapshot, "observation:env:ev")
    edge = next(edge for edge in graph["edges"] if edge["relation"] == "CHECK_OBSERVATION")
    assert edge["target"] == "check:env:two:security"
    assert len({check.ref for check in checks}) == 2
    assert any(edge["relation"] == "OBSERVATION_EVIDENCE" for edge in graph["edges"])


def test_namespace_distinguishes_same_id_and_zero_depth_has_no_invented_edges():
    snapshot = material(
        [node("incident", "incident", affected_asset_ids=["incident"]), node("resource", "incident")]
    )
    full = projections.graph(snapshot)
    assert {n["id"] for n in full["nodes"]} == {"incident:env:incident", "resource:env:incident"}
    root_only = projections.graph(snapshot, depth=0)
    assert len(root_only["nodes"]) == 1 and not root_only["edges"] and root_only["truncated"]


def test_large_neighbourhood_outputs_and_candidate_work_are_bounded():
    snapshot = material(
        [
            node("incident", "incident"),
            *[
                node("task", str(i), incident_id="incident", evidence_ids=[str(j) for j in range(40)])
                for i in range(1000)
            ],
            *[node("evidence", str(j), incident_id="incident") for j in range(40)],
        ]
    )
    result = projections.graph(snapshot)
    assert len(result["nodes"]) <= 200 and len(result["edges"]) <= 400
    assert result["truncated"] and result["limits"]["candidate_edges"] == 10000
    assert all(
        edge["source"] in {n["id"] for n in result["nodes"]}
        and edge["target"] in {n["id"] for n in result["nodes"]}
        for edge in result["edges"]
    )


def test_timeline_contract_uses_only_recorded_timestamp_and_actor_and_evidence():
    snapshot = material(
        [
            node(
                "verification",
                "v",
                finished_at="2026-10-01T00:00:00Z",
                status="INCONCLUSIVE",
                evidence_ids=["ev"],
                claim="Observability unavailable",
            ),
            node(
                "audit",
                "audit",
                timestamp="2026-10-01T00:00:01Z",
                actor_id="reviewer",
                operation="ReviewRecorded",
            ),
            node("proposal", "rejected", status="REJECTED"),
        ]
    )
    entries = projections.timeline(snapshot)["entries"]
    assert len(entries) == 2
    assert entries[0]["stage"] == "VERIFICATION" and entries[0]["object_type"] == "verification"
    assert entries[0]["object_ref"] == "verification:env:v" and entries[0]["evidence_refs"] == [
        "evidence:env:ev"
    ]
    assert entries[0]["time_semantics"] == "finished_at" and entries[0]["status"] == "INCONCLUSIVE"
    assert entries[1]["actor_source"] == "reviewer" and entries[1]["event_type"] == "ReviewRecorded"
    assert all(row["causal_order"] == "NOT_ESTABLISHED" for row in entries)
