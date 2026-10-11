"""Pure presentation projections from one immutable, already authorized snapshot."""

from collections import defaultdict, deque
from typing import Any

from fastapi import HTTPException

from zhiyu.product.contracts import Snapshot
from zhiyu.product.snapshots import digest

# A timestamp is never synthesized from adjacent stages. All values retain their original semantics.
TIMES = (
    "source_timestamp",
    "received_at",
    "ingested_at",
    "observed_at",
    "collected_at",
    "first_observed_at",
    "first_seen_at",
    "last_seen_at",
    "created_at",
    "triaged_at",
    "investigation_started_at",
    "queued_at",
    "claimed_at",
    "started_at",
    "approved_at",
    "finished_at",
    "completed_at",
    "checked_at",
    "contained_at",
    "resolved_at",
    "closed_at",
    "updated_at",
    "timestamp",
)

STAGES = {
    "raw": "DETECTION",
    "normalization": "NORMALIZATION",
    "event": "NORMALIZATION",
    "event_resource": "NORMALIZATION",
    "group": "CORRELATION",
    "group_member": "CORRELATION",
    "correlation": "CORRELATION",
    "incident": "INCIDENT",
    "context": "CONTEXT",
    "ai_context": "CONTEXT",
    "model_request": "AI_ANALYSIS",
    "model_receipt": "AI_ANALYSIS",
    "model_run": "AI_ANALYSIS",
    "analysis": "AI_ANALYSIS",
    "proposal": "PROPOSAL",
    "decision": "PROPOSAL",
    "plan": "PROPOSAL",
    "authorization_context": "AUTHORIZATION",
    "authorization": "AUTHORIZATION",
    "risk": "AUTHORIZATION",
    "approval": "HUMAN_REVIEW",
    "task": "ACTION",
    "action": "ACTION",
    "attempt": "ACTION",
    "result": "ACTION",
    "verification_spec": "VERIFICATION",
    "check": "VERIFICATION",
    "observation": "VERIFICATION",
    "verification": "VERIFICATION",
    "state": "STATE_UPDATE",
    "state_update": "STATE_UPDATE",
    "state_relation": "STATE_UPDATE",
    "replan": "REPLAN",
    "audit": "AUDIT",
    "evidence": "EVIDENCE",
}


def meta(snapshot: Snapshot) -> dict[str, Any]:
    return snapshot.model_dump(mode="json", exclude={"facts"})


def timeline(snapshot: Snapshot) -> dict[str, Any]:
    entries = []
    for fact in snapshot.facts:
        for semantics in TIMES:
            at = fact.fields.get(semantics)
            if at:
                entries.append(
                    {
                        "id": digest([fact.ref, semantics, at]),
                        "source_ref": fact.ref,
                        "object_ref": fact.ref,
                        "object_type": fact.kind,
                        "stage": STAGES.get(fact.kind, "UNKNOWN"),
                        "event_type": fact.fields.get("event_type", fact.fields.get("operation", fact.kind)),
                        "actor_source": next(
                            (
                                fact.fields[key]
                                for key in ("actor_id", "collector_id", "provider", "executor")
                                if fact.fields.get(key)
                            ),
                            None,
                        ),
                        "summary": next(
                            (
                                fact.fields[key]
                                for key in ("title", "claim", "reason", "operation")
                                if fact.fields.get(key)
                            ),
                            None,
                        ),
                        "evidence_refs": [
                            f"evidence:{snapshot.environment_id}:{identifier}"
                            for identifier in fact.fields.get("evidence_ids", [])[:20]
                        ],
                        "evidence_refs_truncated": len(fact.fields.get("evidence_ids", [])) > 20,
                        "kind": fact.kind,
                        "at": at,
                        "time_semantics": semantics,
                        "basis": fact.basis,
                        "clock_status": fact.fields.get("clock_status", "NOT_RECORDED"),
                        "provenance_group": fact.fields.get("provenance_group"),
                        "data_origin": fact.fields.get("data_origin", "NOT_RECORDED"),
                        "freshness": fact.freshness,
                        "status": fact.fields.get(
                            "status", fact.fields.get("outcome", fact.fields.get("execution_outcome"))
                        ),
                        "operation": fact.fields.get("operation"),
                        "causal_order": "NOT_ESTABLISHED",
                    }
                )
    # UTC offsets may differ. Sort by actual instant, then stable ref/semantics, not text or stage.
    from datetime import datetime

    entries.sort(
        key=lambda row: (datetime.fromisoformat(row["at"]), row["source_ref"], row["time_semantics"])
    )
    return {
        **meta(snapshot),
        "entries": entries[:2000],
        "truncated": snapshot.truncated or len(entries) > 2000,
        "returned_count": min(len(entries), 2000),
        "entry_limit": 2000,
    }


