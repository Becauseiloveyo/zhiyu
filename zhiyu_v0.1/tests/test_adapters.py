import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from conftest import ROOT
from jsonschema import Draft202012Validator

from zhiyu.adapters.base import (
    MAPPING_VERSION,
    PARSER_VERSION,
    SURICATA_SEVERITY,
    WAZUH_SEVERITY,
    AdapterContext,
    AdapterError,
    severity,
)
from zhiyu.adapters.registry import AdapterRegistry

FIXTURES = ROOT / "tests/fixtures"
CASES = sorted([*FIXTURES.glob("suricata/*/raw.json"), *FIXTURES.glob("wazuh/*/raw.json")])
NOW = datetime(2026, 9, 13, 10, tzinfo=UTC)


def context(source="suricata"):
    return AdapterContext(
        "lab-zhiyu-01",
        "sensor-" + source,
        source,
        NOW,
        "db://raw_records/test",
        "sensor-" + source,
        "SYNTHETIC",
        resource_by_ip={"10.77.20.10": "target-a"},
    )


def raw(source="suricata", case="alert"):
    return json.loads((FIXTURES / source / case / "raw.json").read_text())


def normalize(value, ctx=None):
    return AdapterRegistry().normalize(json.dumps(value), ctx or context())


@pytest.mark.parametrize("path", CASES, ids=lambda p: "/".join(p.parts[-3:-1]))
def test_golden_mapping_and_contract(path):
    source = path.parts[-3]
    text = path.read_text()
    event = AdapterRegistry().normalize(text, context(source))
    expected = json.loads(path.with_name("expected.json").read_text())
    assert {key: event.model_dump(mode="json")[key] for key in expected} == expected
    assert event.environment_id == "lab-zhiyu-01"
    assert event.source_type == source and event.collector_id == "sensor-" + source
    assert event.raw_ref == "db://raw_records/test"
    assert event.source_timestamp == NOW and event.ingested_at == NOW and event.clock_status == "TRUSTED"
    assert event.parser_version == PARSER_VERSION and event.mapping_version == MAPPING_VERSION
    assert event.validation_run_id is None and event.data_origin == "SYNTHETIC"
    assert event.provenance_group == "sensor-" + source and event.origin_event_id
    schema = json.loads((ROOT / "baseline/ai5/zhiyu.schema.json").read_text())
    Draft202012Validator(schema).validate(event.model_dump(mode="json"))
    if source == "suricata":
        assert event.target_resource_ids == ["target-a"]
        assert any(x.value == "transport=TCP" or x.value == "transport=UDP" for x in event.observables)


@pytest.mark.parametrize(
    "value,expected",
    [(1, 9), (2, 6), (3, 3), (4, 1), (0, 0), (99, 0), ("invalid", 0), (None, 0), (True, 0), (1.5, 0)],
)
def test_suricata_severity(value, expected):
    assert severity(value, SURICATA_SEVERITY) == expected


@pytest.mark.parametrize("value", range(16))
def test_wazuh_severity(value):
    assert severity(value, WAZUH_SEVERITY) == round(value * 10 / 15)


@pytest.mark.parametrize(
    "time,clock",
    [
        ("2026-09-13T10:00:00Z", "TRUSTED"),
        ("2026-09-13T18:00:00+08:00", "TRUSTED"),
        ("2026-09-13T11:00:00Z", "SKEWED"),
        ("2026-09-11T10:00:00Z", "SKEWED"),
    ],
)
def test_source_clock(time, clock):
    value = raw()
    value["timestamp"] = time
    event = normalize(value)
    assert event.clock_status == clock and event.ingested_at == NOW
    assert event.source_timestamp == datetime.fromisoformat(time.replace("Z", "+00:00"))


@pytest.mark.parametrize("value", ["2026-09-13T10:00:00", "nonsense", None, 1234, "2026-99-13T10:00:00Z"])
def test_invalid_timestamps(value):
    event = raw()
    event["timestamp"] = value
    with pytest.raises(AdapterError, match="invalid_timestamp"):
        normalize(event)


@pytest.mark.parametrize("text", ["{bad", "[]", "null", '{"x":NaN}', '{"event_type":"x","event_type":"y"}'])
def test_malformed_json(text):
    with pytest.raises(AdapterError, match="malformed_json"):
        AdapterRegistry().normalize(text, context())


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("src_ip", "999.3.4.5", "invalid_ip"),
        ("proto", "LIES", "invalid_protocol"),
        ("src_port", 70000, "invalid_protocol"),
        ("event_type", None, "missing_required_identity"),
        ("alert", [], "mapping_error"),
    ],
)
def test_structured_field_errors(field, value, code):
    event = raw()
    event[field] = value
    with pytest.raises(AdapterError, match=code):
        normalize(event)


def test_unknown_source_and_missing_context():
    with pytest.raises(AdapterError, match="unsupported_event_type"):
        normalize(raw(), context("absent"))
    with pytest.raises(AdapterError, match="missing_required_identity"):
        normalize(raw(), replace(context(), collector_id=""))


def test_independent_provenance_replay_and_shared_flow():
    value = raw()
    value["flow_id"] = 42
    one = normalize(value)
    assert one.event_id == normalize(value, replace(context(), ingested_at=NOW + timedelta(days=2))).event_id
    independent = normalize(value, replace(context(), collector_id="another", provenance_root="independent"))
    assert one.fingerprint == independent.fingerprint and one.event_id != independent.event_id
    value["timestamp"] = "2026-09-13T10:00:01Z"
    assert one.event_id != normalize(value).event_id


def test_vendor_labels_do_not_authorize_or_invent_attack():
    value = raw()
    value.update(validation_run_id="forged", provenance_group="trusted", environment_id="other")
    result = normalize(value)
    assert result.validation_run_id is None and result.environment_id == "lab-zhiyu-01"
    assert result.provenance_group == "sensor-suricata"
    assert not any("mitre" in x.value for x in result.observables)
    assert any(x.value == "vendor.severity=1" for x in result.observables)


def test_wazuh_missing_and_heterogeneous_fields():
    with pytest.raises(AdapterError, match="missing_required_identity"):
        normalize({"timestamp": NOW.isoformat()}, context("wazuh"))
    for field in ("data", "agent", "rule"):
        value = raw("wazuh", "ssh")
        value[field] = []
        with pytest.raises(AdapterError, match="mapping_error"):
            normalize(value, context("wazuh"))


@pytest.mark.parametrize("source", ["suricata", "wazuh"])
@pytest.mark.parametrize("level", [True, 1.5, 999, "unrated"])
def test_unknown_severity_falls_back_without_losing_original(source, level):
    value = raw(source, "alert" if source == "suricata" else "ssh")
    value["alert" if source == "suricata" else "rule"]["severity" if source == "suricata" else "level"] = (
        level
    )
    event = normalize(value, context(source))
    assert event.severity_signal == 0
    assert any(x.value == "vendor.severity=" + str(level).lower() for x in event.observables)
