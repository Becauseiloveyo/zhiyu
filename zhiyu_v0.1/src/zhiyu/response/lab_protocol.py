"""Opt-in protocol for one disposable Lab HTTP path, never host/network administration."""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

CAPABILITY = "lab_http_containment"


class LabInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Literal["contain", "compensate"] = "contain"
    epoch: str = Field(pattern=r"^[0-9a-f]{32}$")
    expected_generation: int = Field(ge=0)
    before_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    ttl_seconds: int = Field(ge=5, le=60)
    prior_action_id: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def owner_binding(self) -> Self:
        if (self.operation == "compensate") != (self.prior_action_id is not None):
            raise ValueError("compensation requires the original owning action")
        return self


class LabBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    environment_id: str
    resource_id: str
    address: str
    port: int = Field(ge=1, le=65535)
    token: SecretStr = Field(repr=False)


class LabCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment_id: str
    resource_id: str
    action_id: str = Field(min_length=1, max_length=128)
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner: str = Field(min_length=1, max_length=160)
    expires_at: datetime
    parameters: LabInput
