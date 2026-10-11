# Imported pytest fixtures intentionally share the injected parameter names.
# ruff: noqa: F811
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_response_authorization import authority_environment, authorize, claim_fixture  # noqa: F401
from test_response_planner import ENV, INSTANT, SCOPE, response_environment, response_principal  # noqa: F401

from zhiyu.core.errors import ConflictError, LeaseLostError
from zhiyu.db.models import (
    ActionAttemptRow,
    ActionRow,
    IncidentRow,
    ResourceRow,
    ScopeRow,
    TaskRow,
    VerificationResultRow,
)
from zhiyu.db.response_authority import ResponseControlRow
from zhiyu.db.response_execution import ActionResultRow
from zhiyu.response.executors import ExecutorOutput, ExecutorRegistry
from zhiyu.response.gateway import ActionGateway
from zhiyu.response.scheduler import TaskScheduler


def claim(engine, *, now=INSTANT, principal=None):
    with Session(engine) as db:
        return TaskScheduler(db).claim(ENV, principal or response_principal(), now=now)


class CountingRegistry(ExecutorRegistry):
    def __init__(self, engine, outcome=None):
        super().__init__(engine)
        self.calls = 0
        self.outcome = outcome

    def resolve(self, action):
        original = super().resolve(action)
        owner = self

        class Counted:
            version = original.version

            def execute(self, request):
                owner.calls += 1
                return owner.outcome or original.execute(request)

        return Counted()


def execute(engine, lease, *, registry=None, now=INSTANT, principal=None):
    principal = principal or response_principal()
    decision = authorize_with_generation(engine, lease, principal, now)
    return ActionGateway(engine, registry).dispatch(
        ENV, lease["task_id"], lease["generation"], decision.authorization_id, principal, now=now
    ), decision


def authorize_with_generation(engine, lease, principal, now):
    from zhiyu.response.authorization import AuthorizationService

    with Session(engine) as db:
        return AuthorizationService(db).authorize_task(
            ENV, lease["task_id"], generation=lease["generation"], principal=principal, now=now
        )


@pytest.mark.postgres
def test_scheduler_concurrency_dependency_and_real_database_executor(authority_environment):
    engine, plan = authority_environment
    workers = [
        response_principal(),
        response_principal().model_copy(update={"principal_id": "response-worker-b"}),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda p: claim(engine, principal=p), workers))
    assert sum(c is not None for c in claims) == 1
    first = next(c for c in claims if c)
    first_principal = next(p for p in workers if p.principal_id == first["worker_id"])
    registry = CountingRegistry(engine)
    result, decision = execute(engine, first, registry=registry, principal=first_principal)
    assert result["execution_outcome"] == "EXECUTION_SUCCESS" and result["side_effect"] == "NONE"
    assert registry.calls == 1
    replay = ActionGateway(engine, registry).dispatch(
        ENV,
        first["task_id"],
        first["generation"],
        decision.authorization_id,
        first_principal,
        now=INSTANT,
    )
    assert replay["disposition"] == "DUPLICATE" and registry.calls == 1
    for _ in range(2):
        next_lease = claim(engine)
        assert next_lease and next_lease["task_id"] in {t.task_id for t in plan.tasks[1:3]}
        assert execute(engine, next_lease, registry=registry)[0]["execution_outcome"] == "EXECUTION_SUCCESS"
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 3
        assert db.scalar(select(func.count()).select_from(ActionResultRow)) == 3
        assert db.get(IncidentRow, plan.incident_id).status == "TRIAGED"
        assert db.scalar(select(func.count()).select_from(VerificationResultRow)) == 0


@pytest.mark.postgres
def test_fencing_crash_after_executor_before_receipt_and_read_only_retry(authority_environment, monkeypatch):
    engine, _ = authority_environment
    registry = CountingRegistry(engine)
    gateway = ActionGateway(engine, registry)
    first = claim(engine)
    principal = response_principal()
    decision = authorize_with_generation(engine, first, principal, INSTANT)
    original = gateway.complete

    def crash(*args, **kwargs):
        raise RuntimeError("crash before receipt commit")

    monkeypatch.setattr(gateway, "complete", crash)
    with pytest.raises(RuntimeError, match="crash"):
        gateway.dispatch(ENV, first["task_id"], 1, decision.authorization_id, principal, now=INSTANT)
    assert registry.calls == 1
    with Session(engine) as db:
        previous_attempt = db.scalars(select(ActionAttemptRow)).one().attempt_id
        assert db.scalar(select(func.count()).select_from(ActionResultRow)) == 0
    assert claim(engine, now=INSTANT + timedelta(seconds=21)) is None
    second_principal = principal.model_copy(update={"principal_id": "second-worker"})
    second = claim(engine, now=INSTANT + timedelta(seconds=23), principal=second_principal)
    assert second["generation"] == 2 and second["task_id"] == first["task_id"]
    engine.dispose()
    result, _ = execute(
        engine, second, registry=registry, now=INSTANT + timedelta(seconds=23), principal=second_principal
    )
    assert result["execution_outcome"] == "EXECUTION_SUCCESS" and registry.calls == 2
    with pytest.raises(LeaseLostError):
        original(
            ENV,
            previous_attempt,
            1,
            principal,
            ExecutorOutput("EXECUTION_SUCCESS", {}),
            executor_name="old",
            executor_version="test",
            executor_ms=0,
            now=INSTANT + timedelta(seconds=24),
        )
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 1
        assert db.scalar(select(func.count()).select_from(ActionAttemptRow)) == 2
        assert db.get(ActionAttemptRow, previous_attempt).status == "EXECUTION_UNKNOWN"


