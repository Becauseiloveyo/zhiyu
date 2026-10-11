"""Five finite authentication requests and benign DNS/TLS in the internal Lab."""

import base64
import http.client
import json
import socket
import ssl
import struct
import time
from datetime import UTC, datetime


def main():
    # Fixed target; the harness cannot be pointed at external systems.
    results = []
    for index in range(5):
        success = index == 4
        auth = b"lab-user:lab-only-valid" if success else b"lab-user:deliberately-invalid"
        request_id = f"lab-{time.time_ns()}-{index}"
        connection = http.client.HTTPConnection("10.89.60.10", 8080, timeout=5)
        connection.request(
            "GET",
            "/login?request_id=" + request_id,
            headers={
                "Authorization": "Basic " + base64.b64encode(auth).decode(),
                "X-Lab-Request-ID": request_id,
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        response.read()
        assert response.status == (200 if success else 401)
        results.append(
            {
                "request_id": request_id,
                "status": response.status,
                "completed_at": datetime.now(UTC).isoformat(),
            }
        )
        connection.close()
        time.sleep(0.25)
    query = struct.pack("!HHHHHH", 4567, 0x0100, 1, 0, 0, 0) + b"\x06target\x03lab\x00\x00\x01\x00\x01"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as dns:
        dns.settimeout(5)
        dns.sendto(query, ("10.89.60.10", 53))
        answer, peer = dns.recvfrom(1024)
        assert answer[:2] == query[:2] and peer[0] == "10.89.60.10"
        results.append({"dns_response_bytes": len(answer)})
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # Self-signed certificate, fixed isolated Lab IP only.
    with socket.create_connection(("10.89.60.10", 8443), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname="target.lab") as tls:
            tls.sendall(b"GET /health HTTP/1.0\r\nHost: target.lab\r\n\r\n")
            assert b"200" in tls.recv(4096)
            results.append({"tls_version": tls.version()})
    print(json.dumps({"scenario": "SCN-LAB-AUTH-REAL-01", "requests": results}))


if __name__ == "__main__":
    main()
