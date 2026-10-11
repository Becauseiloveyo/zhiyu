"""v0.4 -> v0.5 -> v0.4 -> v0.5 preserves prior golden-chain rows."""

# ruff: noqa: F811
import hashlib
import json

import pytest
from alembic import command
from conftest import migration_config
from sqlalchemy import inspect, text
from test_response_authorization import authority_environment  # noqa: F401
from test_response_planner import response_environment  # noqa: F401
from test_verification_replan import closed_loop_environment, decide  # noqa: F401
from test_verification_runtime import verification_environment  # noqa: F401

from zhiyu.services.health import readiness


@pytest.mark.postgres
def test_v04_roundtrip_preserves_event_action_and_verification_data(closed_loop_environment):
    engine = closed_loop_environment[0]
    decide(closed_loop_environment, "FAIL")
    with engine.begin() as c:
        names = set(inspect(c).get_table_names()) - {
            "alembic_version",
            "ai_state_snapshots",
            "decision_contexts",
            "ai_incident_budgets",
            "model_requests",
            "model_receipts",
            "ai_situation_analyses",
            "ai_plan_proposals",
            "ai_decisions",
        }
        assert len(names) == 63

        def digest():
            rows = {
                n: sorted(c.scalars(text('SELECT row_to_json(r)::text FROM "' + n + '" r')).all())
                for n in sorted(names)
            }
            return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()

        before = digest()
        command.downgrade(migration_config(c), "0010_replan")
        assert digest() == before and len(inspect(c).get_table_names()) == 64
        command.upgrade(migration_config(c), "head")
        assert digest() == before and len(inspect(c).get_table_names()) == 72
    assert readiness(engine)["status"] == "ready"
