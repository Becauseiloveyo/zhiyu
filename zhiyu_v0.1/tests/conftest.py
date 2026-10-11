import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateSchema, DropSchema

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/ai5"


def migration_config(connection=None):
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def fixture_objects():
    result = []
    for path in sorted(FIXTURES.glob("*.json")):
        result.extend(json.loads(path.read_text(encoding="utf-8")).get("objects", []))
    return result


@pytest.fixture
def bundle():
    from zhiyu.services.bootstrap import BootstrapBundle

    return BootstrapBundle.model_validate_json(
        (ROOT / "config/bootstrap.lab.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def principal():
    from zhiyu.core.identity import ServicePrincipal

    return ServicePrincipal(
        principal_id="test-collector",
        environment_ids={"lab-zhiyu-01"},
        collector_ids={"sensor-suricata", "sensor-wazuh"},
        source_types={"suricata", "wazuh_application_log", "wazuh_forwarded_suricata"},
        permissions={"events:write", "incidents:read"},
    )


@pytest.fixture
def event():
    from zhiyu.domain.contracts import NormalizedEvent

    obj = next(o for o in fixture_objects() if o.get("event_id") == "evt-net")
    # This M1 fixture is an ordinary synthetic delivery, NOT a registered validation run.
    obj["validation_run_id"] = None
    return NormalizedEvent.model_validate(obj)


@pytest.fixture
def pg_engine():
    url = os.environ.get("ZHIYU_TEST_DATABASE_URL")
    if not url:
        if os.environ.get("ZHIYU_REQUIRE_POSTGRES") == "1":
            pytest.fail("ZHIYU_TEST_DATABASE_URL is required; PostgreSQL tests may not be skipped")
        pytest.skip("set ZHIYU_TEST_DATABASE_URL to run real PostgreSQL integration tests")
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail("integration tests require PostgreSQL via psycopg")
    schema = "test_zhiyu_" + uuid4().hex
    admin = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 3})
    engine = None
    try:
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = create_engine(
            url,
            hide_parameters=True,
            pool_size=8,
            connect_args={
                "connect_timeout": 3,
                "options": f"-c search_path={schema} -c timezone=UTC -c statement_timeout=10000 -c lock_timeout=5000",
            },
        )
        with engine.begin() as connection:
            command.upgrade(migration_config(connection), "head")
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        # Delete only the unique schema created by THIS fixture; never public or another DB.
        assert schema.startswith("test_zhiyu_") and len(schema) == 43
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        admin.dispose()


@pytest.fixture
def bootstrapped(pg_engine, bundle):
    from sqlalchemy.orm import Session

    from zhiyu.services.bootstrap import BootstrapService

    with Session(pg_engine) as db:
        BootstrapService(db).apply(bundle, actor_id="test-bootstrap")
    return pg_engine
