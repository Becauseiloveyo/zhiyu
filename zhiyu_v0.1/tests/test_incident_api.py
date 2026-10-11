import hashlib
import json
from datetime import UTC, datetime

import pytest
from conftest import ROOT
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_raw_ingest import sensor_principal

from zhiyu.core.config import settings
from zhiyu.db.session import get_db
from zhiyu.main import app

pytestmark = pytest.mark.postgres
TOKEN = "synthetic-incident-api-token-" + "b" * 32


@pytest.fixture
def client(bootstrapped, monkeypatch):
    principal = sensor_principal()
    monkeypatch.setattr(settings, "service_tokens", {hashlib.sha256(TOKEN.encode()).hexdigest(): principal})

    def db_override():
        with Session(bootstrapped) as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    try:
        with TestClient(app, headers={"Authorization": "Bearer " + TOKEN}) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def http_chain(client):
    fixture = json.loads((ROOT / "tests/fixtures/golden_chain_m2.json").read_text(encoding="utf-8"))
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    for source in ("suricata", "wazuh"):
        records = []
        for item in fixture["records"]:
            if item["source_type"] != source:
                continue
            item["raw"]["timestamp"] = now.isoformat()
            records.append({"record": json.dumps(item["raw"]), "origin_event_id": item["origin"]})
        response = client.post(
            "/v1/events/raw-batches",
            json={
                "environment_id": "lab-zhiyu-01",
                "collector_id": "sensor-" + source,
                "source_type": source,
                "data_origin": "SYNTHETIC",
                "records": records,
            },
        )
        assert response.status_code == 202 and response.json()["errors"] == 0
    response = client.post("/v1/intelligence/process", json={"environment_id": "lab-zhiyu-01"})
    assert response.status_code == 200
    result = response.json()
    assert result["incidents"]["created"] == 1
    return next(x["incident_id"] for x in result["incidents"]["results"] if x["incident_id"])


def test_http_raw_to_incident_pagination_filters_and_lifecycle(client):
    identifier = http_chain(client)
    listed = client.get(
        "/v1/incidents", params={"environment_id": "lab-zhiyu-01", "status": "NEW", "min_risk": 60}
    ).json()
    assert [x["incident_id"] for x in listed["items"]] == [identifier]
    assert (
        client.get("/v1/incidents", params={"environment_id": "lab-zhiyu-01", "min_risk": 90}).json()["items"]
        == []
    )
    assert client.get("/v1/incidents/" + identifier).json()["status"] == "NEW"
    assessment = client.get("/v1/incidents/" + identifier + "/assessment").json()["risk"]
    assert assessment["score"] == 62 and assessment["factors"]["verified_raw_count"] == 3
    first = client.get(f"/v1/incidents/{identifier}/events", params={"limit": 2}).json()
    second = client.get(
        f"/v1/incidents/{identifier}/events", params={"limit": 2, "cursor": first["next_cursor"]}
    ).json()
    assert len(first["items"]) == 2 and len(second["items"]) == 1 and second["next_cursor"] is None
    assert len({x["event_id"] for x in first["items"] + second["items"]}) == 3
    for item in first["items"] + second["items"]:
        assert item["raw_ref"].startswith("db://raw_records/")
    assert len(client.get(f"/v1/incidents/{identifier}/correlations").json()["items"]) == 1
    assert len(client.get(f"/v1/incidents/{identifier}/evidence").json()["items"]) == 3
    for target, version in [("TRIAGED", 1), ("INVESTIGATING", 2)]:
        body = {"environment_id": "lab-zhiyu-01", "target": target, "expected_version": version}
        response = client.post(f"/v1/incidents/{identifier}/transitions", json=body)
        assert response.status_code == 200 and response.json()["state_version"] == version + 1
        assert (
            client.post(f"/v1/incidents/{identifier}/transitions", json=body).json()["state_version"]
            == version + 1
        )
    replay = client.post("/v1/intelligence/process", json={"environment_id": "lab-zhiyu-01"}).json()
    assert replay["correlation"]["processed"] == replay["incidents"]["evaluated"] == 0
    measured = client.get("/v1/intelligence/metrics", params={"environment_id": "lab-zhiyu-01"}).json()
    assert measured["raw_event_count"] == 4 and measured["event_group_count"] == 2


def test_http_no_cross_environment_leak_and_invalid_pages(client, monkeypatch):
    identifier = http_chain(client)
    assert client.get("/v1/incidents", params={"environment_id": "other"}).status_code == 403
    for params in ({"limit": 0}, {"limit": 201}, {"cursor": "not-a-cursor"}):
        assert client.get(f"/v1/incidents/{identifier}/events", params=params).status_code == 422
    other = sensor_principal().model_copy(update={"environment_ids": frozenset({"other"})})
    monkeypatch.setattr(settings, "service_tokens", {hashlib.sha256(TOKEN.encode()).hexdigest(): other})
    for suffix in ("", "/events", "/correlations", "/evidence", "/assessment"):
        assert client.get("/v1/incidents/" + identifier + suffix).status_code == 404
    assert client.post("/v1/intelligence/process", json={"environment_id": "lab-zhiyu-01"}).status_code == 403


def test_http_malformed_item_preserved_and_good_neighbor_accepted(client):
    fixture = json.loads((ROOT / "tests/fixtures/suricata/alert/raw.json").read_text())
    fixture["timestamp"] = datetime.now(UTC).isoformat()
    result = client.post(
        "/v1/events/raw-batches",
        json={
            "environment_id": "lab-zhiyu-01",
            "collector_id": "sensor-suricata",
            "source_type": "suricata",
            "data_origin": "SYNTHETIC",
            "records": [{"record": "{broken"}, {"record": json.dumps(fixture)}],
        },
    )
    assert result.status_code == 202
    assert (result.json()["accepted"], result.json()["errors"]) == (1, 1)
    assert result.json()["results"][0]["raw_ref"].startswith("db://raw_records/")
