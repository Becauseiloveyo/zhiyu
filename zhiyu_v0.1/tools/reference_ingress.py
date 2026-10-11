"""Fixed TCP ingress for a loopback-only Reference deployment.

Only this credential-free relay joins the host ingress network. The API,
canonical database, model and Lab remain on their original internal networks.
No request may choose an upstream host, port, command or network.
"""

import selectors
import socket
import socketserver
import threading
import time

ROUTES = {5432: ("canonical-postgres", 5432), 8000: ("api", 8000)}
LIMIT = threading.BoundedSemaphore(64)


def relay(client, upstream, *, idle_seconds=120):
    """Forward bounded chunks and preserve TCP half-close in either direction."""
    peers = {client: upstream, upstream: client}
    for peer in peers:
        peer.settimeout(30)
    last = time.monotonic()
    with selectors.DefaultSelector() as events:
        for peer in peers:
            events.register(peer, selectors.EVENT_READ)
        while events.get_map():
            if time.monotonic() - last > idle_seconds:
                return
            for key, _ in events.select(timeout=1):
                data = key.fileobj.recv(65536)
                if data:
                    peers[key.fileobj].sendall(data)
                    last = time.monotonic()
                else:
                    events.unregister(key.fileobj)
                    peers[key.fileobj].shutdown(socket.SHUT_WR)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        if not LIMIT.acquire(blocking=False):
            return
        try:
            with socket.create_connection(ROUTES[self.server.server_address[1]], timeout=5) as upstream:
                relay(self.request, upstream)
        except (OSError, TimeoutError):
            # No payloads, credentials or connection diagnostics enter public logs.
            return
        finally:
            LIMIT.release()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    servers = [Server(("0.0.0.0", port), Handler) for port in ROUTES]
    try:
        for server in servers:
            threading.Thread(target=server.serve_forever, daemon=True).start()
        threading.Event().wait()
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
