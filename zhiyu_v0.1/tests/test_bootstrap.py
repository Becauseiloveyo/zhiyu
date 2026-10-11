from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zhiyu.core.errors import AccessDenied, ConflictError, StaleVersionError
from zhiyu.db.models import AuditEntryRow, EnvironmentRow, ResourceRow
from zhiyu.repositories.audit import AuditRepository
from zhiyu.repositories.environments import EnvironmentRepository
from zhiyu.repositories.resources import ResourceRepository
from zhiyu.repositories.scopes import ScopeRepository
from zhiyu.services.bootstrap import BootstrapBundle, BootstrapService

pytestmark = pytest.mark.postgres


def test_bootstrap_is_atomic_repeatable_and_contract_roundtrips(pg_engine, bundle):
    with Session(pg_engine) as db:
        result = BootstrapService(db).apply(bundle, actor_id="test")
        assert result == {"environments": 1, "resources": 3, "scopes": 1}
        repeat = BootstrapService(db).apply(bundle, actor_id="test")
        assert repeat == {"environments": 0, "resources": 0, "scopes": 0}
        env = bundle.environment.environment_id
        assert EnvironmentRepository(db).get(env) == bundle.environment
        for resource in bundle.resources:
            assert ResourceRepository(db).get((env, resource.resource_id)) == resource
        for scope in bundle.scopes:
            assert ScopeRepository(db).get((env, scope.scope_id)) == scope
        assert db.scalar(select(func.count()).select_from(AuditEntryRow)) == 5
        assert AuditRepository(db).verify_chain(env)


def test_bootstrap_no_silent_overwrite(bootstrapped, bundle):
    bundle.resources[0].display_name = "mutated"
    with Session(bootstrapped) as db:
        with pytest.raises(ConflictError):
            BootstrapService(db).apply(bundle, actor_id="test")
        assert db.scalar(select(func.count()).select_from(ResourceRow)) == 3
        assert db.scalar(select(func.count()).select_from(AuditEntryRow)) == 5


def test_bootstrap_rejects_cross_environment_and_active_mode(pg_engine, bundle):
    invalid = bundle.model_dump()
    invalid["resources"][0]["environment_id"] = "outside"
    with pytest.raises(ValidationError):
        BootstrapBundle.model_validate(invalid)
    bundle.environment.active_validation = "SCOPED_PREAPPROVED"
    with Session(pg_engine) as db:
        with pytest.raises(AccessDenied):
            BootstrapService(db).apply(bundle, actor_id="test")
        assert db.scalar(select(func.count()).select_from(EnvironmentRow)) == 0


def test_bootstrap_audit_failure_rolls_back(pg_engine, bundle, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("audit failure")

    monkeypatch.setattr(AuditRepository, "append", fail)
    with Session(pg_engine) as db:
        with pytest.raises(RuntimeError):
            BootstrapService(db).apply(bundle, actor_id="test")
        assert db.scalar(select(func.count()).select_from(EnvironmentRow)) == 0


def test_concurrent_binding_updates_require_current_version(bootstrapped, bundle):
    barrier = Barrier(2)

    def change(address):
        resource = bundle.resources[0].model_copy(deep=True)
        resource.locator["address"] = address
        resource.binding_version = 2
        with Session(bootstrapped) as db:
            barrier.wait(timeout=10)
            try:
                BootstrapService(db).rebind_resource(resource, expected_version=1, actor_id="test")
            except StaleVersionError:
                return False
            return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(change, address) for address in ("10.77.20.11", "10.77.20.12")]
        assert sorted(f.result(timeout=20) for f in futures) == [False, True]
    with Session(bootstrapped) as db:
        row = db.get(
            ResourceRow,
            {
                "environment_id": bundle.environment.environment_id,
                "resource_id": bundle.resources[0].resource_id,
            },
        )
        assert row.row_version == row.binding_version == 2
        assert AuditRepository(db).verify_chain(bundle.environment.environment_id)


def test_audit_rows_are_append_only(bootstrapped):
    for operation in ("UPDATE audit_entries SET reason = 'tampered'", "DELETE FROM audit_entries"):
        with bootstrapped.begin() as connection, pytest.raises(IntegrityError):
            connection.execute(text(operation))


def test_missing_audit_stream_is_not_reported_as_verified(pg_engine):
    with Session(pg_engine) as db:
        assert AuditRepository(db).verify_chain("not-bootstrapped") is False
