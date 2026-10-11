import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session
from starlette.requests import Request
from test_incident_api import http_chain
from test_product_api import ENV, PARAMS, get
from test_product_api import client as shared_client
from test_raw_ingest import sensor_principal

from zhiyu.api.routes import product
from zhiyu.db.infrastructure import EventResourceRow
from zhiyu.db.models import EventRow, IncidentRow, ResourceRow
from zhiyu.product import queries, snapshots
from zhiyu.product.access import authorize
from zhiyu.product.contracts import Query

pytestmark = pytest.mark.postgres


@pytest.fixture(name="client")
def product_client_fixture(bootstrapped, monkeypatch):
    yield from shared_client.__wrapped__(bootstrapped, monkeypatch)


def test_projection_views_share_snapshot_and_timeline_pages(client):
    incident = http_chain(client)
    snapshot = get(client, f"/incidents/{incident}/snapshot").json()
    base = "/snapshots/" + snapshot["snapshot_id"]
    results = {
        view: get(client, base + "/" + view) for view in ("timeline", "graph", "ai", "verification", "report")
    }
    for result in results.values():
        assert result.status_code == 200, result.text
        assert result.json()["content_sha256"] == snapshot["content_sha256"]
        assert result.json()["as_of"] == snapshot["as_of"]
    first = get(client, base + "/timeline", limit=2).json()
    second = get(client, base + "/timeline", limit=2, cursor=first["next_cursor"]).json()
    assert not {i["id"] for i in first["items"]}.intersection(i["id"] for i in second["items"])
    other = get(client, f"/incidents/{incident}/snapshot").json()["snapshot_id"]
    assert get(client, f"/snapshots/{other}/timeline", cursor=first["next_cursor"]).status_code == 422
    assert get(client, base + "/graph", scope_id="forbidden").status_code == 403
    scenarios = client.get("/v1/product/demo-scenarios", params={"environment_id": ENV})
    assert scenarios.status_code == 200
    assert scenarios.json()["browser_lifecycle"] == "READ_ONLY_REGISTRY"
    assert scenarios.json()["demo_catalog"] == "/v1/product/demos/catalog"
    assert scenarios.json()["execution_available"] is False
    assert client.get("/v1/product/demo-scenarios", params={"environment_id": "other"}).status_code == 403


@pytest.mark.parametrize("corruption", ["missing-event", "unbound-event", "actor-outside-scope"])
def test_unknown_and_foreign_references_fail_closed(client, bootstrapped, corruption):
    incident = http_chain(client)
    with Session(bootstrapped) as db:
        row = db.get(IncidentRow, incident)
        if corruption == "missing-event":
            row.related_event_ids = [*row.related_event_ids, "private-missing-event"]
        elif corruption == "unbound-event":
            for association in db.scalars(select(EventResourceRow)):
                db.delete(association)
        else:
            source = db.scalars(select(ResourceRow)).first()
            values = {c.name: getattr(source, c.name) for c in ResourceRow.__table__.columns}
            db.add(ResourceRow(**{**values, "resource_id": "private-actor"}))
            db.flush()
            original = db.scalars(select(EventRow)).first()
            event_values = {c.name: getattr(original, c.name) for c in EventRow.__table__.columns}
            db.add(
                EventRow(
                    **{
                        **event_values,
                        "event_id": "actor-test-event",
                        "actor_resource_id": "private-actor",
                        "origin_event_id": "actor-test-origin",
                        "fingerprint": hashlib.sha256(b"actor-test-event").hexdigest(),
                    }
                )
            )
            db.flush()
            for relation in db.scalars(
                select(EventResourceRow).where(EventResourceRow.event_id == original.event_id)
            ):
                db.add(
                    EventResourceRow(
                        environment_id=ENV,
                        event_id="actor-test-event",
                        resource_id=relation.resource_id,
                        role=relation.role,
                    )
                )
            row.related_event_ids = [*row.related_event_ids, "actor-test-event"]
        db.commit()
    assert get(client, "/incidents").json()["items"] == []
    result = get(client, f"/incidents/{incident}/snapshot")
    assert result.status_code == 404
    assert "private" not in result.text


