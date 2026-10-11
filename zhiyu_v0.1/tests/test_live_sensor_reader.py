"""Live sensor writes can be split across reads without becoming malformed events."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("m6_jsonl", Path(__file__).parents[1] / "tools/m6_jsonl.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
complete_records = module.complete_records


def test_partial_sensor_write_is_pending_and_full_replay_is_exact():
    first = b'{"id":"one"}\n'
    second = '{"id":"真实"}\n'.encode()
    for cut in range(1, len(second)):
        rows, pending = complete_records(first + second[:cut])
        assert rows == [(1, first[:-1], {"id": "one"})]
        assert pending["pending_bytes"] == cut
    rows, pending = complete_records(first + second)
    assert [row[1] for row in rows] == [first[:-1], second[:-1]]
    assert pending["pending_bytes"] == 0


def test_malformed_terminated_record_is_never_silently_dropped():
    with pytest.raises(ValueError):
        complete_records(b'{"id":"one"}\n{broken}\n')
