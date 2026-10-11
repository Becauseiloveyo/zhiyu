"""Acceptance-only process barriers; unavailable from the product API or image entrypoint."""

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from sqlalchemy import event

from zhiyu.ai.provider import OpenAICompatibleProvider
from zhiyu.db.session import get_engine

CONTROL = Path("/fault-control")


def barrier(stage, statement=""):
    armed = CONTROL / "armed.json"
    if not armed.exists():
        return
    payload = json.loads(armed.read_text())
    if payload["stage"] != stage or not statement.lower().startswith(payload.get("sql_prefix", "").lower()):
        return
    try:
        armed.rename(CONTROL / (payload["case"] + ".armed.json"))
    except FileNotFoundError:
        return
    (CONTROL / (payload["case"] + ".hit.json")).write_text(
        json.dumps(
            {
                "case": payload["case"],
                "stage": stage,
                "pid": os.getpid(),
                "hit_at": datetime.now(UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    # The host sends SIGKILL after the durable marker, never an arbitrary timing guess.
    time.sleep(45)
    raise RuntimeError("acceptance process barrier was not killed by its controller")


def after_sql(connection, cursor, statement, parameters, context, many):
    barrier("after_sql", statement)


if __name__ == "__main__":
    if os.environ.get("ZHIYU_M6_FAULT_LAB") != "1" or not CONTROL.is_dir():
        raise RuntimeError("isolated M6 fault lab required")
    key_path = os.environ.get("ZHIYU_MODEL_KEY_FILE")
    if key_path:
        os.environ["ZHIYU_LOCAL_MODEL_KEY"] = Path(key_path).read_text().strip()
    event.listen(get_engine(), "after_cursor_execute", after_sql)
    complete = OpenAICompatibleProvider.complete

    def response_barrier(self, config, request):
        result = complete(self, config, request)
        barrier("model_response")
        return result

    OpenAICompatibleProvider.complete = response_barrier
    uvicorn.run("zhiyu.main:app", host="0.0.0.0", port=8000)
