"""Gate A: PostgreSQL persistence and independent real HTTP/database observations."""

# ruff: noqa: F811
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_response_authorization import authority_environment  # noqa: F401
from test_response_gateway import claim, execute
from test_response_planner import ENV, INSTANT, response_environment, response_principal  # noqa: F401

from zhiyu.core.errors import ConflictError, LeaseLostError
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import ActionRow, ResourceRow, ScopeRow, SensorHealthRow
from zhiyu.db.response_execution import ActionResultRow
from zhiyu.db.verification_runtime import VerificationObservationRow
from zhiyu.domain.contracts import ActionRequest, AssertionSpec, VerificationSpec
from zhiyu.verification.policy import assert_value, validate_spec
from zhiyu.verification.runtime import VerificationService, default_spec

AT = INSTANT + timedelta(seconds=1)


def verifier():
    original = response_principal()
    return original.model_copy(
        update={
            "permissions": original.permissions
            | {"verification:write", "verification:execute", "verification:read", "verification:replan"}
        }
    )


@pytest.fixture
def verification_environment(authority_environment):
    engine, plan = authority_environment
    state = {"status": 200, "delay": 0, "calls": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            state["calls"] += 1
            time.sleep(state["delay"])
            self.send_response(state["status"])
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    target = plan.tasks[0].target_resource_ids[0]
    with Session(engine) as db, db.begin():
        db.get(ResourceRow, (target, ENV)).locator = {
            "address": "127.0.0.1",
            "port": server.server_port,
            "protocol": "TCP",
        }
        db.get(ResourceRow, ("validation-a", ENV)).locator = {
            "address": "127.0.0.1",
            "port": 1,
            "protocol": "TCP",
        }
        scope = db.get(ScopeRow, (plan.tasks[0].scope_id, ENV))
        scope.network_constraints = [
            {
                "source_resource_ids": ["validation-a"],
                "target_resource_ids": [target],
                "destination_ports": [server.server_port],
                "protocols": ["TCP"],
            }
        ]
    receipt, _ = execute(engine, claim(engine))
    assert receipt["execution_outcome"] == "EXECUTION_SUCCESS"
    with Session(engine) as db:
        action = contract_from(db.scalar(select(ActionRow)), ActionRequest)
        result = db.scalar(select(ActionResultRow))
        result_id = result.attempt_id
        sensors = list(db.scalars(select(SensorHealthRow.sensor_id)))
    spec = default_spec(action, sensors)
    service = VerificationService(engine)
    yield engine, service, result_id, spec, state
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def collect(environment, *, spec=None, now=AT):
    engine, service, result, original, _ = environment
    spec = spec or original
    service.create(ENV, result, spec, verifier(), now=now)
    results = []
    while lease := service.claim(ENV, verifier(), spec_id=spec.verification_spec_id, now=now):
        results.append(service.run_claim(ENV, lease, verifier(), now=now))
    return results


@pytest.mark.postgres
def test_independent_three_dimensions_and_restart(verification_environment):
    engine, service, result, spec, state = verification_environment
    results = collect(verification_environment)
    assert len(results) == 3 and all(r["assertion"] == "PASS" for r in results)
    assert state["calls"] == 1  # Action was DB-only; independent check really issued HEAD.
    assert (
        VerificationService(engine).create(ENV, result, spec, verifier(), now=AT) == spec.verification_spec_id
    )
    assert service.claim(ENV, verifier(), now=AT) is None
    with Session(engine) as db:
        rows = list(db.scalars(select(VerificationObservationRow)))
        assert len({r.evidence_id for r in rows}) == 3
        assert all(r.started_at > INSTANT and r.assertions and r.executor_version for r in rows)


@pytest.mark.postgres
@pytest.mark.parametrize("case", ["http500", "timeout", "offline", "stale", "missing_evidence"])
def test_check_execution_separate_from_assertion(verification_environment, case):
    engine, _, _, spec, state = verification_environment
    if case == "http500":
        state["status"] = 500
    if case == "timeout":
        state["delay"] = 1.2
    with Session(engine) as db, db.begin():
        if case in {"offline", "stale"}:
            sensor = db.scalar(select(SensorHealthRow))
            if case == "offline":
                sensor.status = "OFFLINE"
            else:
                sensor.last_heartbeat_at = AT - timedelta(seconds=121)
    if case == "missing_evidence":
        # Preserve immutable evidence; absent evidence is represented by a failed lookup at runtime.
        from zhiyu.db.models import EnvironmentRow
        from zhiyu.db.verification_runtime import VerificationRuntimeRow
        from zhiyu.verification.runtime import observation_health

        collect(verification_environment)
        with Session(engine) as db:
            runtime = db.get(VerificationRuntimeRow, spec.verification_spec_id)
            runtime.binding = {**runtime.binding, "input_evidence_ids": ["absent"]}
            with db.no_autoflush:
                assert (
                    observation_health(db, runtime, db.get(EnvironmentRow, ENV), AT)["evidence_fresh"]
                    is False
                )
        return
    collect(verification_environment)
    with Session(engine) as db:
        check = db.get(
            VerificationObservationRow,
            (
                spec.verification_spec_id,
                "business-health" if case in {"http500", "timeout"} else "observation-health",
            ),
        )
        assert check.execution_status == ("TIMEOUT" if case == "timeout" else "SUCCEEDED")
        assert check.assertion_status == ("INCONCLUSIVE" if case == "timeout" else "FAIL")


@pytest.mark.postgres
def test_fencing_two_workers_crash_and_duplicate_completion(verification_environment):
    _, service, result, spec, _ = verification_environment
    service.create(ENV, result, spec, verifier(), now=AT)
    # Isolate the final check so two workers contend for one logical identity.
    for _ in range(2):
        lease = service.claim(ENV, verifier(), now=AT)
        service.run_claim(ENV, lease, verifier(), now=AT)
    worker_b = verifier().model_copy(update={"principal_id": "verify-b"})
    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(pool.map(lambda p: service.claim(ENV, p, now=AT), [verifier(), worker_b]))
    assert sum(item is not None for item in leases) == 1
    old = next(item for item in leases if item)
    recovered = service.claim(ENV, verifier(), now=AT + timedelta(seconds=11))
    assert recovered["generation"] == 2
    with pytest.raises(LeaseLostError):
        service.run_claim(ENV, old, verifier(), now=AT + timedelta(seconds=11))
    first = service.run_claim(ENV, recovered, verifier(), now=AT + timedelta(seconds=11))
    repeat = VerificationService(service.engine).run_claim(
        ENV, recovered, verifier(), now=AT + timedelta(seconds=12)
    )
    assert first["evidence_id"] == repeat["evidence_id"] and repeat["duplicate"]


@pytest.mark.postgres
def test_executor_error_is_persisted(verification_environment, monkeypatch):
    from zhiyu.verification.runtime import VerificationCheckExecutor

    def fail(*args):
        raise OSError("unavailable")

    monkeypatch.setattr(VerificationCheckExecutor, "execute", fail)
    results = collect(verification_environment)
    assert all(r["status"] == "FAILED" and r["assertion"] == "INCONCLUSIVE" for r in results)


@pytest.mark.postgres
def test_identity_mutation_and_malformed_assertion(verification_environment):
    _, service, result, spec, _ = verification_environment
    service.create(ENV, result, spec, verifier(), now=AT)
    mutated = VerificationSpec.model_validate(spec.model_dump())
    mutated.checks[0].assertions[0].expected = 999
    with pytest.raises(ConflictError):
        service.create(ENV, result, mutated, verifier(), now=AT)
    mutated.checks[0].assertions[0].operator = "MATCHES"
    with pytest.raises(ValueError, match="unsupported"):
        validate_spec(mutated)


@pytest.mark.parametrize(
    "values,expected", [({}, "INCONCLUSIVE"), ({"status_code": 200}, "PASS"), ({"status_code": 500}, "FAIL")]
)
def test_explainable_assertion(values, expected):
    result = assert_value(values, AssertionSpec(field="status_code", operator="EQUALS", expected=200))
    assert result["outcome"] == expected and "observed" in result and result["operator"] == "EQUALS"


@pytest.mark.postgres
def test_cancel_fences_claim_and_never_fabricates_evidence(verification_environment):
    engine, service, result_id, spec, _ = verification_environment
    service.create(ENV, result_id, spec, verifier(), now=AT)
    lease = service.claim(ENV, verifier(), now=AT)
    assert service.cancel(ENV, spec.verification_spec_id, lease["check_id"], verifier())
    assert not service.cancel(ENV, spec.verification_spec_id, lease["check_id"], verifier())
    with pytest.raises(LeaseLostError):
        service.run_claim(ENV, lease, verifier(), now=AT)
    with Session(engine) as db:
        assert db.get(VerificationObservationRow, (spec.verification_spec_id, lease["check_id"])) is None


@pytest.mark.postgres
def test_verification_cannot_bypass_scope_probe_rate(verification_environment):
    from zhiyu.db.response_authority import ResponseControlRow

    _, service, result_id, spec, state = verification_environment
    service.create(ENV, result_id, spec, verifier(), now=AT)
    with Session(service.engine) as db, db.begin():
        db.get(ResponseControlRow, ENV).next_probe_at = AT + timedelta(seconds=2)
    for _ in range(2):
        lease = service.claim(ENV, verifier(), now=AT)
        assert lease["check_id"] != "business-health"
        service.run_claim(ENV, lease, verifier(), now=AT)
    assert service.claim(ENV, verifier(), now=AT) is None and state["calls"] == 0
    lease = service.claim(ENV, verifier(), now=AT + timedelta(seconds=2))
    assert lease["check_id"] == "business-health"
    assert service.run_claim(ENV, lease, verifier(), now=AT + timedelta(seconds=2))["assertion"] == "PASS"
    assert state["calls"] == 1
