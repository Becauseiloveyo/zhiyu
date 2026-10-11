# ruff: noqa: F811
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_response_authorization import authority_environment  # noqa: F401
from test_response_planner import ENV, response_environment  # noqa: F401
from test_verification_runtime import AT, collect, verification_environment, verifier  # noqa: F401

from zhiyu.db.models import EvidenceRow, ScopeRow, SensorHealthRow
from zhiyu.db.verification_decisions import EffectivenessRow
from zhiyu.db.verification_runtime import VerificationObservationRow
from zhiyu.verification.engine import VerificationEngine
from zhiyu.verification.policy import VerificationPolicy
from zhiyu.verification.runtime import VerificationCheckExecutor

pytestmark = pytest.mark.postgres


@pytest.mark.parametrize(
    "case,expected",
    [
        ("pass", "PASS"),
        ("security", "FAIL"),
        ("business", "FAIL"),
        ("offline", "INCONCLUSIVE"),
        ("stale", "INCONCLUSIVE"),
        ("missing", "INCONCLUSIVE"),
        ("conflicting", "INCONCLUSIVE"),
        ("failed_and_offline", "INCONCLUSIVE"),
    ],
)
def test_qualified_three_dimensional_verdict(verification_environment, monkeypatch, case, expected):
    engine, service, result_id, spec, state = verification_environment
    if case in {"security", "failed_and_offline"}:
        spec.checks[0].assertions[0].expected = 99
    if case == "business":
        state["status"] = 500
    if case in {"offline", "failed_and_offline"}:
        with Session(engine) as db, db.begin():
            db.scalar(select(SensorHealthRow)).status = "OFFLINE"
    if case == "conflicting":
        spec.checks[0].repetitions = 2
        original = VerificationCheckExecutor.execute
        count = 0

        def alternate(self, runtime, check, *args):
            nonlocal count
            status, values, reason = original(self, runtime, check, *args)
            if check.dimension == "SECURITY":
                count += 1
                values["binding_version"] = count
            return status, values, reason

        monkeypatch.setattr(VerificationCheckExecutor, "execute", alternate)
    if case == "missing":
        service.create(ENV, result_id, spec, verifier(), now=AT)
    else:
        collect(verification_environment)
    now = AT + timedelta(seconds=121) if case == "stale" else AT
    result = VerificationEngine(engine).decide(ENV, spec.verification_spec_id, verifier(), now=now)
    assert result.status == expected
    assert result.action_id and result.evidence_ids and result.residual_risks
    assert VerificationEngine(engine).decide(ENV, spec.verification_spec_id, verifier(), now=now) == result
    with Session(engine) as db:
        effect = db.get(EffectivenessRow, result.verification_id)
        assert effect.decision["objective_type"] == "DETECTION"
        if case == "business":
            assert (
                result.security_status == "PASS"
                and result.business_status == "FAIL"
                and result.observation_status == "PASS"
            )
            check = db.get(VerificationObservationRow, (spec.verification_spec_id, "business-health"))
            assert check.execution_status == "SUCCEEDED" and check.assertion_status == "FAIL"
        if case == "failed_and_offline":
            assert effect.raw_dimensions["SECURITY"] == "FAIL" and result.security_status == "INCONCLUSIVE"
        if expected == "INCONCLUSIVE":
            assert effect.qualification_failures and not effect.decision["observability_sufficient"]


@pytest.mark.parametrize(
    "policy", [VerificationPolicy(minimum_samples=2), VerificationPolicy(minimum_window_seconds=20)]
)
def test_insufficient_sampling_or_window(verification_environment, policy):
    engine, service, result_id, spec, _ = verification_environment
    service.create(ENV, result_id, spec, verifier(), policy, now=AT)
    while lease := service.claim(ENV, verifier(), now=AT):
        service.run_claim(ENV, lease, verifier(), now=AT)
    assert (
        VerificationEngine(engine).decide(ENV, spec.verification_spec_id, verifier(), now=AT).status
        == "INCONCLUSIVE"
    )


def test_verdict_expiry_cannot_outlive_supporting_evidence(verification_environment):
    engine, _, _, spec, _ = verification_environment
    collect(verification_environment)
    result = VerificationEngine(engine).decide(
        ENV, spec.verification_spec_id, verifier(), now=AT + timedelta(seconds=5)
    )
    assert result.status == "PASS"
    with Session(engine) as db:
        assert all(result.valid_until <= db.get(EvidenceRow, eid).valid_until for eid in result.evidence_ids)


def test_scope_revoked_after_checks_blocks_pass(verification_environment):
    engine, _, _, spec, _ = verification_environment
    collect(verification_environment)
    with Session(engine) as db, db.begin():
        db.scalar(
            select(ScopeRow).where(ScopeRow.environment_id == ENV)
        ).version = "revoked-after-observation"
    result = VerificationEngine(engine).decide(ENV, spec.verification_spec_id, verifier(), now=AT)
    assert result.status == "INCONCLUSIVE"
