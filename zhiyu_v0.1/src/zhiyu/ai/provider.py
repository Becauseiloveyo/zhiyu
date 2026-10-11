"""Bounded OpenAI-compatible transport. No SDK dependency or model-selected endpoint."""

import http.client
import ipaddress
import json
import os
import socket
import ssl
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zhiyu.ai.context_policy import serialized


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: str = Field(pattern=r"^[a-zA-Z0-9_.-]{1,64}$")
    location: Literal["LOCAL", "CLOUD"]
    endpoint: str = Field(max_length=256)
    model: str = Field(min_length=1, max_length=128)
    revision: str | None = Field(default=None, max_length=128)
    timeout_seconds: float = Field(default=60, ge=0.1, le=120, allow_inf_nan=False)
    max_output_tokens: int = Field(default=1200, ge=32, le=4096)
    temperature: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
    structured_format: Literal["JSON_SCHEMA", "JSON_OBJECT_SCHEMA"] = "JSON_SCHEMA"
    api_key_env: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{0,63}$", repr=False)

    @model_validator(mode="after")
    def endpoint_boundary(self) -> "ProviderConfig":
        parsed = urlsplit(self.endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path.rstrip("/") not in {"", "/v1"}
        ):
            raise ValueError("provider endpoint must be an operator-configured HTTP API origin")
        if self.location == "CLOUD" and parsed.scheme != "https":
            raise ValueError("cloud provider requires HTTPS")
        return self

    def public(self) -> dict[str, Any]:
        return self.model_dump(exclude={"api_key_env"})


class ProviderFailure(Exception):
    def __init__(self, code: str, response: "ProviderResponse | None" = None) -> None:
        self.code = code
        self.response = response
        super().__init__(code)


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    usage_known: bool
    latency_ms: float
    cost_usd: float | None = None


class ModelProviderAdapter(Protocol):
    def complete(self, config: ProviderConfig, request: dict[str, Any]) -> ProviderResponse: ...


def strict_json(value: str) -> Any:
    def pairs(entries: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in entries:
            if k in result:
                raise ValueError("duplicate JSON key")
            result[k] = v
        return result

    def reject_constant(value: str) -> None:
        raise ValueError("non-finite JSON")

    return json.loads(value, object_pairs_hook=pairs, parse_constant=reject_constant)


class PinnedTLSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: str, port: int, timeout: float) -> None:
        self.tls_context = ssl.create_default_context()
        super().__init__(hostname, port, timeout=timeout, context=self.tls_context)
        self.address = address

    def connect(self) -> None:
        sock = socket.create_connection((self.address, self.port), self.timeout)
        self.sock = self.tls_context.wrap_socket(sock, server_hostname=self.host)


