"""Finish a bounded event run, retaining its partial result and active-time samples."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import benchmark
from m6_benchmarks import database_metrics, distribution, inspect_environment


def main():
    directory = Path("/load-output")
    original = directory / "events.json"
    output = directory / "events-completed.json"
    assert not output.exists()
    report = json.loads(original.read_text())
    prior = report["results"][-1]
    assert report["status"] == "COMPLETED_MEASUREMENT" and prior["requested_events"] == 100000
    assert prior["status"] == "PARTIAL_TIME_BUDGET"
    result = {
        "status": "RUNNING",
        "started_at": datetime.now(UTC).isoformat(),
        "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "original_file": "events.json",
        "initial_database": database_metrics(),
        "source_digest": report["source_digest"],
        "method": "Continue the same environment from its exact committed event count, using its original timestamp/identities and unchanged 1-hour correlation configuration. Cumulative active-time statistics exclude the pause; this is segmented load, not uninterrupted 100k throughput.",
    }
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    value = benchmark.measure(
        100000, max_seconds=3600, progress_path=directory / "events-finish.progress.json", resume=prior
    )
    value["audit"] = inspect_environment(value["environment_id"])
    value["stage_batch_latency"] = {
        key: distribution([r[key] for r in value["raw_batch_samples"]])
        for key in ["ingest_ms", "group_correlate_ms", "promotion_ms"]
    }
    result.update(
        status="COMPLETED_MEASUREMENT",
        result=value,
        finished_at=datetime.now(UTC).isoformat(),
        final_database=database_metrics(),
    )
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    assert value["events"] == 100000 and value["metrics"]["pending_event_count"] == 0


if __name__ == "__main__":
    main()
