"""Internal model-output proposals, never authorization or observed-state contracts."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Structured(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Finding(Structured):
    claim: str = Field(min_length=1, max_length=512)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    resource_ids: list[str] = Field(min_length=1, max_length=8)
    observed_at: AwareDatetime


class ModelHypothesis(Structured):
    claim: str = Field(min_length=1, max_length=512)
    evidence_refs: list[str] = Field(max_length=8)
    missing_evidence: list[str] = Field(max_length=8)
    model_confidence: float = Field(ge=0, le=1, allow_inf_nan=False)


class SituationOutput(Structured):
    incident_summary: str = Field(min_length=1, max_length=512)
    supported_findings: list[Finding] = Field(max_length=8)
    hypotheses: list[ModelHypothesis] = Field(max_length=8)
    evidence_gaps: list[str] = Field(max_length=8)
    affected_resources: list[str] = Field(max_length=8)
    recommended_next_steps: list[str] = Field(max_length=8)
    risk_observations: list[str] = Field(max_length=8)
    uncertainty: str = Field(min_length=1, max_length=512)
    confidence_semantics: Literal["MODEL_SELF_REPORTED_UNCALIBRATED"]


class ProposalParameters(Structured):
    # Fixed typed fields, not an arbitrary dict able to smuggle commands/URLs/credentials.
    limit: int | None = Field(default=None, ge=1, le=100)
    protocol: Literal["http", "https"] | None = None
    timeout_ms: int | None = Field(default=None, ge=100, le=3000)


class TaskProposal(Structured):
    task_key: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    dependencies: list[str] = Field(max_length=8)
    capability_id: str = Field(min_length=1, max_length=128)
    target_resource_id: str = Field(min_length=1, max_length=128)
    parameters: ProposalParameters
    reason: str = Field(min_length=1, max_length=256)
    expected_outcome: str = Field(min_length=1, max_length=256)
    verification_required: Literal["INDEPENDENT_THREE_DIMENSION"]


class PlanProposalOutput(Structured):
    objective: str = Field(min_length=1, max_length=256)
    reasoning_summary: str = Field(min_length=1, max_length=512)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    proposed_tasks: list[TaskProposal] = Field(min_length=1, max_length=8)
    risk_notes: list[str] = Field(max_length=8)
    success_is_unverified: Literal[True]


OUTPUTS: dict[str, type[Structured]] = {"ANALYSIS": SituationOutput, "PLAN": PlanProposalOutput}
