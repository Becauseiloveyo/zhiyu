"""Versioned deterministic policy configuration; no learned parameters."""

from pydantic import BaseModel, ConfigDict, Field


class IntelligenceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: str = "ei-config/1.0.0"
    key_version: str = "correlation-key/1.0.0"
    rule_version: str = "correlation-rules/1.0.0"
    algorithm_version: str = "fixed-window/1.0.0"
    auth_failure_window: int = Field(default=300, ge=1, le=3600)
    network_alert_window: int = Field(default=60, ge=1, le=3600)
    web_activity_window: int = Field(default=120, ge=1, le=3600)
    generic_window: int = Field(default=60, ge=1, le=3600)
    allowed_lateness_seconds: int = Field(default=120, ge=0, le=3600)
    expired_after_seconds: int = Field(default=86400, ge=3600)
    maximum_future_seconds: int = Field(default=300, ge=0)
    candidate_limit: int = Field(default=100, ge=1, le=1000)
    batch_limit: int = Field(default=1000, ge=1, le=1000)

    def window(self, category: str) -> int:
        return {
            "authentication": self.auth_failure_window,
            "network_alert": self.network_alert_window,
            "web": self.web_activity_window,
        }.get(category, self.generic_window)


DEFAULT_INTELLIGENCE_CONFIG = IntelligenceConfig()
