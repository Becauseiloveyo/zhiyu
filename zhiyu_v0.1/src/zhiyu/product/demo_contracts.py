"""Finite controller commands; none accept security execution parameters."""

import re
from datetime import datetime
from typing import Literal

from pydantic import Field

from zhiyu.product.contracts import DTO, Envelope
from zhiyu.product.snapshots import digest

Scenario = Literal["A", "B", "C", "D", "E"]
STEPS = ("PREFLIGHT", "TRIGGER", "VERIFY", "ARCHIVE")
TEMPLATES = {
    "A": {"title": "真实 Sensor 与受控处置闭环", "expected": "PASS", "model_source": "REAL_LOCAL_MODEL"},
    "B": {"title": "无效提案拒绝", "expected": "REJECTED", "model_source": "SCRIPTED_NOT_AI"},
    "C": {"title": "Sensor 离线与观测缺失", "expected": "INCONCLUSIVE", "model_source": "NONE"},
    "D": {"title": "独立验证失败与有限重规划", "expected": "FAIL", "model_source": "SCRIPTED_NOT_AI"},
    "E": {"title": "模型不可用与确定性降级", "expected": "FALLBACK", "model_source": "REAL_LOCAL_MODEL"},
}


def template_hash(scenario: str) -> str:
    return digest({"id": scenario, "version": "0.9.0", "steps": STEPS, **TEMPLATES[scenario]})


def source_environment(run_id: str) -> str:
    if not re.fullmatch(r"demo-[a-f0-9]{32}", run_id):
        raise ValueError("invalid_demo_run_identity")
    return "m6-real-" + run_id


class DemoProfile(DTO):
    environment_id: str
    scope_id: str
    scenarios: frozenset[Scenario]
    enabled: bool = False
    adapter: Literal["CONTROLLED_LAB_V1"] = "CONTROLLED_LAB_V1"


class StartDemo(DTO):
    scenario_id: Scenario
    profile_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{16,80}$")


class DemoCommand(DTO):
    expected_version: int = Field(ge=1)
    idempotency_key: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{16,80}$")


class StepOutput(DTO):
    object_refs: list[str] = Field(default_factory=list, max_length=40)
    artifact_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    outcome: Literal["UNKNOWN", "PASS", "FAIL", "INCONCLUSIVE", "REJECTED", "FALLBACK"] = "UNKNOWN"
    cleanup_verified: bool = False
    residual_count: int = Field(default=0, ge=0, le=10000)
    model_source: Literal["NONE", "REAL_LOCAL_MODEL", "SCRIPTED_NOT_AI"] | None = None


class WorkItem(DTO):
    run_id: str
    environment_id: str
    scope_id: str
    scenario_id: Scenario
    profile_id: str
    operation: str
    position: int
    generation: int
    lease_owner: str
    lease_until: datetime
    deadline: datetime


class DemoStepView(DTO):
    position: int
    operation: Literal["PREFLIGHT", "TRIGGER", "VERIFY", "ARCHIVE", "CLEANUP"]
    status: Literal["STARTED", "COMPLETED", "FAILED", "UNKNOWN"]
    generation: int
    started_at: datetime
    finished_at: datetime | None
    output: StepOutput


class DemoRunView(DTO):
    run_id: str
    environment_id: str
    source_environment_id: str
    scope_id: str
    scenario_id: Scenario
    template_sha256: str
    profile_id: str
    actor_id: str
    predecessor_id: str | None
    run_mode: Literal["LIVE"]
    model_source: Literal["NONE", "REAL_LOCAL_MODEL", "SCRIPTED_NOT_AI"]
    planned_model_source: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "NEEDS_RECONCILIATION"]
    cleanup_status: Literal["NOT_STARTED", "QUEUED", "RUNNING", "CLEAN", "NEEDS_MANUAL"]
    cancel_requested: bool
    version: int
    step_index: int
    created_at: datetime
    updated_at: datetime
    deadline: datetime
    error_code: str | None
    actual_outcome: Literal["UNKNOWN", "PASS", "FAIL", "INCONCLUSIVE", "REJECTED", "FALLBACK"]
    expected_outcome: str
    completion_semantics: Literal["SCENARIO_COMPLETION_NOT_SECURITY_PASS"]
    steps: list[DemoStepView] = Field(max_length=5)


class DemoRunPage(Envelope):
    items: list[DemoRunView] = Field(max_length=50)
    truncated: bool


class DemoRunResponse(Envelope):
    run: DemoRunView


class DemoMutationResponse(DTO):
    run: DemoRunView
