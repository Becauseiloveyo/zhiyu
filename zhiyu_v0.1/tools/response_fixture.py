"""SYNTHETIC acceptance fixtures only; not a sensor or production provisioning service."""

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import values_for
from zhiyu.db.models import EnvironmentRow, SensorHealthRow
from zhiyu.domain.contracts import SensorHealth
from zhiyu.response.admin import ControlRequest, configure
from zhiyu.response.catalog import INPUTS
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.planner import emit
from zhiyu.response.registry import CapabilityRegistry
from zhiyu.services.bootstrap import BootstrapBundle, BootstrapService
from zhiyu.services.event_intelligence import EventIntelligenceEngine
from zhiyu.services.incident_engine import IncidentEngine
from zhiyu.services.incident_lifecycle import transition
from zhiyu.services.raw_ingest import RawIngestService, RawInput

ROOT = Path(__file__).resolve().parents[1]
SCOPE = "scope-lab-web"


def fixture_principal(environment, principal_id="response-benchmark"):
    return ServicePrincipal(
        principal_id=principal_id,
        environment_ids={environment},
        collector_ids={"sensor-suricata", "sensor-wazuh"},
        source_types={"suricata", "wazuh"},
        permissions={
            "events:write",
            "events:synthetic",
            "intelligence:write",
            "incidents:read",
            "incidents:write",
            "response:plan",
            "response:read",
            "response:execute",
            "response:admin",
            *["capability:" + c for c in INPUTS],
        },
    )


def batches(environment, target, port):
    fixture = json.loads((ROOT / "tests/fixtures/golden_chain_m2.json").read_text(encoding="utf-8"))
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    result = []
    for source in ("suricata", "wazuh"):
        records = []
        for item in fixture["records"]:
            if item["source_type"] != source:
                continue
            raw = copy.deepcopy(item["raw"])
            raw["timestamp"] = now.isoformat()
            if source == "suricata":
                raw["dest_ip"], raw["dest_port"] = target, port
            else:
                raw["agent"]["ip"], raw["data"]["dstport"] = target, port
            records.append({"record": json.dumps(raw), "origin_event_id": environment + "/" + item["origin"]})
        result.append(
            {
                "environment_id": environment,
                "collector_id": "sensor-" + source,
                "source_type": source,
                "data_origin": "SYNTHETIC",
                "records": records,
            }
        )
    return result


def refresh_health(engine, environment, principal):
    if not environment.startswith("m3-"):
        raise ValueError("synthetic response fixture environment required")
    principal.require("response:admin", environment)
    now = datetime.now(UTC)
    with Session(engine) as db, db.begin():
        env = db.scalar(
            select(EnvironmentRow).where(EnvironmentRow.environment_id == environment).with_for_update()
        )
        if env is None or env.owner_id != "SYNTHETIC-RESPONSE-ACCEPTANCE":
            raise ValueError("not an acceptance fixture")
        for sensor_id in env.required_sensor_ids:
            sensor = SensorHealth(
                sensor_id=sensor_id,
                environment_id=environment,
                status="HEALTHY",
                last_heartbeat_at=now,
                last_event_at=now,
                lag_seconds=0,
                lost_event_count=0,
                coverage_scope_ids=[SCOPE],
                coverage_validated=True,
                config_version="SYNTHETIC-ACCEPTANCE-NOT-REAL-SENSOR",
            )
            values = values_for(sensor, SensorHealthRow)
            row = db.get(SensorHealthRow, (sensor_id, environment))
            if row:
                for key, value in values.items():
                    setattr(row, key, value)
            else:
                db.add(SensorHealthRow(**values))
        emit(
            db,
            environment,
            "SensorHealth",
            now.isoformat(),
            "SyntheticSensorHealthFixture",
            "synthetic acceptance assertions; real sensor runtime NOT_RUN",
            principal.principal_id,
        )
    for capability in INPUTS:
        with Session(engine) as db:
            health = CapabilityRegistry(db).local_health(capability, environment, "response", now)
        with Session(engine) as db:
            CapabilityRegistry(db).record_health(health, principal)


