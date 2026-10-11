"""Read only terminated records from a live append-only sensor file snapshot."""

import hashlib
import json


def complete_records(payload: bytes):
    boundary = payload.rfind(b"\n") + 1
    complete, pending = payload[:boundary], payload[boundary:]
    records = []
    for line, raw in enumerate(complete.splitlines(), 1):
        if raw.strip():
            records.append((line, raw, json.loads(raw)))
    return records, {"pending_bytes": len(pending), "pending_sha256": hashlib.sha256(pending).hexdigest()}
