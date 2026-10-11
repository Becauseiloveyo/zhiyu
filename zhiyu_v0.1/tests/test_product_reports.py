import hashlib
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_incident_api import http_chain
from test_product_api import client as shared_client
from test_product_api import get
from test_product_projections import material, node

from zhiyu.db.models import ActionRow, AuditEntryRow, IncidentRow
from zhiyu.product import reports, snapshots
from zhiyu.product.access import product_settings


def source(**fields):
    return material(
        [node("incident", "incident", title="Test incident", status="NEW", priority="P2", **fields)]
    )


def test_deterministic_json_markdown_export_hashes_and_snapshot_identity():
    snapshot = source(number=1.0)
    report = reports.build(snapshot)
    assert reports.build(snapshot) == report
    exported = reports.json_export(report)
    value = json.loads(exported["content"])
    report_hash = value.pop("report_sha256")
    assert snapshots.digest(value) == report_hash == report.report_sha256
    assert value["snapshot"]["facts"] == snapshot.model_dump(mode="json")["facts"]
    assert value["content_sha256"] == snapshot.content_sha256
    md = reports.markdown(report)
    for result in (exported, md):
        assert result["export_sha256"] == hashlib.sha256(result["content"].encode()).hexdigest()
        assert result["snapshot_id"] == snapshot.snapshot_id and result["report_sha256"] == report_hash
    assert snapshot.content_sha256 in md["content"]
    assert md["content"].count("\n## ") == 8


def test_markdown_escapes_html_links_and_headings_from_untrusted_records():
    snapshot = source()
    changed = snapshot.facts[0].model_copy(
        update={"fields": {"title": "<script>alert(1)</script>\n[x](javascript:alert(1))\n# false heading"}}
    )
    report = reports.build(material([changed]))
    content = reports.markdown(report)["content"]
    assert (
        "<script>" not in content and "[x](javascript:" not in content and "\n# false heading" not in content
    )
    assert "&lt;script&gt;" in content and "\\[x\\]" in content


@pytest.mark.parametrize("status", ["PASS", "FAIL"])
def test_execution_success_cannot_overwrite_fail_or_expired_pass(status):
    snapshot = material(
        [
            *source().facts,
            node("result", "r", execution_outcome="EXECUTION_SUCCESS"),
            node(
                "verification",
                "v",
                status=status,
                security_status=status,
                business_status="PASS",
                observation_status="PASS",
            ).model_copy(update={"freshness": "EXPIRED"}),
        ]
    )
    report = reports.build(snapshot)
    assert report.summary["overall_security_claim"] == "NOT_INFERRED_FROM_EXECUTION"
    result = report.summary["verification_results"][0]
    assert result["status"] == status and result["freshness_at_snapshot"] == "EXPIRED"
    assert reports.cell("EXECUTION_SUCCESS") in reports.markdown(report)["content"]


def test_report_rejects_changed_facts_with_unchanged_content_hash():
    with pytest.raises(HTTPException) as raised:
        reports.build(source().model_copy(update={"facts": [node("incident", "incident", title="tampered")]}))
    assert raised.value.status_code == 422
    assert raised.value.detail == "snapshot_integrity_failed"


def test_missing_evidence_is_explicit_and_never_backfilled():
    report = reports.build(source())
    assert not next(section.source_refs for section in report.sections if section.id == "evidence")
    assert "本快照未读取到对应记录" in reports.markdown(report)["content"]
    assert report.reviewer is None and report.report_status == "UNREVIEWED_DRAFT"


def test_report_requires_real_incident_root():
    with pytest.raises(HTTPException) as raised:
        reports.build(material([node("evidence", "e")]))
    assert raised.value.status_code == 422


def test_report_has_hard_byte_budget(monkeypatch):
    monkeypatch.setattr(reports, "MAX_REPORT_BYTES", 100)
    with pytest.raises(HTTPException) as raised:
        reports.build(source())
    assert raised.value.status_code == 413


@pytest.fixture(name="client")
def product_client_fixture(bootstrapped, monkeypatch):
    yield from shared_client.__wrapped__(bootstrapped, monkeypatch)


@pytest.mark.postgres
def test_formats_share_snapshot_after_database_changes_and_have_no_business_effects(client, bootstrapped):
    incident = http_chain(client)
    snapshot = get(client, f"/incidents/{incident}/snapshot").json()
    with Session(bootstrapped) as db:
        db.get(IncidentRow, incident).title = "new canonical title after capture"
        db.commit()
        counts = [db.scalar(select(func.count()).select_from(model)) for model in (ActionRow, AuditEntryRow)]
    base = "/snapshots/" + snapshot["snapshot_id"]
    results = {
        suffix: get(client, base + "/" + suffix) for suffix in ("report", "report-json", "report-markdown")
    }
    assert all(result.status_code == 200 for result in results.values())
    report = results["report"].json()
    assert report["snapshot"]["facts"] == snapshot["facts"]
    assert "new canonical title after capture" not in results["report-markdown"].text
    for suffix in ("report-json", "report-markdown"):
        export = results[suffix].json()
        assert export["report_sha256"] == report["report_sha256"]
        assert export["export_sha256"] == hashlib.sha256(export["content"].encode()).hexdigest()
    with Session(bootstrapped) as db:
        assert counts == [
            db.scalar(select(func.count()).select_from(model)) for model in (ActionRow, AuditEntryRow)
        ]


@pytest.mark.postgres
def test_report_export_rechecks_environment_scope_revocation_and_expiry(client, monkeypatch):
    incident = http_chain(client)
    snapshot = get(client, f"/incidents/{incident}/snapshot").json()
    base = "/snapshots/" + snapshot["snapshot_id"]
    for suffix in ("report", "report-json", "report-markdown"):
        assert get(client, base + "/" + suffix, environment_id="foreign").status_code == 403
        assert get(client, base + "/" + suffix, scope_id="foreign").status_code == 403
    now = snapshots.time.monotonic()
    with monkeypatch.context() as context:
        context.setattr(snapshots.time, "monotonic", lambda: now + 301)
        assert get(client, base + "/report-json").status_code == 410
    monkeypatch.setattr(product_settings, "grants", {})
    assert get(client, base + "/report-markdown").status_code == 403
