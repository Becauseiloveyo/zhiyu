"""Fresh 100k event load: generate timestamps at each batch, preserving late-event safeguards."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import benchmark
from m6_benchmarks import ROOT, database_metrics, distribution, inspect_environment

from zhiyu import __version__


def main():
    directory = Path("/load-output")
    output = directory / "events-streaming.json"
    assert not output.exists()
    report = {
        "status": "RUNNING",
        "code_version": __version__,
        "started_at": datetime.now(UTC).isoformat(),
        "source_digest": hashlib.sha256(
            b"".join(
                p.relative_to(ROOT / "src").as_posix().encode() + p.read_bytes()
                for p in sorted((ROOT / "src").rglob("*.py"))
            )
        ).hexdigest(),
        "initial_database": database_metrics(),
        "method": "100k fresh synthetic events, 1000 per batch. Each batch uses its actual generation time. Unchanged 1-hour correlation policy and 120-second lateness allowance; original fixed-time partial and late continuation retained separately.",
    }
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    value = benchmark.measure(
        100000,
        max_seconds=3600,
        progress_path=directory / "events-streaming.progress.json",
        live_source_time=True,
    )
    value["audit"] = inspect_environment(value["environment_id"])
    value["stage_batch_latency"] = {
        key: distribution([r[key] for r in value["raw_batch_samples"]])
        for key in ["ingest_ms", "group_correlate_ms", "promotion_ms"]
    }
    report.update(
        status="COMPLETED_MEASUREMENT",
        result=value,
        finished_at=datetime.now(UTC).isoformat(),
        final_database=database_metrics(),
    )
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert value["events"] == 100000 and value["metrics"]["pending_event_count"] == 0


if __name__ == "__main__":
    main()
