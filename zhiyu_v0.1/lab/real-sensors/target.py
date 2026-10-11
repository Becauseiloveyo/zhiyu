"""Controlled Lab service. Logs are produced by actual requests, never fixtures."""

import base64
import json
import os
import socket
import ssl
import struct
import subprocess
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = Path("/lab-logs/auth.json")
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/login"):
            # Deliberately public Lab-only account, with no host or real account access.
            expected = "Basic " + base64.b64encode(b"lab-user:lab-only-valid").decode()
            success = self.headers.get("Authorization") == expected
            record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "event": "zhiyu_login",
                "auth_result": "success" if success else "denied",
                "srcip": self.client_address[0],
                "dstip": self.connection.getsockname()[0],
                "srcport": str(self.client_address[1]),
                "dstport": str(self.server.server_port),
                "protocol": "TCP",
                "srcuser": "lab-user",
                "url": self.path,
                "request_id": self.headers.get("X-Lab-Request-ID", "unidentified"),
                "scenario": "SCN-LAB-AUTH-REAL-01",
            }
            with LOCK, LOG.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            self.send_response(200 if success else 401)
            if not success:
                self.send_header("WWW-Authenticate", 'Basic realm="zhiyu-lab"')
        else:
            self.send_response(200)
        self.send_header("Content-Length", "3")
        self.end_headers()
        self.wfile.write(b"OK\n")

    def log_message(self, pattern, *args):
        print(json.dumps({"http_log": pattern % args}), flush=True)


def dns_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind(("0.0.0.0", 53))
        while True:
            data, peer = server.recvfrom(1024)
            if len(data) < 17:
                continue
            # Answer only a single A/IN question; no recursion or external traffic.
            end = data.find(b"\x00", 12)
            if end < 0 or data[end + 1 : end + 5] != b"\x00\x01\x00\x01":
                continue
            answer = data[:2] + struct.pack("!HHHHH", 0x8180, 1, 1, 0, 0)
            answer += data[12 : end + 5] + b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 30, 4)
            answer += socket.inet_aton("10.89.60.10")
            server.sendto(answer, peer)


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.touch(exist_ok=True)
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "2",
            "-subj",
            "/CN=target.lab",
            "-keyout",
            "/tmp/lab.key",
            "-out",
            "/tmp/lab.crt",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain("/tmp/lab.crt", "/tmp/lab.key")
    https = ThreadingHTTPServer(("0.0.0.0", 8443), Handler)
    https.socket = tls.wrap_socket(https.socket, server_side=True)
    threading.Thread(target=https.serve_forever, daemon=True).start()
    threading.Thread(target=dns_server, daemon=True).start()
    print("LAB_TARGET_READY", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()


if __name__ == "__main__":
    main()
