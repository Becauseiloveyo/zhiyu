import json
from typing import Any, Protocol

from pydantic import ValidationError

from zhiyu.adapters.base import AdapterContext, AdapterError
from zhiyu.adapters.suricata import SuricataAdapter
from zhiyu.adapters.wazuh import WazuhAdapter
from zhiyu.domain.contracts import NormalizedEvent


class VendorAdapter(Protocol):
    def normalize(self, raw: dict[str, Any], ctx: AdapterContext) -> NormalizedEvent: ...


def reject_constant(value: str) -> None:
    raise ValueError("non-JSON numeric constant")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class AdapterRegistry:
    def __init__(self) -> None:
        self.adapters: dict[str, VendorAdapter] = {"suricata": SuricataAdapter(), "wazuh": WazuhAdapter()}

    def normalize(self, text: str, ctx: AdapterContext) -> NormalizedEvent:
        adapter = self.adapters.get(ctx.source_type)
        if adapter is None:
            raise AdapterError("unsupported_event_type", "source_type")
        try:
            text.encode("utf-8")
            raw = json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_object)
        except (ValueError, RecursionError) as exc:
            raise AdapterError("malformed_json", "record") from exc
        if not isinstance(raw, dict):
            raise AdapterError("malformed_json", "record.object_required")
        try:
            return adapter.normalize(raw, ctx)
        except AdapterError:
            raise
        except ValidationError as exc:
            raise AdapterError("contract_validation_error", "NormalizedEvent") from exc
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError) as exc:
            raise AdapterError("mapping_error", "vendor_structure") from exc
