"""Disposable Lab target. Only /attack can change; /health is always independent.

No disk state, shell, firewall, forwarding or arbitrary route. Restart opens the path
and changes the epoch, invalidating every pre-restart command. TTL runs locally.
"""

import json
import os
import secrets
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import monotonic
from typing import Any
from uuid import uuid4

from zhiyu.core.canonical import canonical_hash
from zhiyu.response.lab_protocol import LabCommand


class LabState:
    def __init__(self, environment_id: str, resource_id: str) -> None:
        self.environment_id, self.resource_id = environment_id, resource_id
        self.epoch, self.generation = uuid4().hex, 0
        self.owner: str | None = None
        self.deadline = 0.0
        self.expires_at: str | None = None
        self.mutations, self.expirations = 0, 0
        self.receipts: dict[str, dict[str, Any]] = {}
        self.lock = threading.RLock()

    def _expire(self) -> None:
        if self.owner is not None and monotonic() >= self.deadline:
            self.owner, self.expires_at = None, None
            self.generation += 1
            self.expirations += 1

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            self._expire()
            state = {
                "environment_id": self.environment_id,
                "resource_id": self.resource_id,
                "epoch": self.epoch,
                "generation": self.generation,
                "owner": self.owner,
                "restricted": self.owner is not None,
                "expires_at": self.expires_at,
            }
            return {**state, "digest": canonical_hash(state)}

    def inspect(self, action_id: str | None = None) -> dict[str, Any]:
        with self.lock:
            return {
                "observed_at": datetime.now(UTC).isoformat(),
                "state": self.snapshot(),
                "receipt": self.receipts.get(action_id or ""),
                "mutations": self.mutations,
                "expirations": self.expirations,
            }

    def apply(self, command: LabCommand) -> dict[str, Any]:
        with self.lock:
            before, p = self.snapshot(), command.parameters
            if (command.environment_id, command.resource_id) != (self.environment_id, self.resource_id):
                raise ValueError("target_binding_mismatch")
            prior = self.receipts.get(command.action_id)
            if prior:
                if prior["command_hash"] != canonical_hash(command.model_dump(mode="json")):
                    raise ValueError("idempotency_identity_conflict")
                return {**prior, "duplicate": True, "current": before}
            if len(self.receipts) >= 4096:
                raise ValueError("receipt_capacity_exhausted")
            if command.expires_at.tzinfo is None or command.expires_at <= datetime.now(UTC):
                raise ValueError("expired_command")
            if (p.epoch, p.expected_generation, p.before_digest) != (
                self.epoch,
                self.generation,
                before["digest"],
            ):
                raise ValueError("state_compare_failed")
            if p.operation == "contain":
                if self.owner is not None or command.owner != "zhiyu-lab:" + command.action_id:
                    raise ValueError("ownership_conflict")
                self.owner = command.owner
                self.deadline = monotonic() + p.ttl_seconds
                self.expires_at = (datetime.now(UTC) + timedelta(seconds=p.ttl_seconds)).isoformat()
                timer = threading.Timer(p.ttl_seconds, self.snapshot)
                timer.daemon = True
                timer.start()
            else:
                if self.owner != command.owner or command.owner != "zhiyu-lab:" + str(p.prior_action_id):
                    raise ValueError("foreign_owner_compensation_refused")
                self.owner, self.expires_at = None, None
            self.generation += 1
            self.mutations += 1
            result = {
                "action_id": command.action_id,
                "action_digest": command.action_digest,
                "command_hash": canonical_hash(command.model_dump(mode="json")),
                "before": before,
                "intended": {"restricted": p.operation == "contain", "owner": self.owner},
                "after": self.snapshot(),
                "duplicate": False,
                "mutations": self.mutations,
            }
            self.receipts[command.action_id] = result
            return result


def make_server(address: str, port: int, state: LabState, token: str) -> ThreadingHTTPServer:
    if len(token) < 32:
        raise ValueError("Lab control token must contain at least 32 characters")

    class Handler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(2)

        def log_message(self, *args: Any) -> None:
            pass

        def reply(self, status: int, value: dict[str, Any]) -> None:
            body = json.dumps(value, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def authorized(self) -> bool:
            return secrets.compare_digest(self.headers.get("X-Zhiyu-Lab-Control", ""), token)

        def do_HEAD(self) -> None:
            self.do_GET()

        def do_GET(self) -> None:
            if self.path in {"/health", "/attack"}:
                restricted = self.path == "/attack" and state.snapshot()["restricted"]
                self.reply(403 if restricted else 200, {"path": self.path})
            elif self.path == "/control" and self.authorized():
                self.reply(200, state.inspect(self.headers.get("X-Action-Id")))
            else:
                self.reply(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if self.path != "/control" or not self.authorized():
                self.reply(404, {"error": "not_found"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096 or self.headers.get("Transfer-Encoding"):
                    raise ValueError("invalid_length")
                command = LabCommand.model_validate_json(self.rfile.read(size))
                self.reply(200, state.apply(command))
            except (ValueError, TimeoutError):
                self.reply(409, {"error": "command_rejected"})

    return ThreadingHTTPServer((address, port), Handler)


def main() -> None:
    # Explicit Lab deployment is mandatory; this service is not included in the default stack.
    if os.environ.get("ZHIYU_LAB_DISPOSABLE_TARGET") != "1":
        raise SystemExit("disposable Lab opt-in required")
    state = LabState(os.environ["ZHIYU_LAB_ENVIRONMENT"], os.environ["ZHIYU_LAB_RESOURCE"])
    server = make_server("0.0.0.0", 8080, state, os.environ["ZHIYU_LAB_CONTROL_TOKEN"])
    server.serve_forever()


if __name__ == "__main__":
    main()
