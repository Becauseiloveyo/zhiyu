from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

WorkloadClass = Literal["BACKGROUND", "SECURITY_CRITICAL", "RECOVERY"]


class ResponsePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    rule_version: str = "response-policy/1.0.0"
    authorization_ttl_seconds: int = Field(default=30, ge=5, le=120)
    action_ttl_seconds: int = Field(default=300, ge=30, le=600)
    health_ttl_seconds: int = Field(default=120, ge=5, le=300)
    lease_seconds: int = Field(default=20, ge=5, le=60)
    retry_backoff_seconds: int = Field(default=1, ge=1, le=30)
    max_actions_per_plan: int = Field(default=64, ge=1, le=100)
    budget_seconds: int = Field(default=600, ge=30, le=3600)
    worker_pool: str = "response"
    worker_sources: dict[str, str] = Field(default_factory=dict)
    asset_criticality: dict[str, Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]] = Field(default_factory=dict)
    allow_lab_r2: bool = True
    reserved_capacity_enabled: bool = False
    worker_classes: dict[str, WorkloadClass] = Field(default_factory=dict)
    class_capacity: dict[str, int] = Field(
        default_factory=lambda: {"BACKGROUND": 2, "SECURITY_CRITICAL": 1, "RECOVERY": 1}
    )

    @model_validator(mode="after")
    def bounded_capacity(self) -> Self:
        if set(self.class_capacity) != {"BACKGROUND", "SECURITY_CRITICAL", "RECOVERY"} or any(
            type(v) is not int or not 1 <= v <= 16 for v in self.class_capacity.values()
        ):
            raise ValueError("all three workload classes require bounded positive capacity")
        if self.reserved_capacity_enabled and set(self.worker_classes.values()) != set(self.class_capacity):
            raise ValueError("reserved capacity requires separately bound workers for all three classes")
        return self
