"""Isolated acceptance target. Fixed HEAD health endpoint; no mutable management interface."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        status = 200 if self.path == "/health" else 404
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()
        print(json.dumps({"method": "HEAD", "path": self.path, "status": status}), flush=True)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8081), Handler).serve_forever()
