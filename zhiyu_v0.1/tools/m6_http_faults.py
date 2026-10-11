"""Finite HTTP transport faults in an isolated container; scripted output is not AI."""

import io
import json
import socket
import struct
import time
from datetime import UTC, datetime
from http.server import ThreadingHTTPServer

from model_fault_fixture import Handler as ValidHandler


class Handler(ValidHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 131072:
            self.send_error(413)
            return
        body_bytes = self.rfile.read(length)
        body = json.loads(body_bytes)
        mode = body["model"]
        print(
            json.dumps(
                {
                    "mode": mode,
                    "observed_at": datetime.now(UTC).isoformat(),
                    "data_origin": "SCRIPTED_TRANSPORT_FAULT",
                }
            ),
            flush=True,
        )
        if mode == "M6_RESET":
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            self.connection.close()
            return
        if mode == "M6_TIMEOUT":
            time.sleep(3)
        if mode in {"M6_LATENCY", "SCRIPTED_VALID"} or not mode.startswith("M6_"):
            if mode == "M6_LATENCY":
                time.sleep(0.5)
            # Delegate the exact existing controlled valid schema without duplicating it.
            original = self.rfile
            self.rfile = io.BytesIO(body_bytes)
            try:
                return super().do_POST()
            finally:
                self.rfile = original
        status = 503 if mode == "M6_HTTP" else 200
        envelope = {"choices": [{"message": {"role": "assistant", "content": "{}"}, "finish_reason": "stop"}]}
        if mode == "M6_REFUSAL":
            envelope["choices"][0]["message"]["refusal"] = "Controlled refusal fixture"
        if mode == "M6_PARTIAL":
            envelope["choices"][0]["message"]["content"] = '{"incident_summary":'
            envelope["choices"][0]["finish_reason"] = "length"
        payload = b'{"unfinished":' if mode == "M6_MALFORMED" else json.dumps(envelope).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
