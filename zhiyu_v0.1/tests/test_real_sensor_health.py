import copy
import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def evaluate(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "tools"))
    return importlib.import_module("m6_sensor_verification").health_from_proof


def proof(now):
    return {
        "observed_at": now.isoformat(),
        "expected_requests": ["real-request"],
        "processes": {name: {"running": True} for name in ["suricata", "wazuh-manager", "wazuh-agent"]},
        "suricata": {
            "stats": {
                "timestamp": now.isoformat(),
                "stats": {"capture": {"kernel_drops": 0}, "decoder": {"invalid": 0}},
            },
            "seen_requests": ["real-request"],
            "last_event_at": now.isoformat(),
        },
        "wazuh": {
            "agent_status": {"data": {"status": "Active", "lastKeepAlive": str(int(now.timestamp()))}},
            "seen_requests": ["real-request"],
            "last_event_at": now.isoformat(),
        },
    }


@pytest.mark.parametrize("component", ["suricata", "wazuh-manager", "wazuh-agent"])
def test_healthy_process_label_cannot_override_an_actual_stopped_component(evaluate, component):
    now = datetime(2026, 9, 17, tzinfo=UTC)
    observed = proof(now)
    assert all(row.status == "HEALTHY" for row in evaluate("m6-real-test", observed, "hash", now))
    observed["processes"][component]["running"] = False
    rows = evaluate("m6-real-test", observed, "hash", now)
    source = "suricata" if component == "suricata" else "wazuh"
    unavailable = next(row for row in rows if row.sensor_id == "sensor-" + source)
    assert unavailable.status == "OFFLINE" and not unavailable.coverage_validated


def test_fresh_heartbeat_is_insufficient_with_missing_events_or_capture_loss(evaluate):
    now = datetime(2026, 9, 17, tzinfo=UTC)
    original = proof(now)
    missing = copy.deepcopy(original)
    missing["wazuh"]["seen_requests"] = []
    assert evaluate("m6-real-test", missing, "hash", now)[1].status == "DEGRADED"
    assert evaluate("m6-real-test", missing, "hash", now)[1].lost_event_count == 1
    truncated = copy.deepcopy(original)
    truncated["suricata"]["stats"]["stats"]["decoder"]["invalid"] = 1
    assert evaluate("m6-real-test", truncated, "hash", now)[0].status == "DEGRADED"
    assert not evaluate("m6-real-test", truncated, "hash", now)[0].coverage_validated


def test_stale_and_future_observation_do_not_become_current_health(evaluate):
    now = datetime(2026, 9, 17, tzinfo=UTC)
    observed = proof(now)
    assert all(
        row.status != "HEALTHY"
        for row in evaluate("m6-real-test", observed, "hash", now + timedelta(seconds=121))
    )
    assert all(
        row.status != "HEALTHY"
        for row in evaluate("m6-real-test", observed, "hash", now - timedelta(seconds=1))
    )
