"""Fixed-path, source-bound Lab transport; configuration is never a task parameter."""

import http.client
import ipaddress
import json
import socket
import threading
from typing import TYPE_CHECKING, Any, Literal

from zhiyu.core.config import settings
from zhiyu.domain.contracts import ActionRequest, action_digest
from zhiyu.response.lab_protocol import CAPABILITY, LabBinding, LabCommand, LabInput

if TYPE_CHECKING:
    from zhiyu.response.executors import ExecutorOutput


def binding_for(action: ActionRequest) -> LabBinding:
    binding = settings.lab_targets.get(action.environment_id + "/" + action.target.resource_id)
    if (
        not binding
        or binding.environment_id != action.environment_id
        or binding.resource_id != action.target.resource_id
        or action.target.resource_type != "NETWORK_ENDPOINT"
        or action.target.locator.get("address") != binding.address
        or action.target.locator.get("port") != binding.port
        or action.target.locator.get("protocol") != "TCP"
        or not action.source
        or action.source.environment_id != action.environment_id
        or len(binding.token.get_secret_value()) < 32
    ):
        raise ValueError("unconfigured_lab_target")
    for address in (binding.address, action.source.locator.get("address", "")):
        ip = ipaddress.ip_address(address)
        if not (ip.is_private or ip.is_loopback) or ip.is_unspecified or ip.is_multicast or ip.is_link_local:
            raise ValueError("non_lab_endpoint")
    return binding


class LabClient:
    def __init__(self, action: ActionRequest) -> None:
        self.action, self.binding = action, binding_for(action)

    def command(self) -> LabCommand:
        return LabCommand(
            environment_id=self.action.environment_id,
            resource_id=self.action.target.resource_id,
            action_id=self.action.action_id,
            action_digest=action_digest(self.action),
            owner=self.action.ownership_tag,
            expires_at=self.action.expires_at,
            parameters=LabInput.model_validate(self.action.parameters),
        )

    def request(self, method: Literal["GET", "POST"]) -> dict[str, Any]:
        assert self.action.source is not None
        connection = http.client.HTTPConnection(
            self.binding.address,
            self.binding.port,
            timeout=2,
            source_address=(self.action.source.locator["address"], 0),
        )
        deadline: threading.Timer | None = None
        expired = threading.Event()
        try:
            # Connect has its own two-second bound. The connected exchange also
            # has an absolute deadline, including a peer trickling response bytes.
            connection.connect()
            channel = connection.sock
            assert channel is not None

            def interrupt() -> None:
                expired.set()
                try:
                    channel.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

            deadline = threading.Timer(2, interrupt)
            deadline.daemon = True
            deadline.start()
            body = self.command().model_dump_json() if method == "POST" else None
            connection.request(
                method,
                "/control",
                body,
                {
                    "X-Zhiyu-Lab-Control": self.binding.token.get_secret_value(),
                    "X-Action-Id": self.action.action_id,
                    "Content-Type": "application/json",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            data = response.read(32769)
            if expired.is_set():
                raise TimeoutError("lab_exchange_deadline")
            if len(data) > 32768 or response.status != 200:
                raise ValueError("lab_response_unconfirmed")
            result = json.loads(data)
            if not isinstance(result, dict):
                raise ValueError("invalid_lab_response")
            return result
        except http.client.HTTPException as error:
            raise ValueError("invalid_lab_transport") from error
        finally:
            if deadline is not None:
                deadline.cancel()
            connection.close()


class LabExecutor:
    version = "lab-http-path/1.0.0"

    def execute(self, action: ActionRequest) -> "ExecutorOutput":
        from zhiyu.response.executors import ExecutorOutput

        if action.capability_id != CAPABILITY:
            raise ValueError("lab_capability_mismatch")
        from zhiyu.response.lab_reconcile import compare

        result = LabClient(action).request("POST")
        disposition, _ = compare(action, {"state": result["after"], "receipt": result})
        if disposition != "CONFIRMED_APPLIED":
            raise ValueError("lab_receipt_not_bound_to_intent")
        return ExecutorOutput("EXECUTION_SUCCESS", result, side_effect="LAB_PATH")
