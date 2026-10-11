"""Runtime limits supplement, without replacing, frozen check contracts."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from zhiyu.domain.contracts import AssertionSpec, VerificationSpec


class VerificationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: str = "verification/1.0.0"
    validity_seconds: int = Field(default=120, ge=10, le=300)
    evidence_ttl_seconds: int = Field(default=120, ge=5, le=300)
    sensor_ttl_seconds: int = Field(default=120, ge=5, le=300)
    lease_seconds: int = Field(default=10, ge=5, le=30)
    max_attempts: int = Field(default=3, ge=1, le=3)
    minimum_samples: int = Field(default=1, ge=1, le=5)
    minimum_window_seconds: int = Field(default=0, ge=0, le=30)
    minimum_evidence: int = Field(default=3, ge=3, le=20)
    start_after_seconds: int = Field(default=0, ge=0, le=65)


FIELDS = {
    "lab_containment_probe": {"status_code", "reachable", "latency_ms"},
    "state_snapshot_check": {"binding_version", "resource_id"},
    "safe_http_probe": {"status_code", "reachable", "latency_ms"},
    "sensor_health_check": {"sensors_healthy", "evidence_fresh", "telemetry_complete"},
}


def validate_spec(spec: VerificationSpec) -> None:
    if spec.objective_type not in {"DETECTION", "CONTAINMENT"} or len(spec.checks) > 12:
        raise ValueError("only bounded read-only DETECTION verification is implemented")
    if len({c.check_id for c in spec.checks}) != len(spec.checks):
        raise ValueError("duplicate check identity")
    dimensions = {
        "state_snapshot_check": "SECURITY",
        "safe_http_probe": "BUSINESS",
        "sensor_health_check": "OBSERVATION",
    }
    if spec.objective_type == "CONTAINMENT":
        dimensions = {
            "lab_containment_probe": "SECURITY",
            "safe_http_probe": "BUSINESS",
            "sensor_health_check": "OBSERVATION",
        }
        required: dict[str, set[tuple[str, Any]]] = {
            "lab_containment_probe": {("status_code", 403), ("reachable", True)},
            "safe_http_probe": {("status_code", 200), ("reachable", True)},
            "sensor_health_check": {
                (f, True) for f in ("sensors_healthy", "evidence_fresh", "telemetry_complete")
            },
        }
        if len(spec.checks) != 3 or {c.capability_id for c in spec.checks} != set(required):
            raise ValueError("containment requires three independent dimensions")
        for check in spec.checks:
            for field, expected in required[check.capability_id]:
                if not any(
                    a.field == field
                    and a.operator == "EQUALS"
                    and type(a.expected) is type(expected)
                    and a.expected == expected
                    for a in check.assertions
                ):
                    raise ValueError("containment assertion cannot weaken the acceptance condition")
    for check in spec.checks:
        if (
            dimensions.get(check.capability_id) != check.dimension
            or check.timeout_seconds > 3
            or check.repetitions > 5
            or not check.executor_must_differ_from_action_executor
            or check.on_missing_observation != "INCONCLUSIVE"
        ):
            raise ValueError("unsupported or unsafe check configuration")
        for assertion in check.assertions:
            if assertion.field not in FIELDS[check.capability_id]:
                raise ValueError("unknown observed field")
            if assertion.operator not in {"EQUALS", "NOT_EQUALS", "LTE", "GTE", "EXISTS"}:
                raise ValueError("unsupported bounded assertion operator")
            if assertion.operator in {"LTE", "GTE"} and (type(assertion.expected) not in {int, float}):
                raise ValueError("numeric assertion requires numeric expectation")
            if assertion.operator in {"EQUALS", "NOT_EQUALS"} and not isinstance(
                assertion.expected, (str, int, float, bool)
            ):
                raise ValueError("equality requires a scalar expectation")


def assert_value(values: dict[str, Any], assertion: AssertionSpec) -> dict[str, Any]:
    observed = values.get(assertion.field)
    outcome = "INCONCLUSIVE"
    if assertion.field in values:
        op, expected = assertion.operator, assertion.expected
        if op == "EXISTS":
            outcome = "PASS" if observed is not None else "FAIL"
        elif op in {"EQUALS", "NOT_EQUALS"}:
            equal = type(observed) is type(expected) and observed == expected
            outcome = "PASS" if (equal if op == "EQUALS" else not equal) else "FAIL"
        elif type(observed) in {int, float} and type(expected) in {int, float}:
            assert isinstance(observed, (int, float)) and isinstance(expected, (int, float))
            outcome = "PASS" if (observed <= expected if op == "LTE" else observed >= expected) else "FAIL"
    return {**assertion.model_dump(mode="json"), "observed": observed, "outcome": outcome}
