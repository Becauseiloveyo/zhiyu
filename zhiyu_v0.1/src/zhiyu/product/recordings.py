"""Read-only, operator-pinned recordings. No upload, execution, ingestion or fact write path."""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.db.models import IncidentRow
from zhiyu.product import queries, registry, snapshots
from zhiyu.product.access import Access, RecordingRegistration, visible_incidents
from zhiyu.product.contracts import Query, Snapshot


def entries(db: Session, access: Access) -> dict[str, RecordingRegistration]:
    """A completed archive step pins one server-named file; no user path or mutable catalog."""
    from zhiyu.db.demo_control import DemoRunRow, DemoStepRow
    from zhiyu.product.access import product_settings
    from zhiyu.product.demo_contracts import TEMPLATES

    result = {
        key: value
        for key, value in product_settings.recordings.items()
        if safe_identifier(key) and allowed(value, access)
    }
    if not product_settings.demo_profiles or not re.fullmatch(
        r"m6-real-demo-[a-f0-9]{32}", access.environment_id
    ):
        return result
    run = db.get(DemoRunRow, access.environment_id.removeprefix("m6-real-"))
    if not run or run.status != "COMPLETED":
        return result
    profile = product_settings.demo_profiles.get(run.profile_id)
    step = db.get(DemoStepRow, (run.run_id, 3))
    if (
        not profile
        or profile.environment_id != run.environment_id
        or profile.scope_id != run.scope_id
        or (
            not step
            or step.status != "COMPLETED"
            or not re.fullmatch(r"[a-f0-9]{64}", step.output.get("artifact_sha256") or "")
        )
    ):
        return result
    entry = RecordingRegistration(
        environment_id=access.environment_id,
        scope_id=run.scope_id,
        title=f"场景 {run.scenario_id} · {TEMPLATES[run.scenario_id]['title']} · {run.actual_outcome}",
        filename=run.run_id + ".json",
        sha256=step.output["artifact_sha256"],
        source_run_id=run.run_id,
        model_source=run.model_source,
    )
    if allowed(entry, access):
        result[run.run_id] = entry
    return result


def allowed(entry: RecordingRegistration, access: Access) -> bool:
    return entry.environment_id == access.environment_id and (
        access.unrestricted or entry.scope_id in access.scope_ids
    )


def _validate_source(source: Snapshot, entry: RecordingRegistration, access: Access) -> None:
    if (
        source.environment_id != entry.environment_id
        or source.scope_id != entry.scope_id
        or source.run_mode != "LIVE"
        or source.recording_id is not None
        or len(source.facts) > 2000
        or len({fact.ref for fact in source.facts}) != len(source.facts)
        or source.content_sha256 != snapshots.digest([f.model_dump(mode="json") for f in source.facts])
    ):
        raise ValueError("recording_identity_or_integrity")
    roots = [f for f in source.facts if f.kind == "incident"]
    if len(roots) != 1 or roots[0].id != source.incident_id:
        raise ValueError("recording_root")
    resources: set[str] = set()
    for fact in source.facts:
        if fact.kind not in registry.SPECS or fact.ref != f"{fact.kind}:{source.environment_id}:{fact.id}":
            raise ValueError("recording_reference")
        permitted = set(registry.SPECS[fact.kind][2].split()) | {
            "display_truncated_fields",
            "reference_completeness",
        }
        if fact.kind in {"analysis", "proposal"}:
            permitted |= {"confidence_semantics", "semantic_correctness"}
        if fact.kind == "analysis":
            permitted |= {
                "incident_summary",
                "uncertainty",
                "hypotheses",
                "confidence_semantics",
                "semantic_correctness",
            }
        if fact.kind == "proposal":
            permitted |= {"objective", "reasoning_summary"}
        if not set(fact.fields) <= permitted:
            raise ValueError("recording_fields")
        if fact.kind == "resource":
            resources.add(fact.id)
        for key in ("affected_asset_ids", "source_resource_ids", "target_resource_ids", "target_ids"):
            value = fact.fields.get(key, [])
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                raise ValueError("recording_resources")
            resources.update(value)
        for key in ("resource_id", "actor_resource_id"):
            if fact.fields.get(key):
                resources.add(str(fact.fields[key]))
        scope = fact.fields.get("scope_id")
        if scope and scope != entry.scope_id:
            raise ValueError("recording_scope")
        # Refuse nonfinite numbers and unexpected deep/secret fields instead of silently repairing archives.
        for key, value in fact.fields.items():
            if registry.public_value(value) != value:
                raise ValueError("recording_public_fields")
    if not access.unrestricted and not resources <= set(access.resources):
        raise HTTPException(404, "recording_not_found")


def open_recording(db: Session, identifier: str, query: Query, access: Access) -> Snapshot:
    from zhiyu.product.access import product_settings

    entry = entries(db, access).get(identifier)
    if entry is None or not allowed(entry, access):
        raise HTTPException(404, "recording_not_found")
    try:
        root = Path(product_settings.recording_root).resolve(strict=True)
        path = root / entry.filename
        if not root.is_dir() or path.is_symlink() or path.resolve(strict=True).parent != root:
            raise ValueError("recording_path")
        with path.open("rb") as handle:
            body = handle.read(snapshots.MAX_BYTES + 1)
        if len(body) > snapshots.MAX_BYTES or hashlib.sha256(body).hexdigest() != entry.sha256:
            raise ValueError("recording_hash_or_size")
        source = Snapshot.model_validate_json(body)
        json.dumps(source.model_dump(mode="json"), allow_nan=False)
        _validate_source(source, entry, access)
    except (OSError, ValueError, TypeError):
        raise HTTPException(422, "recording_invalid_or_unavailable") from None
    # Revoked/deleted canonical objects do not remain visible through a historical archive.
    if (
        db.scalar(
            select(IncidentRow.incident_id).where(
                *visible_incidents(access), IncidentRow.incident_id == source.incident_id
            )
        )
        is None
    ):
        raise HTTPException(404, "recording_not_found")
    now = datetime.now(UTC)
    result = source.model_copy(
        update={
            "snapshot_id": uuid4().hex,
            "expires_at": now + timedelta(seconds=snapshots.TTL),
            "run_mode": "RECORDED_REPLAY",
            "access_policy_version": access.version,
            "recording_id": identifier,
            "recording_sha256": entry.sha256,
            "source_snapshot_id": source.snapshot_id,
            "source_run_id": entry.source_run_id,
            "model_source": entry.model_source,
        }
    )
    snapshots.put(result, queries.binding(query, access))
    return result


def safe_identifier(value: str) -> bool:
    return re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", value) is not None
