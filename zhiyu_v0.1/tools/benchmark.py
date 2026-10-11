"""Synthetic service-level benchmark against real PostgreSQL, no external sensor traffic."""

import argparse
import hashlib
import json
import os
import platform
import time
from collections import defaultdict
from datetime import UTC, datetime
from ipaddress import IPv4Address
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from zhiyu import __version__
from zhiyu.adapters.base import AdapterContext
from zhiyu.adapters.registry import AdapterRegistry
from zhiyu.core.identity import ServicePrincipal
from zhiyu.core.intelligence_config import IntelligenceConfig
from zhiyu.db.session import get_engine
from zhiyu.services.bootstrap import BootstrapBundle, BootstrapService
from zhiyu.services.event_intelligence import EventIntelligenceEngine
from zhiyu.services.incident_engine import IncidentEngine
from zhiyu.services.intelligence_metrics import metrics
from zhiyu.services.raw_ingest import RawIngestService, RawInput

ROOT = Path(__file__).resolve().parents[1]


def measure(
    size: int,
    *,
    max_seconds: float | None = None,
    progress_path: Path | None = None,
    resume: dict | None = None,
    live_source_time: bool = False,
) -> dict:
    assert not (resume and live_source_time), "continuation must retain original event timestamps"
    environment = resume["environment_id"] if resume else "benchmark-" + str(size) + "-" + uuid4().hex[:8]
    engine = get_engine()
    bundle = BootstrapBundle.model_validate_json((ROOT / "config/bootstrap.lab.json").read_text())
    bundle.environment.environment_id = environment
    for resource in bundle.resources:
        resource.environment_id = environment
    for scope in bundle.scopes:
        scope.environment_id = environment
    principal = ServicePrincipal(
        principal_id="synthetic-benchmark",
        environment_ids={environment},
        collector_ids={"sensor-suricata", "sensor-wazuh"},
        source_types={"suricata", "wazuh"},
        permissions={"events:write", "events:synthetic", "incidents:read", "intelligence:write"},
    )
    if resume is None:
        with Session(engine) as db:
            BootstrapService(db).apply(bundle, actor_id="synthetic-benchmark")
    # Explicit one-hour test window keeps slow benchmark ingestion within one modeled interval.
    config = IntelligenceConfig(version="ei-config/benchmark-1h", auth_failure_window=3600)
    reference = datetime.now(UTC)
    if resume:
        assert resume["requested_events"] == size and resume["status"] == "PARTIAL_TIME_BUDGET"
        assert environment.startswith("benchmark-") and 0 < resume["events"] < size
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT count(*),min(source_timestamp),max(source_timestamp) FROM normalized_events WHERE environment_id=:env"
                ),
                {"env": environment},
            ).one()
            assert row[0] == resume["events"] and row[1] == row[2], (
                "resume requires exact existing dataset and original event timestamp"
            )
            reference = row[1]
    raw = []
    for index in range(size):
        source = "suricata" if index % 2 == 0 else "wazuh"
        ip = (
            str(IPv4Address("198.18.0.1") + index // 100)
            if size > 10000
            else "192.0.2." + str(index // 100 + 1)
        )
        if source == "suricata":
            value = {
                "timestamp": reference.isoformat(),
                "event_type": "alert",
                "src_ip": ip,
                "dest_ip": "10.77.20.10",
                "dest_port": 8080,
                "proto": "TCP",
                "alert": {"signature_id": 990002, "severity": 2, "action": "allowed"},
                "http": {"status": 401, "url": "/login"},
            }
        else:
            value = {
                "timestamp": reference.isoformat(),
                "id": environment + "/" + str(index),
                "agent": {"ip": "10.77.20.10"},
                "rule": {"id": "5716", "level": 9, "groups": ["authentication_failed"]},
                "data": {"srcip": ip, "dstport": 8080, "protocol": "TCP"},
            }
        raw.append((source, RawInput(json.dumps(value), environment + "/" + str(index))))
    registry = AdapterRegistry()
    start = time.perf_counter()
    for source, item in [] if resume else raw:
        registry.normalize(
            item.record,
            AdapterContext(
                environment,
                "sensor-" + source,
                source,
                reference,
                "db://benchmark/raw",
                "sensor-" + source,
                "SYNTHETIC",
                item.origin_event_id,
            ),
        )
    normalization_seconds = time.perf_counter() - start
    if resume:
        normalization_seconds = resume["normalization_seconds"]
    ingest_seconds = correlation_seconds = promotion_seconds = 0.0
    accepted = created_incidents = 0
    batch_samples = []
    if resume:
        ingest_seconds = resume["ingest_seconds"]
        correlation_seconds = resume["correlation_total_seconds"]
        promotion_seconds = resume["promotion_total_seconds"]
        accepted, created_incidents = resume["events"], resume["incidents_created"]
        batch_samples = list(resume["raw_batch_samples"])
    offset_start = accepted
    overall = time.perf_counter()
    for offset in range(offset_start, size, 1000):
        if max_seconds is not None and offset > offset_start and time.perf_counter() - overall >= max_seconds:
            break
        batch = {"offset": offset, "events": min(1000, size - offset)}
        sources = defaultdict(list)
        source_time = datetime.now(UTC).isoformat() if live_source_time else reference.isoformat()
        for source, item in raw[offset : offset + 1000]:
            if live_source_time:
                value = json.loads(item.record)
                value["timestamp"] = source_time
                item = RawInput(json.dumps(value), item.origin_event_id)
            sources[source].append(item)
        batch["source_timestamp"] = source_time
        start = time.perf_counter()
        for source, items in sources.items():
            with Session(engine) as db:
                result = RawIngestService(db).ingest(
                    items,
                    environment_id=environment,
                    collector_id="sensor-" + source,
                    source_type=source,
                    principal=principal,
                    data_origin="SYNTHETIC",
                )
                assert result["errors"] == 0 and result["duplicates"] == 0
                accepted += result["accepted"]
        batch["ingest_ms"] = (time.perf_counter() - start) * 1000
        ingest_seconds += batch["ingest_ms"] / 1000
        start = time.perf_counter()
        with Session(engine) as db:
            EventIntelligenceEngine(db, config).process(environment, principal=principal)
        batch["group_correlate_ms"] = (time.perf_counter() - start) * 1000
        correlation_seconds += batch["group_correlate_ms"] / 1000
        start = time.perf_counter()
        with Session(engine) as db:
            created_incidents += IncidentEngine(db).promote(environment, principal=principal)["created"]
        batch["promotion_ms"] = (time.perf_counter() - start) * 1000
        promotion_seconds += batch["promotion_ms"] / 1000
        batch_samples.append(batch)
        progress = {
            "accepted": accepted,
            "requested": size,
            "environment": environment,
            "elapsed_seconds": time.perf_counter() - overall,
            "last_batch": batch,
        }
        if progress_path is not None:
            progress_path.write_text(json.dumps(progress, indent=2), encoding="utf-8")
        print(json.dumps(progress), flush=True)
    elapsed = time.perf_counter() - overall
    if resume:
        elapsed += resume["pipeline_total_seconds"]
    with Session(engine) as db:
        measured = metrics(db, environment, principal)
    assert accepted > 0 and measured["pending_event_count"] == 0 and measured["adapter_error_count"] == 0
    if max_seconds is None:
        assert accepted == size
    return {
        "status": "COMPLETED" if accepted == size else "PARTIAL_TIME_BUDGET",
        "requested_events": size,
        "events": accepted,
        "max_pipeline_seconds": max_seconds,
        "budget_semantics": "Checked between complete 1000-event batches; do not kill an active transaction",
        "environment_id": environment,
        "reference_timestamp": reference.isoformat(),
        "source_timestamp_policy": "actual batch generation time"
        if live_source_time
        else "fixed initial timestamp",
        "resumed_from_events": offset_start,
        "timing_scope": "Cumulative active pipeline time; excludes any pause between recorded segments. Standalone normalization measured once for all requested inputs.",
        "normalization_seconds": normalization_seconds,
        "normalization_events_per_second": size / normalization_seconds,
        "ingest_seconds": ingest_seconds,
        "ingest_events_per_second": accepted / ingest_seconds,
        "correlation_total_seconds": correlation_seconds,
        "promotion_total_seconds": promotion_seconds,
        "pipeline_total_seconds": elapsed,
        "incidents_created": created_incidents,
        "config": config.model_dump(),
        "metrics": measured,
        "raw_batch_samples": batch_samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[1000, 10000])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float)
    args = parser.parse_args()
    if any(size not in (1000, 10000, 100000) for size in args.sizes):
        raise ValueError("supported benchmark sizes: 1000,10000,100000")
    if args.max_seconds is not None and args.max_seconds <= 0:
        raise ValueError("time budget must be positive")
    with get_engine().connect() as connection:
        postgres = connection.scalar(text("SELECT version()"))
    report = {
        "label": "SYNTHETIC service-level benchmark; not production performance; no HTTP serialization in timing",
        "started_at": datetime.now(UTC).isoformat(),
        "code_version": __version__,
        "source_digest": hashlib.sha256(
            b"".join(
                path.relative_to(ROOT / "src").as_posix().encode() + path.read_bytes()
                for path in sorted((ROOT / "src").rglob("*.py"))
            )
        ).hexdigest(),
        "host": {
            "python": platform.python_version(),
            "os": platform.platform(),
            "logical_cpus": os.cpu_count(),
            "postgres": postgres,
        },
        "results": [],
    }
    for size in args.sizes:
        report["results"].append(
            measure(
                size, max_seconds=args.max_seconds, progress_path=args.output.with_suffix(".progress.json")
            )
        )
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["finished_at"] = datetime.now(UTC).isoformat()
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("BENCHMARK_REPORT=" + str(args.output), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