@pytest.mark.postgres
def test_failure_retry_budget_and_dependency_cancellation(authority_environment):
    engine, plan = authority_environment
    registry = CountingRegistry(
        engine, ExecutorOutput("EXECUTION_FAILURE", {}, "injected_read_failure", True)
    )
    for seconds in [0, 2, 5]:
        now = INSTANT + timedelta(seconds=seconds)
        lease = claim(engine, now=now)
        assert lease["task_id"] == plan.tasks[0].task_id
        result, _ = execute(engine, lease, registry=registry, now=now)
        assert result["execution_outcome"] == "EXECUTION_FAILURE"
    assert claim(engine, now=INSTANT + timedelta(seconds=10)) is None
    with Session(engine) as db:
        root = db.get(TaskRow, plan.tasks[0].task_id)
        assert root.attempt_count == root.max_attempts == 3
        assert {db.get(TaskRow, t.task_id).status for t in plan.tasks[1:]} == {"CANCELLED"}
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 1


@pytest.mark.postgres
@pytest.mark.parametrize("case", ["digest", "expired", "scope", "stale_generation"])
def test_gateway_rejections_do_not_invoke_executor(authority_environment, case):
    engine, _ = authority_environment
    if case == "expired":
        with Session(engine) as db, db.begin():
            control = db.get(ResponseControlRow, ENV)
            control.configuration = {**control.configuration, "authorization_ttl_seconds": 5}
    lease = claim(engine)
    decision = authorize_with_generation(engine, lease, response_principal(), INSTANT)
    registry = CountingRegistry(engine)
    if case == "scope":
        with Session(engine) as db, db.begin():
            scope = db.get(ScopeRow, (SCOPE, ENV))
            scope.version = "revoked-old-binding"
    gateway = ActionGateway(engine, registry)
    kwargs = {"submitted_digest": "0" * 64} if case == "digest" else {}
    if case == "stale_generation":
        with pytest.raises(LeaseLostError):
            gateway.dispatch(
                ENV, lease["task_id"], 2, decision.authorization_id, response_principal(), now=INSTANT
            )
    else:
        result = gateway.dispatch(
            ENV,
            lease["task_id"],
            1,
            decision.authorization_id,
            response_principal(),
            now=INSTANT + timedelta(seconds=6) if case == "expired" else INSTANT,
            **kwargs,
        )
        assert result["execution_outcome"] in {"DENIED", "STALE"}
    assert registry.calls == 0


@pytest.fixture
def http_target():
    calls = []
    settings = {"status": 200, "delay": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            calls.append((self.command, self.path))
            time.sleep(settings["delay"])
            self.send_response(settings["status"])
            if settings["status"] == 302:
                self.send_header("Location", "http://127.0.0.1:1/never-follow")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, calls, settings
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.postgres
@pytest.mark.parametrize("mode", ["ok", "redirect", "timeout"])
def test_real_safe_http_probe_bounded_target_no_redirect_and_timeout(
    authority_environment, http_target, mode
):
    engine, _ = authority_environment
    port, calls, settings = http_target
    settings.update(status=302 if mode == "redirect" else 200, delay=1.2 if mode == "timeout" else 0)
    with Session(engine) as db, db.begin():
        db.get(ResourceRow, ("target-a", ENV)).locator = {
            "address": "127.0.0.1",
            "port": port,
            "protocol": "TCP",
        }
        db.get(ResourceRow, ("validation-a", ENV)).locator = {"address": "127.0.0.1", "os": "test-loopback"}
        scope = db.get(ScopeRow, (SCOPE, ENV))
        scope.network_constraints = [
            {
                "source_resource_ids": ["validation-a"],
                "target_resource_ids": ["target-a"],
                "destination_ports": [port],
                "protocols": ["TCP"],
            }
        ]
    task_id = claim_fixture(authority_environment, "safe_http_probe")
    decision = authorize(engine, task_id)
    result = ActionGateway(engine).dispatch(
        ENV, task_id, 1, decision.authorization_id, response_principal(), now=INSTANT
    )
    assert calls == [("HEAD", "/health")]
    assert result["execution_outcome"] == ("TIMEOUT" if mode == "timeout" else "EXECUTION_SUCCESS")
    assert result["side_effect"] == "NONE" and "verified" not in result
    if mode != "timeout":
        assert result["output"]["status_code"] == settings["status"]
        assert result["output"]["redirect_followed"] is False
    with Session(engine) as db, pytest.raises(IntegrityError), db.begin():
        db.get(ActionResultRow, result["attempt_id"]).output = {"forged": True}


@pytest.mark.postgres
def test_scheduler_cancellation_and_renewal_guards(authority_environment):
    engine, plan = authority_environment
    lease = claim(engine)
    with Session(engine) as db:
        deadline = TaskScheduler(db).renew(
            ENV, lease["task_id"], 1, response_principal(), now=INSTANT + timedelta(seconds=1)
        )
        assert deadline == INSTANT + timedelta(seconds=20)
    with Session(engine) as db, pytest.raises(LeaseLostError):
        TaskScheduler(db).renew(
            ENV, lease["task_id"], 1, response_principal(), now=INSTANT + timedelta(seconds=21)
        )
    with Session(engine) as db, pytest.raises(ConflictError):
        TaskScheduler(db).cancel(ENV, lease["task_id"], 1, response_principal(), now=INSTANT)
    with Session(engine) as db:
        task = db.get(TaskRow, plan.tasks[-1].task_id)
        version = task.row_version
    with Session(engine) as db:
        TaskScheduler(db).cancel(ENV, plan.tasks[-1].task_id, version, response_principal(), now=INSTANT)
    with Session(engine) as db:
        assert db.get(TaskRow, plan.tasks[-1].task_id).status == "CANCELLED"
