"""Regression for the live API fixture splitting its own three-event incident."""

# ruff: noqa: F811
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_response_api import live_authority  # noqa: F401
from test_response_authorization import authority_environment, response_environment  # noqa: F401

from zhiyu.db.models import EventGroupRow, EvidenceRow, IncidentRow


@pytest.mark.postgres
@pytest.mark.parametrize("second", [41, 43, 45])
def test_live_fixture_keeps_incident_at_five_minute_boundary(monkeypatch, request, second):
    import test_response_api

    class FixtureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 16, 13, 16, second, tzinfo=UTC)

    monkeypatch.setattr(test_response_api, "datetime", FixtureClock)
    engine, plan = request.getfixturevalue("live_authority")
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(EventGroupRow)) == 2
        assert db.scalar(select(func.count()).select_from(IncidentRow)) == 1
        assert db.scalar(select(func.count()).select_from(EvidenceRow)) == 3
        assert db.get(IncidentRow, plan.incident_id).status == "TRIAGED"
    assert len(plan.tasks) == 4
