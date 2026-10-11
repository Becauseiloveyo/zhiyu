"""Actual consumer process exit after a local idempotent test sink, before Outbox ACK."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy.orm import Session

from zhiyu.core.errors import LeaseLostError
from zhiyu.db.session import get_engine
from zhiyu.domain.contracts import OutboxMessage
from zhiyu.repositories.outbox import OutboxClaim, OutboxRepository

ROOT = Path("/fault-control/outbox")


def save(path, value):
    with path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2))
        stream.flush()
        os.fsync(stream.fileno())


def main():
    assert os.environ.get("ZHIYU_M6_FAULT_LAB") == "1"
    engine = get_engine()
    if len(sys.argv) > 1 and sys.argv[1] == "child":
        with Session(engine) as db, db.begin():
            claim = OutboxRepository(db).claim("m6-outbox-old", limit=1, lease_seconds=1)[0]
        save(
            ROOT / "old-claim.json",
            {
                "message": claim.message.model_dump(mode="json"),
                "generation": claim.generation,
                "worker_id": claim.worker_id,
            },
        )
        save(ROOT / "sink.json", {claim.message.message_id: {"logical_deliveries": 1}})
        print(
            json.dumps(
                {"boundary": "durable_test_sink_before_outbox_ack", "message_id": claim.message.message_id}
            ),
            flush=True,
        )
        os._exit(72)
    ROOT.mkdir(exist_ok=False)
    process = subprocess.run([sys.executable, __file__, "child"], capture_output=True, text=True, timeout=20)
    (ROOT / "stdout.log").write_text(process.stdout)
    (ROOT / "stderr.log").write_text(process.stderr)
    assert process.returncode == 72
    time.sleep(1.2)
    stored = json.loads((ROOT / "old-claim.json").read_text())
    old = OutboxClaim(
        OutboxMessage.model_validate(stored["message"]), stored["generation"], stored["worker_id"]
    )
    with Session(engine) as db, db.begin():
        new = OutboxRepository(db).claim("m6-outbox-replacement", limit=1)[0]
    assert new.message.message_id == old.message.message_id and new.generation == old.generation + 1
    try:
        with Session(engine) as db, db.begin():
            OutboxRepository(db).finish(old, published=True)
    except LeaseLostError:
        pass
    else:
        raise AssertionError("stale Outbox ACK accepted")
    sink = json.loads((ROOT / "sink.json").read_text())
    sink.setdefault(new.message.message_id, {"logical_deliveries": 1})
    save(ROOT / "sink.json", sink)
    with Session(engine) as db, db.begin():
        OutboxRepository(db).finish(new, published=True)
    assert len(sink) == 1
    result = {
        "status": "PASS",
        "physical_exit": process.returncode,
        "message_id": new.message.message_id,
        "recovered_generation": new.generation,
        "stale_ack_rejected": True,
        "sink": "LOCAL_FILE_IDEMPOTENT_TEST_SINK",
        "delivery_attempts": 2,
        "logical_sink_effects": 1,
    }
    save(ROOT / "result.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
