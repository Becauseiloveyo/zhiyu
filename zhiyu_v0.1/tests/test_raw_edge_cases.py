import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_adapters import raw
from test_raw_ingest import ingest

from zhiyu.db.infrastructure import RawRecordRow
from zhiyu.db.models import EventRow

pytestmark = pytest.mark.postgres


def test_invalid_unicode_and_mapped_nul_are_isolated(bootstrapped):
    result = ingest(
        bootstrapped, ["\ud800", json.dumps({**raw(), "event_type": "nul\x00"}), json.dumps(raw())]
    )
    assert (result["accepted"], result["errors"]) == (1, 2)
    assert result["results"][0]["error_code"] == "malformed_json"
    assert result["results"][1]["error_code"] == "mapping_error"
    with Session(bootstrapped) as db:
        assert b"\xed\xa0\x80" in list(db.scalars(select(RawRecordRow.content)))


def test_resource_binding_requires_endpoint_port_and_protocol(bootstrapped):
    good = raw()
    wrong_port = {**good, "dest_port": 22}
    wrong_protocol = {**good, "proto": "UDP"}
    missing_protocol = {**good}
    missing_protocol.pop("proto")
    result = ingest(
        bootstrapped, [json.dumps(x) for x in (good, wrong_port, wrong_protocol, missing_protocol)]
    )
    assert result["accepted"] == 4
    with Session(bootstrapped) as db:
        events = [db.get(EventRow, x["event_id"]) for x in result["results"]]
        assert events[0].target_resource_ids == ["target-a"]
        assert all(x.target_resource_ids == [] for x in events[1:])
