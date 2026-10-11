"""Real PostgreSQL controller concurrency, crash fencing, explicit cleanup and HTTP security."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import DropSchema
from test_product_api import ENV, TOKEN
from test_product_api import client as shared_client

from zhiyu.api.routes.product import get_product_db
from zhiyu.core.config import settings
from zhiyu.db.demo_control import DemoRunRow, DemoStepRow
from zhiyu.db.models import ActionRow
from zhiyu.db.session import get_db
from zhiyu.main import app
from zhiyu.product import demo_control as controller
from zhiyu.product.access import product_settings
from zhiyu.product.contracts import Query
from zhiyu.product.demo_contracts import DemoCommand, DemoProfile, StartDemo, StepOutput
from zhiyu.product.demo_store import initialize
from zhiyu.product.sessions import BrowserAccount

pytestmark = pytest.mark.postgres
QUERY = Query(environment_id=ENV, scope_id="scope-lab-web")
START = StartDemo(scenario_id="B", profile_id="lab", idempotency_key="request_" + "1" * 24)


@pytest.fixture
def lab(bootstrapped, monkeypatch):
    # The original core regression's 72 tables remain intact; only this test owns this product schema.
    schema = "test_demo_" + uuid4().hex
    initialize(bootstrapped, schema)
    engine = bootstrapped.execution_options(schema_translate_map={"zhiyu_product": schema})
    fixture = shared_client.__wrapped__(bootstrapped, monkeypatch)
    client = next(fixture)
    principal = next(iter(settings.service_tokens.values())).model_copy(
        update={"permissions": {"product:read", "demo:run"}}
    )
    account = BrowserAccount(
        access_key_sha256=hashlib.sha256(TOKEN.encode()).hexdigest(), principal=principal
    )
    monkeypatch.setattr(product_settings, "browser_users", {"operator": account})
    monkeypatch.setattr(
        product_settings,
        "demo_profiles",
        {
            "lab": DemoProfile(
                environment_id=ENV,
                scope_id="scope-lab-web",
                scenarios={"A", "B", "C", "D", "E"},
                enabled=True,
            )
        },
    )

    def db_session():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = db_session
    app.dependency_overrides[get_product_db] = db_session
    try:
        yield engine, principal, client
    finally:
        fixture.close()
        with bootstrapped.begin() as db:
            db.execute(DropSchema(schema, cascade=True))


def create(lab):
    engine, principal, _ = lab
    with Session(engine) as db, db.begin():
        return controller.public_run(db, controller.start(db, principal, QUERY, START))


def change(lab, row, operation, **updates):
    engine, principal, _ = lab
    with Session(engine) as db, db.begin():
        result = controller.command(
            db,
            principal,
            QUERY,
            row["run_id"],
            operation,
            DemoCommand(expected_version=row["version"], **updates),
        )
        return controller.public_run(db, result)


def claim(lab, worker="test-worker"):
    with Session(lab[0]) as db, db.begin():
        return controller.claim(db, "lab", worker)


def finish(lab, work, **output):
    with Session(lab[0]) as db, db.begin():
        return controller.public_run(db, controller.finish(db, work, StepOutput(**output)))


def test_fixed_commands_reject_execution_parameters():
    for field in ("command", "target", "capability", "payload", "risk_override", "url"):
        with pytest.raises(ValidationError):
            StartDemo.model_validate({**START.model_dump(), field: "arbitrary"})
    with pytest.raises(ValidationError):
        StartDemo.model_validate({**START.model_dump(), "scenario_id": "shell"})


def test_concurrent_start_is_idempotent_and_only_one_worker_claims(lab):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(lab), range(2)))
    assert results[0]["run_id"] == results[1]["run_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        work = list(pool.map(lambda i: claim(lab, f"worker-{i}"), range(2)))
    assert sum(item is not None for item in work) == 1
    with Session(lab[0]) as db:
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0
        assert db.scalar(select(func.count()).select_from(DemoRunRow)) == 1


def test_duplicate_key_with_different_scenario_is_conflict(lab):
    create(lab)
    with Session(lab[0]) as db, db.begin(), pytest.raises(HTTPException) as raised:
        controller.start(db, lab[1], QUERY, START.model_copy(update={"scenario_id": "D"}))
    assert raised.value.status_code == 409


def test_crash_after_intent_never_redispatches_and_stale_completion_is_fenced(lab):
    create(lab)
    work = claim(lab)
    with Session(lab[0]) as db, db.begin():
        db.get(DemoRunRow, work.run_id).lease_until = controller.clock(db) - timedelta(seconds=1)
    with Session(lab[0]) as db, db.begin():
        assert controller.recover_expired(db, "lab") == 1
    assert claim(lab) is None
    with Session(lab[0]) as db:
        assert db.get(DemoRunRow, work.run_id).status == "NEEDS_RECONCILIATION"
        assert db.get(DemoStepRow, (work.run_id, 0)).status == "UNKNOWN"
    with pytest.raises(HTTPException) as raised:
        finish(lab, work)
    assert raised.value.detail == "demo_worker_fenced"


def test_cancel_inflight_waits_for_recorded_result_without_dispatching_next_step(lab):
    row = create(lab)
    work = claim(lab)
    with Session(lab[0]) as db:
        row = controller.public_run(db, db.get(DemoRunRow, row["run_id"]))
    row = change(lab, row, "cancel")
    assert row["status"] == "RUNNING" and row["cancel_requested"]
    row = finish(lab, work)
    assert row["status"] == "CANCELLED" and claim(lab) is None


def test_cleanup_must_be_independently_confirmed_before_reset(lab):
    row = change(lab, create(lab), "cancel")
    with pytest.raises(HTTPException):
        change(lab, row, "reset", idempotency_key="reset_" + "2" * 24)
    row = change(lab, row, "cleanup")
    row = finish(lab, claim(lab), cleanup_verified=False)
    assert row["cleanup_status"] == "NEEDS_MANUAL"
    with pytest.raises(HTTPException):
        change(lab, row, "reset", idempotency_key="reset_" + "2" * 24)


def test_reset_creates_new_generation_and_preserves_original_failure_and_steps(lab):
    row = create(lab)
    for _ in range(4):
        row = finish(lab, claim(lab), outcome="FAIL")
    assert row["status"] == "COMPLETED" and row["actual_outcome"] == "FAIL"
    row = change(lab, row, "cleanup")
    row = finish(lab, claim(lab), cleanup_verified=True)
    reset = change(lab, row, "reset", idempotency_key="reset_" + "2" * 24)
    again = change(lab, row, "reset", idempotency_key="reset_" + "2" * 24)
    assert reset["run_id"] == again["run_id"] != row["run_id"]
    assert reset["predecessor_id"] == row["run_id"]
    assert row["actual_outcome"] == "FAIL" and len(row["steps"]) == 5


def test_grant_revoked_before_worker_dispatch_blocks_queue(lab, monkeypatch):
    row = create(lab)
    monkeypatch.setattr(product_settings, "browser_users", {})
    assert claim(lab) is None
    with Session(lab[0]) as db:
        assert db.get(DemoRunRow, row["run_id"]).error_code == "DEMO_GRANT_OR_TEMPLATE_REVOKED"


def test_http_cookie_csrf_permission_and_scope_boundaries(lab, monkeypatch):
    _, principal, client = lab
    params = {"environment_id": ENV, "scope_id": "scope-lab-web"}
    path = "/v1/product/demos/runs"
    for endpoint in ("/v1/product/demos/catalog", path):
        listed = client.get(endpoint, params=params)
        assert listed.status_code == 200, listed.text
        assert listed.json()["projection_version"] == "0.9.0"
        assert listed.json()["run_mode"] == "LIVE"
    assert (
        client.post(
            path, params=params, json=START.model_dump(), headers={"Origin": "http://127.0.0.1:8000"}
        ).status_code
        == 401
    )
    login = client.post(
        "/v1/product/session",
        json={"username": "operator", "access_key": TOKEN},
        headers={"Origin": "http://127.0.0.1:8000"},
    )
    headers = {"Origin": "http://127.0.0.1:8000", "X-Zhiyu-CSRF": login.json()["csrf"]}
    assert (
        client.post(
            path, params=params, json=START.model_dump(), headers={"Origin": headers["Origin"]}
        ).status_code
        == 403
    )
    assert (
        client.post(
            path,
            params=params,
            json=START.model_dump(),
            headers={**headers, "Origin": "https://evil.invalid"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            path, params={**params, "scope_id": "other"}, json=START.model_dump(), headers=headers
        ).status_code
        == 403
    )
    response = client.post(path, params=params, json=START.model_dump(), headers=headers)
    assert response.status_code == 202, response.text
    assert response.json()["run"]["status"] == "QUEUED"
    account = product_settings.browser_users["operator"].model_copy(
        update={"principal": principal.model_copy(update={"permissions": {"product:read"}})}
    )
    monkeypatch.setattr(product_settings, "browser_users", {"operator": account})
    assert client.post(path, params=params, json=START.model_dump(), headers=headers).status_code == 403


def test_product_migration_preserves_core_inventory(lab):
    with lab[0].connect() as db:
        assert len(inspect(db).get_table_names()) == 72


def test_worker_rechecks_cancel_and_grant_before_external_operation(lab, monkeypatch):
    from zhiyu.product.demo_worker import once

    row = create(lab)

    class CancellingAdapter:
        def perform(self, work, current):
            assert current()
            with Session(lab[0]) as db:
                run = controller.public_run(db, db.get(DemoRunRow, work.run_id))
            change(lab, run, "cancel")
            assert not current()  # A pending operation is no longer allowed.
            return StepOutput()

    assert once(lab[0], "lab", CancellingAdapter()) == row["run_id"]
    with Session(lab[0]) as db:
        assert db.get(DemoRunRow, row["run_id"]).status == "CANCELLED"
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0


def test_worker_renewal_cannot_extend_total_step_budget(lab):
    create(lab)
    work = claim(lab)
    with Session(lab[0]) as db, db.begin():
        assert controller.renew(db, work)
        step = db.get(DemoStepRow, (work.run_id, work.position))
        step.started_at = controller.clock(db) - timedelta(seconds=controller.MAX_STEP_SECONDS + 1)
    with Session(lab[0]) as db, db.begin():
        assert not controller.renew(db, work)
    with pytest.raises(HTTPException):
        finish(lab, work)


def test_dynamic_recording_needs_completed_pinned_archive_in_authorized_child(lab, bundle):
    from zhiyu.product.access import Access
    from zhiyu.product.recordings import entries

    run = create(lab)
    access = Access(
        lab[1].principal_id,
        run["source_environment_id"],
        frozenset({"scope-lab-web"}),
        ("target-a",),
        False,
        "test",
        "test",
    )
    with Session(lab[0]) as db:
        assert entries(db, access) == {}
    for _ in range(3):
        finish(lab, claim(lab))
    finish(lab, claim(lab), artifact_sha256="a" * 64)
    with Session(lab[0]) as db:
        entry = entries(db, access)[run["run_id"]]
        assert entry.filename == run["run_id"] + ".json" and entry.sha256 == "a" * 64
        denied = Access(lab[1].principal_id, access.environment_id, frozenset({"other"}), (), False, "x", "x")
        assert entries(db, denied) == {}


def test_child_read_scope_is_bound_to_registered_parent_and_current_resource_ceiling(
    lab, bundle, monkeypatch
):
    from zhiyu.core.errors import AccessDenied
    from zhiyu.db.infrastructure import ScopeResourceRow
    from zhiyu.product.access import authorize
    from zhiyu.services.bootstrap import BootstrapService

    row = create(lab)
    child = row["source_environment_id"]
    bundle = bundle.model_copy(deep=True)
    bundle.environment.environment_id = child
    for resource in bundle.resources:
        resource.environment_id = child
    for scope in bundle.scopes:
        scope.environment_id = child
    with Session(lab[0]) as db:
        BootstrapService(db).apply(bundle, actor_id="test-owned-demo-bootstrap")
    with Session(lab[0]) as db:
        access = authorize(db, lab[1], Query(environment_id=child, scope_id="scope-lab-web"))
        assert "target-a" in access.resources and not access.unrestricted
    # Deriving a product read never alters core execution permission or the principal's environments.
    with pytest.raises(AccessDenied):
        lab[1].require("response:execute", child)
    listed = lab[2].get("/v1/product/access").json()["environments"]
    assert child in {entry["environment_id"] for entry in listed}
    with Session(lab[0]) as db, db.begin():
        for binding in db.scalars(
            select(ScopeResourceRow).where(
                ScopeResourceRow.environment_id == ENV, ScopeResourceRow.resource_id == "target-a"
            )
        ):
            db.delete(binding)
    with Session(lab[0]) as db:
        assert "target-a" not in authorize(db, lab[1], Query(environment_id=child)).resources
    monkeypatch.setattr(product_settings, "demo_profiles", {})
    with Session(lab[0]) as db, pytest.raises(HTTPException) as raised:
        authorize(db, lab[1], Query(environment_id=child))
    assert raised.value.status_code == 403
