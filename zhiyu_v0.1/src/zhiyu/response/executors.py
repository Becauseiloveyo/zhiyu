"""Five bounded read-only executors. No subprocess, arbitrary URL, proxy or redirect."""

import ipaddress
import socket
import ssl
from dataclasses import dataclass
from time import monotonic
from typing import Any, Literal, Protocol

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.db.infrastructure import EventResourceRow
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import EventRow, EvidenceRow, ResourceRow
from zhiyu.domain.contracts import ActionRequest, ResourceRef
from zhiyu.response.catalog import ProbeInput, ReadInput


@dataclass(frozen=True)
class ExecutorOutput:
    execution_outcome: Literal["EXECUTION_SUCCESS", "EXECUTION_FAILURE", "TIMEOUT"]
    output: dict[str, Any]
    error_code: str | None = None
    retryable: bool = False
    side_effect: Literal["NONE", "LAB_PATH"] = "NONE"


class CapabilityExecutor(Protocol):
    version: str

    def execute(self, action: ActionRequest) -> ExecutorOutput: ...


class DatabaseReadExecutor:
    version = "database-read/1.0.0"

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def execute(self, action: ActionRequest) -> ExecutorOutput:
        parameters = ReadInput.model_validate(action.parameters)
        output: dict[str, Any]
        with Session(self.engine) as db:
            if action.capability_id == "collect_resource_context":
                resource = db.get(ResourceRow, (action.target.resource_id, action.environment_id))
                if resource is None:
                    return ExecutorOutput("EXECUTION_FAILURE", {}, "target_missing")
                output = {"resource": contract_from(resource, ResourceRef).model_dump(mode="json")}
            elif action.capability_id == "query_event_history":
                events = db.scalars(
                    select(EventRow)
                    .join(EventResourceRow, EventResourceRow.event_id == EventRow.event_id)
                    .where(
                        EventRow.environment_id == action.environment_id,
                        EventResourceRow.environment_id == action.environment_id,
                        EventResourceRow.resource_id == action.target.resource_id,
                        EventResourceRow.role == "TARGET",
                    )
                    .order_by(EventRow.source_timestamp.desc(), EventRow.event_id)
                    .limit(parameters.limit)
                )
                output = {
                    "events": [
                        {
                            "event_id": e.event_id,
                            "source_type": e.source_type,
                            "source_timestamp": e.source_timestamp.isoformat(),
                            "activity_category": e.activity_category,
                            "activity_name": e.activity_name,
                            "outcome": e.outcome,
                        }
                        for e in events
                    ]
                }
            elif action.capability_id == "query_incident_evidence":
                evidence = db.scalars(
                    select(EvidenceRow)
                    .where(
                        EvidenceRow.environment_id == action.environment_id,
                        EvidenceRow.incident_id == action.incident_id,
                        EvidenceRow.evidence_id.in_(action.evidence_ids),
                    )
                    .order_by(EvidenceRow.evidence_id)
                    .limit(parameters.limit)
                )
                output = {
                    "evidence": [
                        {
                            "evidence_id": e.evidence_id,
                            "content_ref": e.content_ref,
                            "integrity_hash": e.integrity_hash,
                        }
                        for e in evidence
                    ]
                }
            else:
                return ExecutorOutput("EXECUTION_FAILURE", {}, "executor_capability_mismatch")
        return ExecutorOutput("EXECUTION_SUCCESS", output)


