"""Acceptance-only adapter: append actual HTTP path observations for the real Wazuh agent."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from zhiyu.response.lab_target import LabState, make_server


def main():
    if os.environ.get("ZHIYU_LAB_DISPOSABLE_TARGET") != "1":
        raise SystemExit("isolated target opt-in required")
    state = LabState(os.environ["ZHIYU_LAB_ENVIRONMENT"], "target-a")
    server = make_server("0.0.0.0", 8081, state, Path("/run/secrets/lab-control").read_text().strip())
    original = server.RequestHandlerClass.reply
    log = Path("/lab-logs/auth.json")
    log.parent.mkdir(parents=True, exist_ok=True)

    def reply(self, status, value):
        if self.path == "/health" and Path("/tmp/business-down").exists():
            status = 503
        if self.path in {"/attack", "/health"}:
            record = {
                "event": "zhiyu_lab_path",
                "timestamp": datetime.now(UTC).isoformat(),
                "path": self.path,
                "http_status": str(status),
                "srcip": self.client_address[0],
                "srcport": str(self.client_address[1]),
                "dstip": self.connection.getsockname()[0],
                "dstport": "8081",
                "request_id": "real-path-" + uuid4().hex,
            }
            with log.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")
                stream.flush()
        return original(self, status, value)

    server.RequestHandlerClass.reply = reply
    server.serve_forever()


if __name__ == "__main__":
    main()
