"""Explicit server configuration; AI influence cannot raise frozen execution autonomy."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AIBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    max_calls: int = Field(default=6, ge=0, le=20)
    max_tokens: int = Field(default=96000, ge=0, le=500000)
    max_ai_replans: int = Field(default=1, ge=0, le=3)
    max_wall_seconds: int = Field(default=900, ge=10, le=3600)
    max_cost_usd: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)


class AIPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: str = "ai-policy/1.0.0"
    routing_version: str = "explicit-routing/1.0.0"
    enabled: bool = False
    mode: Literal["SHADOW", "ASSISTED"] = "SHADOW"
    provider_id: str | None = None
    cloud_classifications: tuple[Literal["PUBLIC", "INTERNAL", "SENSITIVE", "RESTRICTED"], ...] = (
        "PUBLIC",
        "INTERNAL",
    )
    budget: AIBudget = Field(default_factory=AIBudget)
