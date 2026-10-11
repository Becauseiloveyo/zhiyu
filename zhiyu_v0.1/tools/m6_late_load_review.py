"""Record the interrupted late-data workload and safely finish only already committed input."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from zhiyu.core.identity import ServicePrincipal
from zhiyu.core.intelligence_config import IntelligenceConfig
from zhiyu.db.session import get_engine
from zhiyu.repositories.audit import AuditRepository
from zhiyu.services.event_intelligence import EventIntelligenceEngine
from zhiyu.services.incident_engine import IncidentEngine
from zhiyu.services.intelligence_metrics import metrics


def main():
    directory = Path("/load-output")
    original = json.loads((directory / "events.json").read_text())["results"][-1]
    env = original["environment_id"]
    output = directory / "late-continuation-review.json"
    assert not output.exists() and env.startswith("benchmark-100000-")
    engine = get_engine()
    principal = ServicePrincipal(
        principal_id="synthetic-benchmark",
        environment_ids={env},
        collector_ids={"sensor-suricata", "sensor-wazuh"},
        source_types={"suricata", "wazuh"},
        permissions={"events:write", "events:synthetic", "incidents:read", "intelligence:write"},
    )
    with Session(engine) as db:
        before = metrics(db, env, principal)
    with engine.connect() as c:
        timing = c.execute(
            text(
                "SELECT min(source_timestamp),max(source_timestamp),min(ingested_at),max(ingested_at) FROM normalized_events WHERE environment_id=:env"
            ),
            {"env": env},
        ).one()
    report = {
        "status": "IN_PROGRESS",
        "environment_id": env,
        "recorded_at": datetime.now(UTC).isoformat(),
        "before": before,
        "timestamp_range": [value.isoformat() for value in timing],
        "reason": "Original timestamp crossed fixed 1-hour window plus 120-second grace during pause. Late inputs isolated per event; this is a different workload from 100-member timely groups. SIGINT stopped only the exact m6_finish_events.py test process; original logs and committed rows retained.",
    }
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    start = time.perf_counter()
    if before["pending_event_count"]:
        assert before["pending_event_count"] <= 1000
        with Session(engine) as db:
            report["recovery_process"] = EventIntelligenceEngine(
                db, IntelligenceConfig.model_validate(original["config"])
            ).process(env, principal=principal)
        with Session(engine) as db:
            report["recovery_promotion"] = IncidentEngine(db).promote(env, principal=principal)
    with Session(engine) as db:
        report["after"] = metrics(db, env, principal)
        report["audit_valid"] = AuditRepository(db).verify_chain(env)
    with engine.connect() as c:
        report["group_dispositions"] = [
            dict(row)
            for row in c.execute(
                text(
                    "SELECT disposition,status,count(*) AS groups FROM event_group_state WHERE environment_id=:env GROUP BY disposition,status"
                ),
                {"env": env},
            ).mappings()
        ]
    assert report["audit_valid"] and report["after"]["pending_event_count"] == 0
    assert report["after"]["normalized_event_count"] == before["normalized_event_count"]
    report.update(
        status="PASS_DURABILITY_AND_CLASSIFICATION_ONLY", recovery_seconds=time.perf_counter() - start
    )
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    prior = directory / "events-completed.json"
    value = json.loads(prior.read_text())
    value.update(status="ABORTED_WORKLOAD_CHANGED_TO_LATE", diagnosis=output.name)
    prior.write_text(json.dumps(value, indent=2), encoding="utf-8")
    print(
        json.dumps({"status": report["status"], "groups": report["group_dispositions"], "pending": 0}),
        flush=True,
    )


if __name__ == "__main__":
    main()