def prepare(engine, environment, principal, target="10.77.20.10", source="10.77.30.10", port=8080, seed=True):
    if not environment.startswith("m3-"):
        raise ValueError("synthetic response fixture environment required")
    principal.require("response:admin", environment)
    with Session(engine) as db:
        if db.get(EnvironmentRow, environment):
            raise ValueError("acceptance setup requires a new environment")
    now = datetime.now(UTC)
    bundle = BootstrapBundle.model_validate_json((ROOT / "config/bootstrap.lab.json").read_text())
    bundle.environment.environment_id, bundle.environment.owner_id = (
        environment,
        "SYNTHETIC-RESPONSE-ACCEPTANCE",
    )
    bundle.environment.capability_allowlist = list(INPUTS)
    for resource in bundle.resources:
        resource.environment_id = environment
        if resource.resource_id == "target-a":
            resource.locator = {"address": target, "port": port, "protocol": "TCP"}
        elif resource.resource_id == "validation-a":
            resource.locator = {"address": source, "os": "Linux"}
    for scope in bundle.scopes:
        scope.environment_id = environment
        scope.allowed_capabilities = list(INPUTS)
        scope.capability_source_ids = {c: ["validation-a"] for c in INPUTS}
        scope.valid_from, scope.valid_until = now - timedelta(minutes=1), now + timedelta(hours=2)
        scope.network_constraints[0].destination_ports = [port]
    with Session(engine) as db:
        BootstrapService(db).apply(bundle, actor_id="SYNTHETIC-response-bootstrap")
    with Session(engine) as db:
        CapabilityRegistry(db).install(environment, principal)
    with Session(engine) as db, db.begin():
        env = db.scalar(
            select(EnvironmentRow).where(EnvironmentRow.environment_id == environment).with_for_update()
        )
        env.autonomy_mode, env.max_auto_risk, env.active_validation = (
            "CONTROLLED_AUTONOMY",
            "R2",
            "ISOLATED_ONLY",
        )
        emit(
            db,
            environment,
            "EnvironmentProfile",
            environment,
            "SyntheticLabControlEnabled",
            "explicit isolated response acceptance fixture",
            principal.principal_id,
        )
    with Session(engine) as db:
        configure(
            db,
            ControlRequest(
                environment_id=environment,
                expected_version=0,
                policy_version=bundle.environment.policy_version,
                enabled=True,
                configuration=ResponsePolicy(worker_sources={principal.principal_id: "validation-a"}),
                valid_from=now - timedelta(minutes=1),
                valid_until=now + timedelta(hours=2),
            ),
            principal,
        )
    refresh_health(engine, environment, principal)
    inputs = batches(environment, target, port)
    identifier = None
    if seed:
        for batch in inputs:
            with Session(engine) as db:
                result = RawIngestService(db).ingest(
                    [RawInput(**item) for item in batch["records"]],
                    environment_id=environment,
                    collector_id=batch["collector_id"],
                    source_type=batch["source_type"],
                    data_origin="SYNTHETIC",
                    principal=principal,
                )
                assert result["accepted"] == len(batch["records"]) and result["errors"] == 0
        with Session(engine) as db:
            EventIntelligenceEngine(db).process(environment, principal=principal)
        with Session(engine) as db:
            promotion = IncidentEngine(db).promote(environment, principal=principal)
            identifier = next(x["incident_id"] for x in promotion["results"] if x["incident_id"])
        with Session(engine) as db:
            transition(
                db,
                environment_id=environment,
                incident_id=identifier,
                target="TRIAGED",
                expected_version=1,
                principal=principal,
            )
    return {
        "environment_id": environment,
        "incident_id": identifier,
        "inputs": inputs,
        "sensor_health": "SYNTHETIC",
    }