# key -> (destination kind, relation). These are record references, never attack causality.
REFS = {
    "incident_id": ("incident", "BELONGS_TO_INCIDENT"),
    "context_id": ("ai_context", "ANALYSIS_CONTEXT"),
    "request_id": ("model_request", "MODEL_REQUEST"),
    "model_run_id": ("model_run", "MODEL_RUN"),
    "analysis_id": ("analysis", "ANALYSIS_REFERENCE"),
    "state_entity_id": ("state", "PRODUCED_STATE"),
    "plan_id": ("plan", "PLAN_REFERENCE"),
    "task_id": ("task", "TASK_REFERENCE"),
    "action_id": ("action", "ACTION_REFERENCE"),
    "authorization_context_id": ("authorization_context", "AUTHORIZATION_CONTEXT"),
    "approval_id": ("approval", "APPROVAL_REFERENCE"),
    "raw_id": ("raw", "NORMALIZED_FROM"),
    "event_id": ("event", "EVENT_REFERENCE"),
    "group_id": ("group", "MEMBER_OF"),
    "output_group_id": ("group", "CORRELATION_GROUP"),
    "verification_spec_id": ("verification_spec", "CHECKS_SPEC"),
    "spec_id": ("verification_spec", "CHECKS_SPEC"),
    "action_result_id": ("result", "ACTION_RESULT"),
    "parent_verification_id": ("verification", "REPLAN_AFTER"),
    "root_plan_id": ("plan", "ROOT_PLAN"),
    "parent_plan_id": ("plan", "PARENT_PLAN"),
    "new_plan_id": ("plan", "REPLANNED_TO"),
    "source_entity_id": ("state", "RELATION_SOURCE"),
    "destination_entity_id": ("state", "RELATION_DESTINATION"),
    "actor_resource_id": ("resource", "EVENT_ACTOR"),
}
LIST_REFS = {
    "affected_asset_ids": ("resource", "AFFECTS_RESOURCE"),
    "target_resource_ids": ("resource", "TARGETS_RESOURCE"),
    "target_ids": ("resource", "VERIFIES_RESOURCE"),
    "source_event_ids": ("event", "EVIDENCE_FROM"),
    "member_event_ids": ("event", "HAS_MEMBER"),
    "outlier_event_ids": ("event", "OUTLIER_REFERENCE"),
    "input_event_ids": ("event", "INPUT_REFERENCE"),
    "excluded_event_ids": ("event", "EXCLUDED_REFERENCE"),
    "evidence_ids": ("evidence", "EVIDENCE_REFERENCE"),
    "entity_ids": ("state", "PRODUCED_STATE"),
}


