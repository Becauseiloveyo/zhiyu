"""Explicit structured capability catalog. Definitions grant no execution authority."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from zhiyu.domain.contracts import CapabilityManifest, Risk
from zhiyu.response.lab_protocol import CAPABILITY, LabInput


class ReadInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    limit: int = Field(default=50, ge=1, le=100)


class ProbeInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    protocol: Literal["http", "https"] = "http"
    timeout_ms: int = Field(default=1000, ge=100, le=3000)


CAPABILITY_VERSION = "1.0.0"
INPUTS: dict[str, type[BaseModel]] = {
    "collect_resource_context": ReadInput,
    "query_event_history": ReadInput,
    "query_incident_evidence": ReadInput,
    "check_service_reachability": ProbeInput,
    "safe_http_probe": ProbeInput,
}
PASSIVE_CAPABILITIES = tuple(list(INPUTS)[:3])


def manifest(capability_id: str) -> CapabilityManifest:
    if capability_id == CAPABILITY:
        return lab_manifest()
    model = INPUTS[capability_id]
    active = model is ProbeInput
    return CapabilityManifest(
        capability_id=capability_id,
        version=CAPABILITY_VERSION,
        adapter=capability_id,
        base_risk=Risk.R2 if active else Risk.R0 if capability_id == "collect_resource_context" else Risk.R1,
        operation_kind="ACTIVE_CHECK" if active else "PASSIVE_READ",
        controller_location="zhiyu-control",
        execution_location="bound-worker",
        target_domain="registered-resource",
        network_path="scope-bound" if active else "database-only",
        cleanup_owner="none-read-only",
        supported_os=["Linux", "Windows"],
        input_schema=model.model_json_schema(),
        output_schema={
            "type": "object",
            "required": ["execution_outcome", "side_effect"],
            "properties": {"execution_outcome": {"type": "string"}, "side_effect": {"const": "NONE"}},
        },
        scope_required=True,
        timeout_seconds=5,
        idempotency="ADAPTER_RECONCILE",
        reconciliation_method="return durable receipt; interrupted read-only calls may repeat",
        ttl_enforcement="NONE",
        rollback_policy="none-read-only",
        required_permissions=["response:execute", "capability:" + capability_id],
        required_secret_refs=[],
        supports_cancel=False,
        supports_dry_run=False,
        resource_locks=[],
        max_concurrency=1,
        expected_evidence_types=["execution-receipt"],
        integration_status="ADAPTED",
    )


def validate_input(capability_id: str, parameters: dict) -> dict:
    if capability_id == CAPABILITY:
        return LabInput.model_validate(parameters).model_dump()
    if capability_id not in INPUTS:
        raise ValueError("unknown structured capability")
    return INPUTS[capability_id].model_validate(parameters).model_dump()


def lab_manifest() -> CapabilityManifest:
    return CapabilityManifest(
        capability_id=CAPABILITY,
        version=CAPABILITY_VERSION,
        adapter=CAPABILITY,
        base_risk=Risk.R2,
        operation_kind="STATE_CHANGE",
        controller_location="zhiyu-control",
        execution_location="bound-worker",
        target_domain="explicit-disposable-lab-http-path",
        network_path="scope-bound",
        cleanup_owner="target-native-expiry",
        supported_os=["Linux", "Windows"],
        input_schema=LabInput.model_json_schema(),
        output_schema={"type": "object", "required": ["before", "intended", "after"]},
        scope_required=True,
        timeout_seconds=5,
        idempotency="NATIVE",
        reconciliation_method="read target receipt and current epoch/owner/generation/digest; never replay",
        ttl_enforcement="DEVICE",
        rollback_policy="lab-owner-generation-digest-cas",
        required_permissions=["response:execute", "capability:" + CAPABILITY],
        required_secret_refs=["protected-settings:lab-target-token"],
        supports_cancel=False,
        supports_dry_run=False,
        resource_locks=["target-http-test-path"],
        max_concurrency=1,
        expected_evidence_types=["lab-target-state", "independent-http-path-observation"],
        verification_capability_id="lab_containment_probe",
        compensator_capability_id=CAPABILITY,
        integration_status="ADAPTED",
    )