class OpenAICompatibleProvider:
    def complete(self, config: ProviderConfig, request: dict[str, Any]) -> ProviderResponse:
        started = perf_counter()
        parsed = urlsplit(config.endpoint)
        host = parsed.hostname
        assert host is not None
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        connection: http.client.HTTPConnection | None = None
        try:
            addresses = sorted(
                {str(v[4][0]) for v in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
            )
            if not addresses:
                raise ProviderFailure("CONNECTION_FAILURE")
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if ip.is_link_local or ip.is_multicast or ip.is_unspecified:
                    raise ProviderFailure("ENDPOINT_DENIED")
                if config.location == "LOCAL" and not (ip.is_loopback or ip.is_private):
                    raise ProviderFailure("LOCAL_ENDPOINT_NOT_LOCAL")
                if config.location == "CLOUD" and not ip.is_global:
                    raise ProviderFailure("CLOUD_ENDPOINT_NOT_PUBLIC")
            # Resolve once and connect to the vetted address. No proxy/environment redirect behavior.
            connection = (
                PinnedTLSConnection(host, addresses[0], port, config.timeout_seconds)
                if parsed.scheme == "https"
                else http.client.HTTPConnection(addresses[0], port, timeout=config.timeout_seconds)
            )
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Host": parsed.netloc,
            }
            if config.api_key_env:
                key = os.environ.get(config.api_key_env)
                if not key:
                    raise ProviderFailure("CREDENTIAL_UNAVAILABLE")
                headers["Authorization"] = "Bearer " + key
            body = serialized(request).encode()
            if len(body) > 131072:
                raise ProviderFailure("REQUEST_TOO_LARGE")
            connection.request(
                "POST",
                parsed.path.rstrip("/") + "/chat/completions"
                if parsed.path.rstrip("/") == "/v1"
                else "/v1/chat/completions",
                body=body,
                headers=headers,
            )
            active_socket = connection.sock
            response = connection.getresponse()
            if response.status != 200:
                raise ProviderFailure("RATE_LIMIT" if response.status == 429 else "HTTP_FAILURE")
            chunks = []
            length = 0
            # A Content-Length response may close its HTTP/1.0 socket as soon as
            # read1 consumes the last byte. Never touch that socket again.
            while not response.isclosed():
                remaining = config.timeout_seconds - (perf_counter() - started)
                if remaining <= 0:
                    raise ProviderFailure("TIMEOUT")
                if active_socket:
                    active_socket.settimeout(remaining)
                chunk = response.read1(min(8192, 131073 - length))
                if not chunk:
                    break
                chunks.append(chunk)
                length += len(chunk)
                if length > 131072:
                    raise ProviderFailure("RESPONSE_TOO_LARGE")
            raw = b"".join(chunks)
            data = strict_json(raw.decode("utf-8", errors="strict"))
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("choices"), list)
                or len(data["choices"]) != 1
            ):
                raise ProviderFailure("EMPTY_OR_INVALID_RESPONSE")
            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content")
            usage = data.get("usage") or {}
            known = all(
                type(usage.get(k)) is int and 0 <= usage[k] <= 1000000
                for k in ("prompt_tokens", "completion_tokens")
            )
            cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
            if type(cached) is not int or cached < 0:
                cached = 0
            receipt = ProviderResponse(
                content if isinstance(content, str) else "",
                usage["prompt_tokens"] if known else 0,
                usage["completion_tokens"] if known else 0,
                cached if known else 0,
                known,
                (perf_counter() - started) * 1000,
            )
            if message.get("tool_calls") or message.get("function_call"):
                raise ProviderFailure("TOOL_CALL_REJECTED", receipt)
            if message.get("refusal"):
                raise ProviderFailure("MODEL_REFUSAL", receipt)
            if choice.get("finish_reason") != "stop":
                raise ProviderFailure("INCOMPLETE_RESPONSE", receipt)
            if not isinstance(content, str) or not content.strip():
                raise ProviderFailure("EMPTY_OR_INVALID_RESPONSE", receipt)
            return receipt
        except ProviderFailure as error:
            if error.response is None:
                error.response = ProviderResponse("", 0, 0, 0, False, (perf_counter() - started) * 1000)
            raise
        except (TimeoutError, socket.timeout) as error:
            raise ProviderFailure(
                "TIMEOUT", ProviderResponse("", 0, 0, 0, False, (perf_counter() - started) * 1000)
            ) from error
        except UnicodeDecodeError as error:
            raise ProviderFailure(
                "MALFORMED_UTF8", ProviderResponse("", 0, 0, 0, False, (perf_counter() - started) * 1000)
            ) from error
        except (ValueError, KeyError, IndexError, TypeError, AttributeError, RecursionError) as error:
            raise ProviderFailure(
                "INVALID_JSON_OR_ENVELOPE",
                ProviderResponse("", 0, 0, 0, False, (perf_counter() - started) * 1000),
            ) from error
        except (OSError, http.client.HTTPException) as error:
            raise ProviderFailure(
                "CONNECTION_FAILURE", ProviderResponse("", 0, 0, 0, False, (perf_counter() - started) * 1000)
            ) from error
        finally:
            if connection:
                connection.close()