def graph(snapshot: Snapshot, root_ref: str | None = None, depth: int = 2) -> dict[str, Any]:
    """Bounded, undirected neighbourhood selection; edge direction retains the recorded reference.

    Expanding changes the root inside the SAME snapshot. No SQL recursion, node accumulation,
    guessed connections or unrelated live fetch. Candidate work is capped independently of output.
    """
    if depth not in (0, 1, 2):
        raise HTTPException(422, "graph_depth_out_of_bounds")
    by_ref = {fact.ref: fact for fact in snapshot.facts}
    if root_ref is not None and root_ref not in by_ref:
        raise HTTPException(404, "graph_root_not_in_snapshot")
    canonical_root = f"incident:{snapshot.environment_id}:{snapshot.incident_id}"
    root_ref = root_ref or (canonical_root if canonical_root in by_ref else None)
    refs = set(by_ref)
    edges: list[dict[str, Any]] = []
    unresolved = 0
    candidates = 0
    candidate_limit = 10000
    seen_edges: set[str] = set()

    def edge(
        source: str,
        destination_kind: str,
        identifier: str,
        relation: str,
        field: str,
        provenance: str | None = None,
    ) -> None:
        nonlocal unresolved, candidates
        if not identifier:
            return
        destination = f"{destination_kind}:{snapshot.environment_id}:{identifier}"
        if destination not in refs or source not in refs:
            unresolved += 1
            return
        identity = digest([source, field, destination, relation])
        if identity in seen_edges:
            return
        seen_edges.add(identity)
        candidates += 1
        record = by_ref[provenance or source]
        if len(edges) < candidate_limit:
            edges.append(
                {
                    "id": identity,
                    "source": source,
                    "target": destination,
                    "relation": relation,
                    "source_ref": record.ref,
                    "source_field": field,
                    "basis": "EXPLICIT_REFERENCE",
                    "semantic_class": "UNKNOWN" if relation == "UNKNOWN_STATE_RELATION" else record.basis,
                    "freshness": record.freshness,
                    "evidence_refs": [
                        f"evidence:{snapshot.environment_id}:{value}"
                        for value in record.fields.get("evidence_ids", [])[:20]
                    ],
                    "observed_at": record.fields.get("observed_at"),
                    "valid_until": record.fields.get("valid_until"),
                    "causal": False,
                }
            )

    for fact in snapshot.facts:
        if candidates >= candidate_limit:
            break
        for field, (kind, relation) in REFS.items():
            if fact.fields.get(field):
                edge(fact.ref, kind, fact.fields[field], relation, field)
        for field, (kind, relation) in LIST_REFS.items():
            if fact.kind == "event" and field == "target_resource_ids":
                continue
            for identifier in fact.fields.get(field, []):
                edge(fact.ref, kind, identifier, relation, field)
        if fact.kind == "event_resource":
            # Only materialized event_resources links authorize a source/target graph edge.
            event_id = fact.id.rsplit(":" + fact.fields["role"] + ":", 1)[0]
            source = f"event:{snapshot.environment_id}:{event_id}"
            if source in refs:
                list_field = {"SOURCE": "source_resource_ids", "TARGET": "target_resource_ids"}.get(
                    fact.fields["role"]
                )
                if list_field is None or fact.fields["resource_id"] not in by_ref[source].fields.get(
                    list_field, []
                ):
                    unresolved += 1
                    continue
                edge(
                    source,
                    "resource",
                    fact.fields["resource_id"],
                    "EVENT_" + fact.fields["role"],
                    fact.ref + ".resource_id",
                    fact.ref,
                )
        if fact.kind == "model_receipt":
            edge(fact.ref, "model_request", fact.id, "MODEL_REQUEST", "request_id")
        if fact.kind == "result":
            edge(fact.ref, "attempt", fact.id, "EXECUTION_RECEIPT", "attempt_id")
        if fact.kind in {"state_update", "replan"}:
            edge(fact.ref, "verification", fact.id, "VERIFICATION_RESULT", "verification_id")
        if fact.kind == "observation":
            edge(
                fact.ref,
                "check",
                fact.fields["spec_id"] + ":" + fact.fields["check_id"],
                "CHECK_OBSERVATION",
                "spec_id/check_id",
            )
            edge(fact.ref, "evidence", fact.id, "OBSERVATION_EVIDENCE", "evidence_id")
        if fact.kind == "state_relation":
            known = fact.fields.get("relation_type") in {
                "SUPPORTS",
                "CONTRADICTS",
                "RELATED_TO",
                "DEPENDS_ON",
            }
            source = f"state:{snapshot.environment_id}:{fact.fields['source_entity_id']}"
            edge(
                source,
                "state",
                fact.fields["destination_entity_id"],
                fact.fields["relation_type"] if known else "UNKNOWN_STATE_RELATION",
                "source_entity_id/destination_entity_id/relation_type",
                fact.ref,
            )

    adjacency: dict[str, set[str]] = defaultdict(set)
    for item in edges:
        adjacency[item["source"]].add(item["target"])
        adjacency[item["target"]].add(item["source"])
    selected: dict[str, int] = {}
    if root_ref:
        queue = deque([(root_ref, 0)])
        while queue and len(selected) < 200:
            ref, distance = queue.popleft()
            if ref in selected:
                continue
            selected[ref] = distance
            if distance < depth:
                queue.extend(
                    (neighbor, distance + 1)
                    for neighbor in sorted(adjacency[ref])
                    if neighbor not in selected
                )
    else:
        # Empty/partial input has no incident root. Keep isolated records without inventing a root edge.
        selected = {fact.ref: 0 for fact in snapshot.facts[:200]}
    visible_edges = [item for item in edges if item["source"] in selected and item["target"] in selected]
    frontier = [
        {"node_ref": ref, "remaining_neighbors": len(adjacency[ref] - selected.keys())}
        for ref in selected
        if adjacency[ref] - selected.keys()
    ]
    nodes = [
        {
            "id": fact.ref,
            "kind": fact.kind,
            "source_ref": fact.ref,
            "label": fact.id,
            "basis": fact.basis,
            "freshness": fact.freshness,
            "fields": fact.fields,
            "distance": selected[fact.ref],
        }
        for fact in (by_ref[ref] for ref in selected)
    ]
    return {
        **meta(snapshot),
        "nodes": nodes,
        "edges": visible_edges[:400],
        "root_ref": root_ref,
        "frontier": frontier,
        "snapshot_node_count": len(snapshot.facts),
        "unshown_node_count": len(snapshot.facts) - len(nodes),
        "causal_attack_path": "NOT_ESTABLISHED",
        "unresolved_count": unresolved,
        "truncated": snapshot.truncated
        or len(snapshot.facts) > len(nodes)
        or len(visible_edges) > 400
        or candidates >= candidate_limit,
        "limits": {"nodes": 200, "edges": 400, "depth": depth, "candidate_edges": candidate_limit},
        "history_completeness": "PARTIAL",
    }


def section(snapshot: Snapshot, kinds: set[str]) -> dict[str, Any]:
    return {**meta(snapshot), "facts": [f.model_dump(mode="json") for f in snapshot.facts if f.kind in kinds]}
