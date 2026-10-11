"""Product DTOs; independent of, and never replacements for, ai.5 contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReadGrant(DTO):
    version: str = Field(min_length=1, max_length=80)
    scope_ids: frozenset[str] = frozenset()
    whole_environment: bool = False


class Query(DTO):
    environment_id: str = Field(min_length=1, max_length=160)
    scope_id: str | None = Field(default=None, min_length=1, max_length=160)
    hours: int = Field(default=24, ge=1, le=168)
    status: (
        Literal[
            "NEW",
            "TRIAGED",
            "INVESTIGATING",
            "PLANNED",
            "WAITING_APPROVAL",
            "EXECUTING",
            "VERIFYING",
            "CONTAINED",
            "RESOLVED",
            "CLOSED",
            "HUMAN_REVIEW",
            "REOPENED",
        ]
        | None
    ) = None
    priority: Literal["P0", "P1", "P2", "P3", "P4"] | None = None
    search: str = Field(default="", max_length=120)
    sort: Literal["created_desc", "created_asc"] = "created_desc"


class Fact(DTO):
    """Fields follow the explicit kind registry; no ORM/object serialization."""

    ref: str
    kind: str
    id: str
    fields: dict[str, Any]
    basis: Literal["OBSERVED", "DERIVED", "MODEL_INFERENCE", "UNKNOWN"]
    freshness: Literal["CURRENT", "EXPIRED", "UNKNOWN"]


class Envelope(DTO):
    projection_version: Literal["0.9.0"] = "0.9.0"
    environment_id: str
    scope_id: str | None
    access_policy_version: str
    as_of: datetime
    consistency: Literal["LIVE_PAGE", "IMMUTABLE_SNAPSHOT"]
    run_mode: Literal["LIVE", "RECORDED_REPLAY"] = "LIVE"


class IncidentPage(Envelope):
    items: list[dict[str, Any]]
    next_cursor: str | None = None


class SnapshotMetadata(Envelope):
    snapshot_id: str
    expires_at: datetime
    content_sha256: str
    incident_id: str
    truncated: bool
    omitted_count: int | None
    history_completeness: Literal["PARTIAL"] = "PARTIAL"
    limits: dict[str, int]
    recording_id: str | None = None
    recording_sha256: str | None = None
    source_snapshot_id: str | None = None
    source_run_id: str | None = None
    model_source: str | None = None


class Snapshot(SnapshotMetadata):
    facts: list[Fact]


class TimelineEntry(DTO):
    id: str
    source_ref: str
    object_ref: str
    object_type: str
    stage: str
    event_type: str
    actor_source: str | None
    summary: str | None
    evidence_refs: list[str]
    evidence_refs_truncated: bool
    kind: str
    at: datetime
    time_semantics: str
    basis: Literal["OBSERVED", "DERIVED", "MODEL_INFERENCE", "UNKNOWN"]
    clock_status: str
    provenance_group: str | None
    data_origin: str
    freshness: Literal["CURRENT", "EXPIRED", "UNKNOWN"]
    status: str | None
    operation: str | None
    causal_order: Literal["NOT_ESTABLISHED"]


class TimelinePage(SnapshotMetadata):
    items: list[TimelineEntry]
    next_cursor: str | None
    returned_count: int
    entry_limit: int


class GraphNode(DTO):
    id: str
    kind: str
    source_ref: str
    label: str
    basis: Literal["OBSERVED", "DERIVED", "MODEL_INFERENCE", "UNKNOWN"]
    freshness: Literal["CURRENT", "EXPIRED", "UNKNOWN"]
    fields: dict[str, Any]
    distance: int = Field(ge=0, le=2)


class GraphEdge(DTO):
    id: str
    source: str
    target: str
    relation: str
    source_ref: str
    source_field: str
    basis: Literal["EXPLICIT_REFERENCE"]
    semantic_class: Literal["OBSERVED", "DERIVED", "MODEL_INFERENCE", "UNKNOWN"]
    freshness: Literal["CURRENT", "EXPIRED", "UNKNOWN"]
    evidence_refs: list[str] = Field(max_length=20)
    observed_at: datetime | None
    valid_until: datetime | None
    causal: Literal[False]


class GraphFrontier(DTO):
    node_ref: str
    remaining_neighbors: int = Field(ge=1)


class GraphProjection(SnapshotMetadata):
    nodes: list[GraphNode] = Field(max_length=200)
    edges: list[GraphEdge] = Field(max_length=400)
    root_ref: str | None
    frontier: list[GraphFrontier] = Field(max_length=200)
    snapshot_node_count: int
    unshown_node_count: int
    causal_attack_path: Literal["NOT_ESTABLISHED"]
    unresolved_count: int


class Overview(Envelope):
    metrics: dict[str, Any]
    status_counts: dict[str, int]
    daily_incidents: list[dict[str, Any]]
    formulas: dict[str, str]
    protection_score: None = None
    protection_score_status: Literal["NOT_CALCULATED"] = "NOT_CALCULATED"


class Health(Envelope):
    database: Literal["AVAILABLE"] = "AVAILABLE"
    sensors: list[dict[str, Any]]
    capabilities: list[dict[str, Any]]
    ai_mode: str
    freshness_seconds: int = 120
    truncated: bool
    runtime_status: Literal["UNKNOWN", "DEGRADED", "HEALTHY"]
    model_runtime_status: Literal["UNKNOWN"] = "UNKNOWN"
    worker_status: Literal["UNKNOWN"] = "UNKNOWN"
