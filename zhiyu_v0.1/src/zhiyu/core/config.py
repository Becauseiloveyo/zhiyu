import re

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from zhiyu.ai.policy import AIPolicy
from zhiyu.ai.provider import ProviderConfig
from zhiyu.core.identity import ServicePrincipal
from zhiyu.response.lab_protocol import LabBinding


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZHIYU_", env_file=".env", extra="ignore")
    env: str = "dev"
    database_url: str = Field(
        default="postgresql+psycopg://zhiyu:zhiyu_dev_only@localhost:5432/zhiyu", repr=False
    )
    log_level: str = "INFO"
    architecture_baseline: str = "2026.09.12-ai.5"
    service_tokens: dict[str, ServicePrincipal] = Field(default_factory=dict, repr=False)
    db_connect_timeout: int = Field(default=2, ge=1, le=30)
    db_statement_timeout_ms: int = Field(default=5000, ge=100, le=30000)
    db_lock_timeout_ms: int = Field(default=3000, ge=100, le=30000)
    max_body_bytes: int = Field(default=4 * 1024 * 1024, ge=1024, le=16 * 1024 * 1024)
    ai_policies: dict[str, AIPolicy] = Field(default_factory=dict)
    ai_providers: dict[str, ProviderConfig] = Field(default_factory=dict, repr=False)
    lab_targets: dict[str, LabBinding] = Field(default_factory=dict, repr=False)

    @field_validator("service_tokens")
    @classmethod
    def validate_tokens(cls, value: dict[str, ServicePrincipal]) -> dict[str, ServicePrincipal]:
        if any(not re.fullmatch(r"[0-9a-f]{64}", key) for key in value):
            raise ValueError("service_tokens keys must be SHA256 digests, not plaintext tokens")
        return value


settings = Settings()
