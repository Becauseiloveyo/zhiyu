"""Operator-managed capability definitions, separately measured/reported health."""

from datetime import datetime
from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ConflictError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from, values_for
from zhiyu.db.models import CapabilityHealthRow, CapabilityRow, EnvironmentRow
from zhiyu.db.response_authority import CapabilityConfigRow, CapabilityHealthObservationRow
from zhiyu.domain.contracts import CapabilityHealth, CapabilityManifest
from zhiyu.response.catalog import INPUTS, ProbeInput, manifest
from zhiyu.response.lab_protocol import CAPABILITY
from zhiyu.response.planner import emit, identity


class CapabilityRegistry:
    def __init__(self, db: Session) -> None:
        self.db = db

    def install(self, environment_id: str, principal: ServicePrincipal, *, lab: bool = False) -> None:
        principal.require("response:admin", environment_id)
        with self.db.begin():
            self.db.execute(select(func.pg_advisory_xact_lock(func.hashtext("zhiyu:capability-catalog"))))
            if (
                self.db.scalar(
                    select(EnvironmentRow)
                    .where(EnvironmentRow.environment_id == environment_id)
                    .with_for_update()
                )
                is None
            ):
                raise ReferenceError("environment missing")
            environment = self.db.get(EnvironmentRow, environment_id)
            assert environment is not None
            if lab and environment.deployment_stage != "LAB":
                raise ConflictError("Lab capability cannot be installed for production")
            for capability_id in [CAPABILITY] if lab else INPUTS:
                definition = manifest(capability_id)
                existing = self.db.get(CapabilityRow, (definition.capability_id, definition.version))
                if existing and contract_from(existing, CapabilityManifest) != definition:
                    raise ConflictError("capability version already has another definition")
                if not existing:
                    self.db.add(CapabilityRow(**values_for(definition, CapabilityRow)))
                    self.db.flush()
                if self.db.get(CapabilityConfigRow, (definition.capability_id, definition.version)) is None:
                    self.db.add(
                        CapabilityConfigRow(
                            capability_id=definition.capability_id,
                            version=definition.version,
                            active=True,
                            definition_hash=canonical_hash(definition.model_dump(mode="json")),
                            supported_resource_types=["NETWORK_ENDPOINT"]
                            if capability_id == CAPABILITY or INPUTS.get(capability_id) is ProbeInput
                            else [
                                "NETWORK_ENDPOINT",
                                "HOST",
                                "IDENTITY",
                                "KUBERNETES",
                                "CLOUD",
                                "SAAS",
                                "SECURITY_CONTROL",
                            ],
                            supported_profiles=["LAB"] if lab else ["LAB", "PILOT", "PRODUCTION"],
                            minimum_autonomy="CONTROLLED_AUTONOMY"
                            if capability_id == CAPABILITY or INPUTS.get(capability_id) is ProbeInput
                            else "OBSERVE_ONLY",
                            business_impact="LOW",
                            retry_policy={"kind": "READ_RECONCILE_ONLY", "max_attempts": 1}
                            if lab
                            else {"kind": "READ_ONLY_REPLAY", "max_attempts": 3},
                        )
                    )
                    emit(
                        self.db,
                        environment_id,
                        "CapabilityManifest",
                        f"{capability_id}:{definition.version}",
                        "CapabilityRegistered",
                        "definition is not authorization",
                        principal.principal_id,
                    )

    def resolve(self, capability_id: str, version: str) -> tuple[CapabilityManifest, CapabilityConfigRow]:
        row = self.db.get(CapabilityRow, (capability_id, version))
        config = self.db.get(CapabilityConfigRow, (capability_id, version))
        if row is None or config is None:
            raise ReferenceError("unknown capability or version")
        definition = contract_from(row, CapabilityManifest)
        if config.definition_hash != canonical_hash(definition.model_dump(mode="json")):
            raise ConflictError("capability definition changed without version")
        if not config.active or definition.integration_status == "DESIGN":
            raise ConflictError("inactive capability")
        return definition, config

    def record_health(self, health: CapabilityHealth, principal: ServicePrincipal) -> None:
        principal.require("response:admin", health.environment_id)
        with self.db.begin():
            self.db.scalar(
                select(EnvironmentRow)
                .where(EnvironmentRow.environment_id == health.environment_id)
                .with_for_update()
            )
            self.resolve(health.capability_id, health.capability_version)
            row = self.db.get(
                CapabilityHealthRow,
                (health.capability_id, health.capability_version, health.environment_id, health.worker_pool),
            )
            if row and row.checked_at > health.checked_at:
                raise ConflictError("out-of-order capability health")
            if row and row.checked_at == health.checked_at:
                if contract_from(row, CapabilityHealth) != health:
                    raise ConflictError("health timestamp reused with different observation")
                return
            values = values_for(health, CapabilityHealthRow)
            if row:
                for key, value in values.items():
                    setattr(row, key, value)
            else:
                self.db.add(CapabilityHealthRow(**values))
            self.db.flush()
            observation_id = identity(
                "caphealth",
                [
                    health.environment_id,
                    health.capability_id,
                    health.capability_version,
                    health.worker_pool,
                    health.checked_at.isoformat(),
                ],
            )
            if self.db.get(CapabilityHealthObservationRow, observation_id) is None:
                self.db.add(
                    CapabilityHealthObservationRow(
                        observation_id=observation_id,
                        environment_id=health.environment_id,
                        capability_id=health.capability_id,
                        capability_version=health.capability_version,
                        worker_pool=health.worker_pool,
                        checked_at=health.checked_at,
                        status=health.status,
                        latency_ms=health.latency_ms,
                        failure_reason=health.detail if health.status != "HEALTHY" else None,
                    )
                )
            emit(
                self.db,
                health.environment_id,
                "CapabilityHealth",
                f"{health.capability_id}:{health.capability_version}:{health.worker_pool}:{health.checked_at.isoformat()}",
                "CapabilityHealthRecorded",
                health.status,
                principal.principal_id,
            )

    def local_health(
        self, capability_id: str, environment_id: str, worker_pool: str, now: datetime
    ) -> CapabilityHealth:
        start = perf_counter()
        definition, _ = self.resolve(capability_id, "1.0.0")
        self.db.execute(select(1))
        return CapabilityHealth(
            capability_id=capability_id,
            capability_version=definition.version,
            environment_id=environment_id,
            worker_pool=worker_pool,
            status="HEALTHY" if capability_id in INPUTS else "UNVERIFIED",
            checked_at=now,
            latency_ms=int((perf_counter() - start) * 1000),
            queue_depth=0,
            running_count=0,
            detail="local structured adapter and database available; target reachability is not asserted",
        )

    def health_history(self, environment_id: str, capability_id: str, version: str, worker_pool: str) -> dict:
        base = select(func.max(CapabilityHealthObservationRow.checked_at)).where(
            CapabilityHealthObservationRow.environment_id == environment_id,
            CapabilityHealthObservationRow.capability_id == capability_id,
            CapabilityHealthObservationRow.capability_version == version,
            CapabilityHealthObservationRow.worker_pool == worker_pool,
        )
        return {
            "last_success": self.db.scalar(base.where(CapabilityHealthObservationRow.status == "HEALTHY")),
            "last_failure": self.db.scalar(base.where(CapabilityHealthObservationRow.status != "HEALTHY")),
        }
