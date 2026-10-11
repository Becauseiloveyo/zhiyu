"""Archive validation and replay side-effect boundaries using canonical PostgreSQL facts."""

import hashlib
import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_incident_api import http_chain
from test_product_api import client as shared_client
from test_product_api import get

from zhiyu.db.models import ActionRow, AuditEntryRow, EventRow, ModelRunRow, VerificationResultRow
from zhiyu.product import snapshots
from zhiyu.product.access import RecordingRegistration, product_settings

pytestmark = pytest.mark.postgres


@pytest.fixture(name="client")
def product_client_fixture(bootstrapped, monkeypatch):
    yield from shared_client.__wrapped__(bootstrapped, monkeypatch)


@pytest.fixture
def archive(client, tmp_path, monkeypatch):
    incident = http_chain(client)
    source = get(client, f"/incidents/{incident}/snapshot", scope_id="scope-lab-web").json()
    path = tmp_path / "recording.json"
    body = json.dumps(source, ensure_ascii=False).encode()
    path.write_bytes(body)
    registration = RecordingRegistration(
        environment_id=source["environment_id"],
        scope_id=source["scope_id"],
        title="Recorded core ingestion",
        filename=path.name,
        sha256=hashlib.sha256(body).hexdigest(),
        source_run_id="test-canonical-capture",
        model_source="NONE",
    )
    monkeypatch.setattr(product_settings, "recording_root", str(tmp_path))
    monkeypatch.setattr(product_settings, "recordings", {"case": registration})
    return source, path, registration


def test_replay_all_views_preserve_source_and_create_no_business_or_model_objects(
    client, archive, bootstrapped
):
    source, _, _ = archive
    models = (EventRow, ActionRow, VerificationResultRow, ModelRunRow, AuditEntryRow)
    with Session(bootstrapped) as db:
        before = [db.scalar(select(func.count()).select_from(model)) for model in models]
    catalog = get(client, "/recordings").json()
    assert len(catalog["items"]) == 1
    assert catalog["projection_version"] == "0.9.0" and catalog["run_mode"] == "LIVE"
    opened = get(client, "/recordings/case/snapshot", scope_id="scope-lab-web")
    assert opened.status_code == 200, opened.text
    replay = opened.json()
    assert replay["run_mode"] == "RECORDED_REPLAY" and replay["source_snapshot_id"] == source["snapshot_id"]
    assert replay["facts"] == source["facts"] and replay["as_of"] == source["as_of"]
    assert replay["content_sha256"] == source["content_sha256"]
    for suffix in ("graph", "timeline", "ai", "verification", "report", "report-json", "report-markdown"):
        response = get(client, f"/snapshots/{replay['snapshot_id']}/{suffix}", scope_id="scope-lab-web")
        assert response.status_code == 200, response.text
        assert "RECORDED_REPLAY" in response.text
    with Session(bootstrapped) as db:
        assert before == [db.scalar(select(func.count()).select_from(model)) for model in models]


@pytest.mark.parametrize(
    "change", ["bytes", "content_hash", "environment", "scope", "private_field", "mode", "oversize"]
)
def test_recording_tamper_or_invalid_schema_is_rejected_even_when_operator_pins_file(
    client, archive, monkeypatch, change
):
    source, path, registration = archive
    if change == "bytes":
        path.write_bytes(b"tampered")
    else:
        if change == "content_hash":
            source["facts"][0]["fields"]["title"] = "tampered title"
        if change == "environment":
            source["environment_id"] = "other"
        if change == "scope":
            source["scope_id"] = "other"
        if change == "mode":
            source["run_mode"] = "RECORDED_REPLAY"
        if change == "private_field":
            source["facts"][0]["fields"]["raw_content"] = "not allowed in console"
            source["content_sha256"] = snapshots.digest(source["facts"])
        body = b" " * (snapshots.MAX_BYTES + 1) if change == "oversize" else json.dumps(source).encode()
        path.write_bytes(body)
        monkeypatch.setattr(
            product_settings,
            "recordings",
            {"case": registration.model_copy(update={"sha256": hashlib.sha256(body).hexdigest()})},
        )
    assert get(client, "/recordings/case/snapshot", scope_id="scope-lab-web").status_code == 422


def test_replay_revocation_and_scope_isolation(client, archive, monkeypatch):
    assert get(client, "/recordings/case/snapshot", environment_id="other").status_code == 403
    assert get(client, "/recordings/case/snapshot", scope_id="other").status_code == 403
    opened = get(client, "/recordings/case/snapshot", scope_id="scope-lab-web").json()
    monkeypatch.setattr(product_settings, "grants", {})
    assert get(client, "/recordings/case/snapshot").status_code == 403
    assert get(client, f"/snapshots/{opened['snapshot_id']}/report").status_code == 403


def test_archive_path_is_not_client_controlled():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RecordingRegistration(
            environment_id="env",
            scope_id="scope",
            title="x",
            filename="../private.json",
            sha256="a" * 64,
            source_run_id="run",
            model_source="NONE",
        )