class SafeHttpProbeExecutor:
    version = "safe-probe/1.0.0"

    def execute(self, action: ActionRequest) -> ExecutorOutput:
        parameters = ProbeInput.model_validate(action.parameters)
        start = monotonic()
        deadline = start + parameters.timeout_ms / 1000
        if action.source is None or action.target.resource_type != "NETWORK_ENDPOINT":
            return ExecutorOutput("EXECUTION_FAILURE", {}, "missing_bound_network_identity")
        try:
            target_ip = ipaddress.ip_address(action.target.locator["address"])
            source_ip = ipaddress.ip_address(action.source.locator["address"])
            port = int(action.target.locator["port"])
            if (
                target_ip.version != source_ip.version
                or target_ip.is_multicast
                or target_ip.is_unspecified
                or target_ip.is_link_local
                or (isinstance(target_ip, ipaddress.IPv6Address) and target_ip.ipv4_mapped is not None)
            ):
                return ExecutorOutput("EXECUTION_FAILURE", {}, "unsupported_network_address")
            if action.target.locator["protocol"] != "TCP" or not 1 <= port <= 65535:
                return ExecutorOutput("EXECUTION_FAILURE", {}, "unsupported_transport")
        except (ValueError, KeyError, TypeError):
            return ExecutorOutput("EXECUTION_FAILURE", {}, "invalid_bound_endpoint")
        path = "/attack" if action.capability_id == "lab_containment_probe" else "/health"
        endpoint = f"{parameters.protocol}://{target_ip}:{port}{path}"
        connection = None
        try:
            connection = socket.create_connection(
                (str(target_ip), port),
                timeout=max(0.001, deadline - monotonic()),
                source_address=(str(source_ip), 0),
            )
            if action.capability_id == "check_service_reachability":
                return ExecutorOutput(
                    "EXECUTION_SUCCESS",
                    {
                        "reachable": True,
                        "endpoint": f"tcp://{target_ip}:{port}",
                        "latency_ms": (monotonic() - start) * 1000,
                    },
                )
            if action.capability_id not in {"safe_http_probe", "lab_containment_probe"}:
                return ExecutorOutput("EXECUTION_FAILURE", {}, "executor_capability_mismatch")
            if parameters.protocol == "https":
                connection.settimeout(max(0.001, deadline - monotonic()))
                connection = ssl.create_default_context().wrap_socket(
                    connection, server_hostname=str(target_ip)
                )
            host = f"[{target_ip}]" if target_ip.version == 6 else str(target_ip)
            request = f"HEAD {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\nUser-Agent: Zhiyu-Safe-Probe/1.0\r\n\r\n".encode(
                "ascii"
            )
            connection.settimeout(max(0.001, deadline - monotonic()))
            connection.sendall(request)
            header = bytearray()
            while b"\r\n\r\n" not in header:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                if len(header) >= 16384:
                    return ExecutorOutput("EXECUTION_FAILURE", {}, "response_header_too_large")
                connection.settimeout(remaining)
                chunk = connection.recv(min(1024, 16384 - len(header)))
                if not chunk:
                    return ExecutorOutput("EXECUTION_FAILURE", {}, "incomplete_http_headers", True)
                header.extend(chunk)
            first_line = bytes(header).split(b"\r\n", 1)[0].split(b" ", 2)
            if (
                len(first_line) < 2
                or first_line[0] not in {b"HTTP/1.0", b"HTTP/1.1"}
                or len(first_line[1]) != 3
                or not first_line[1].isdigit()
            ):
                return ExecutorOutput("EXECUTION_FAILURE", {}, "invalid_http_status")
            status = int(first_line[1])
            if not 100 <= status <= 599:
                return ExecutorOutput("EXECUTION_FAILURE", {}, "invalid_http_status")
            return ExecutorOutput(
                "EXECUTION_SUCCESS",
                {
                    "reachable": True,
                    "status_code": status,
                    "endpoint": endpoint,
                    "latency_ms": (monotonic() - start) * 1000,
                    "redirect_followed": False,
                    "meaning": "HTTP response received; no security verdict",
                },
            )
        except (TimeoutError, socket.timeout):
            return ExecutorOutput("TIMEOUT", {"endpoint": endpoint}, "executor_timeout", True)
        except (OSError, ssl.SSLError):
            return ExecutorOutput("EXECUTION_FAILURE", {"endpoint": endpoint}, "network_or_tls_failure", True)
        finally:
            if connection is not None:
                connection.close()


class ExecutorRegistry:
    def __init__(self, engine: Engine) -> None:
        from zhiyu.response.lab_client import LabExecutor
        from zhiyu.response.lab_protocol import CAPABILITY

        read = DatabaseReadExecutor(engine)
        probe = SafeHttpProbeExecutor()
        self.executors: dict[str, CapabilityExecutor] = {
            CAPABILITY: LabExecutor(),
            "collect_resource_context": read,
            "query_event_history": read,
            "query_incident_evidence": read,
            "safe_http_probe": probe,
            "check_service_reachability": probe,
        }

    def resolve(self, action: ActionRequest) -> CapabilityExecutor:
        if action.capability_version != "1.0.0" or action.capability_id not in self.executors:
            raise ValueError("executor capability/version not registered")
        return self.executors[action.capability_id]