def test_real_dependency_repeatable_read_and_capacity(client, bootstrapped, monkeypatch):
    incident = http_chain(client)
    monkeypatch.setattr(product, "get_engine", lambda: bootstrapped)
    principal = sensor_principal().model_copy(update={"permissions": {"product:read"}})
    request = Request({"type": "http", "query_string": f"environment_id={ENV}".encode(), "headers": []})
    first = product.get_product_db(request, principal)
    second = product.get_product_db(request, principal)
    db = next(first)
    next(second)
    try:
        assert db.scalar(text("SHOW transaction_read_only")) == "on"
        assert db.scalar(text("SHOW transaction_isolation")) == "repeatable read"
        assert db.scalar(text("SHOW statement_timeout")) == "2s"
        original = db.scalar(select(IncidentRow.title).where(IncidentRow.incident_id == incident))
        with Session(bootstrapped) as writer:
            writer.get(IncidentRow, incident).title = "concurrent update"
            writer.commit()
        assert db.scalar(select(IncidentRow.title).where(IncidentRow.incident_id == incident)) == original
        third = product.get_product_db(request, principal)
        with pytest.raises(HTTPException) as exc:
            next(third)
        assert exc.value.status_code == 429
    finally:
        first.close()
        second.close()


def test_ten_thousand_incidents_bounded_query_plan(client, bootstrapped):
    incident = http_chain(client)
    with Session(bootstrapped) as db:
        source = db.get(IncidentRow, incident)
        values = {c.name: getattr(source, c.name) for c in IncidentRow.__table__.columns}
        db.execute(
            IncidentRow.__table__.insert(), [{**values, "incident_id": f"load-{i:05d}"} for i in range(10000)]
        )
        db.commit()
        db.execute(text("ANALYZE incidents"))
        # Large unrelated event population; only registered fixture resources, no execution.
        source_event = db.scalar(select(EventRow.event_id).limit(1))
        names = [c.name for c in EventRow.__table__.columns]
        replacements = {
            "event_id": "'load-event-' || n",
            "origin_event_id": "'load-origin-' || n",
            "fingerprint": "md5(n::text) || md5(n::text)",
        }
        expressions = [replacements.get(name, "source." + name) for name in names]
        db.execute(
            text(
                "INSERT INTO normalized_events ("
                + ",".join(names)
                + ") SELECT "
                + ",".join(expressions)
                + " FROM normalized_events source CROSS JOIN generate_series(1,100000) n "
                + "WHERE source.event_id=:source"
            ),
            {"source": source_event},
        )
        db.commit()
        db.execute(text("ANALYZE normalized_events"))
    plans = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if not plans and statement.startswith("SELECT incidents.incident_id"):
            with cursor.connection.cursor() as explain:
                explain.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, parameters)
                plans.append(explain.fetchone()[0])

    with bootstrapped.connect() as connection:
        event.listen(connection, "before_cursor_execute", capture)
        with Session(bind=connection) as db:
            query = Query(**PARAMS)
            principal = sensor_principal().model_copy(update={"permissions": {"product:read"}})
            access = authorize(db, principal, query)
            response = queries.incident_page(db, query, access, 50, None)
            assert len(response.items) == 50 and response.next_cursor
            assert len(response.model_dump_json().encode()) < snapshots.MAX_BYTES
    assert plans and plans[0][0]["Plan"]["Actual Rows"] == 51
    path = Path(__file__).resolve().parents[1] / "artifacts/v0.9/incident-query-plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "measured_at": datetime.now(UTC).isoformat(),
                "incidents": 10001,
                "additional_events": 100000,
                "not_sla": True,
                "plan": plans,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
