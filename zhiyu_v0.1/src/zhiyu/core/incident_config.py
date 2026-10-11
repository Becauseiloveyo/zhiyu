from pydantic import BaseModel, ConfigDict, Field


class IncidentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    promotion_version: str = "incident-promotion/1.0.0"
    risk_version: str = "incident-risk/1.0.0"
    merge_version: str = "incident-merge/1.0.0"
    promotion_score: int = Field(default=55, ge=0, le=100)
    merge_horizon_seconds: int = Field(default=900, ge=1, le=86400)
    evidence_ttl_seconds: int = Field(default=86400, ge=60)
    default_asset_criticality: int = Field(default=1, ge=0, le=5)
    # Operator-owned environment/resource keys, never vendor supplied criticality.
    asset_criticality: dict[str, int] = Field(default_factory=dict)
    severity_weight: int = 4
    independence_weight: int = 10
    criticality_weight: int = 4
    repetition_weight: int = 2
    evidence_weight: int = 10
    validation_reduction: int = 60


DEFAULT_INCIDENT_CONFIG = IncidentConfig()
