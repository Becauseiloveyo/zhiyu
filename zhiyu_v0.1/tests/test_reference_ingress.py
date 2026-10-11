"""Exercise transport half-close and reject absent/non-loopback publications."""

import importlib.util
import socket
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize("bindings", [None, [], [{"HostIp": "0.0.0.0", "HostPort": "5432"}],
                                     [{"HostIp": "127.0.0.1", "HostPort": ""}]])
def test_unusable_database_publication_rejected(bindings):
    profile = module("release_profile")
    with pytest.raises(RuntimeError, match="reference_port_not_loopback_published"):
        profile.loopback_port({"NetworkSettings": {"Ports": {"5432/tcp": bindings}}}, "5432/tcp")


def test_multi_chunk_request_half_close_preserves_full_response():
    ingress = module("reference_ingress")
    client, relay_client = socket.socketpair()
    upstream, relay_upstream = socket.socketpair()
    request, response = bytes(range(256)) * 1025, b"response-after-request-eof" * 10000
    errors = []

    def forward():
        try:
            ingress.relay(relay_client, relay_upstream, idle_seconds=5)
        except Exception as exc:
            errors.append(exc)
        finally:
            relay_client.close()
            relay_upstream.close()

    def backend():
        received = bytearray()
        with upstream:
            while chunk := upstream.recv(65536):
                received.extend(chunk)
            if bytes(received) != request:
                errors.append(AssertionError("request truncated"))
            upstream.sendall(response)
            upstream.shutdown(socket.SHUT_WR)

    threads = [threading.Thread(target=f) for f in (forward, backend)]
    for thread in threads:
        thread.start()
    with client:
        client.settimeout(5)
        client.sendall(request)
        client.shutdown(socket.SHUT_WR)
        received = bytearray()
        while chunk := client.recv(65536):
            received.extend(chunk)
    for thread in threads:
        thread.join(timeout=6)
        assert not thread.is_alive()
    assert not errors
    assert bytes(received) == response
