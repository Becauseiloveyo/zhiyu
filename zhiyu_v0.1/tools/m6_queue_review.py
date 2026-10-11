"""Read-only final queue accounting for exactly the recorded Gate D environments."""

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from zhiyu.db.session import get_engine

OUTPUT = Path("/load-output")


def read(name):
    return json.loads((OUTPUT / name).read_text())


def main():
    path = OUTPUT / "load-queue-review.json"
    assert not path.exists(), "preserve previous observation"
    environments = set()
    expected_pending = 0
    for kind in ["response", "verification"]:
        report = read(kind + ".json")
        assert report["status"] == "COMPLETED_MEASUREMENT"
        for result in report["results"]:
            expected_pending += result["intentional_unexecuted_tail_tasks"]
            environments.update(chunk["environment_id"] for chunk in result["chunks"])
    environments.update(row["environment"] for row in read("soak.json")["cycles"])
    environments.update(
        row["environment"] for group in read("ai-load.json")["groups"] for row in group["results"]
    )
    environments.update(row["environment_id"] for row in read("events.json")["results"])
    environments.add(read("events-streaming.json")["result"]["environment_id"])
    params = {"envs": sorted(environments)}
    with get_engine().connect() as connection:
        states = {
            table: dict(
                connection.execute(
                    text(
                        "SELECT status,count(*) FROM "
                        + table
                        + " WHERE environment_id=ANY(:envs) GROUP BY status"
                    ),
                    params,
                ).all()
            )
            for table in ["tasks", "verification_checks", "model_requests"]
        }
        pending_outbox = connection.scalar(
            text("SELECT count(*) FROM outbox WHERE environment_id=ANY(:envs) AND published_at IS NULL"),
            params,
        )
        active_leases = connection.scalar(
            text("SELECT count(*) FROM tasks WHERE environment_id=ANY(:envs) AND status='RUNNING'"), params
        )
        pending_events = connection.scalar(
            text(
                "SELECT count(*) FROM normalized_events e WHERE e.environment_id=ANY(:envs) "
                "AND NOT EXISTS (SELECT 1 FROM event_group_members m WHERE m.event_id=e.event_id AND m.environment_id=e.environment_id)"
            ),
            params,
        )
        database = {
            "size_bytes": connection.scalar(text("SELECT pg_database_size(current_database())")),
            "connections": connection.scalar(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()")
            ),
        }
    actual_pending = sum(states["tasks"].get(status, 0) for status in ["QUEUED", "BLOCKED"])
    assert actual_pending == expected_pending
    assert active_leases == pending_events == 0
    assert set(states["tasks"]) <= {"SUCCEEDED", "QUEUED", "BLOCKED"}
    assert set(states["verification_checks"]) <= {"SUCCEEDED"}
    assert not set(states["model_requests"]) & {"RUNNING", "RESERVED"}
    result = {
        "status": "PASS_ACCOUNTED_BACKLOG",
        "observed_at": datetime.now(UTC).isoformat(),
        "environments": sorted(environments),
        "states": states,
        "database": database,
        "running_tasks": active_leases,
        "ungrouped_events": pending_events,
        "expected_intentional_pending_tasks": expected_pending,
        "actual_pending_tasks": actual_pending,
        "pending_outbox": pending_outbox,
        "outbox_semantics": "No consumer configured; retained durable backlog, not delivery proof.",
        "task_semantics": "Unexecuted response tails and deliberate diagnostic replan tasks; not stuck leased jobs.",
    }
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["status", "actual_pending_tasks", "pending_outbox"]}))


if __name__ == "__main__":
    main()
