import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from ipaddress import ip_address
from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from zhiyu.adapters.base import AdapterContext, AdapterError
from zhiyu.adapters.registry import AdapterRegistry
from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import AccessDenied, ConflictError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.infrastructure import RawDeliveryRow, RawRecordRow
from zhiyu.db.models import EnvironmentRow, ResourceRow
from zhiyu.repositories.audit import AuditRepository
from zhiyu.services.event_ingest import EventIngestService


@dataclass(frozen=True)
class RawInput:
    record: str
    origin_event_id: str | None = None


class RawIngestService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest(
        self,
        records: list[RawInput],
        *,
        environment_id: str,
        collector_id: str,
        source_type: str,
        principal: ServicePrincipal,
        data_origin: Literal["SYNTHETIC", "OBSERVED"] = "OBSERVED",
        received_at: datetime | None = None,
    ) -> dict[str, Any]:
        principal.require("events:write", environment_id)
        if collector_id not in principal.collector_ids or source_type not in principal.source_types:
            raise AccessDenied("unregistered collector/source")
        if data_origin == "SYNTHETIC":
            principal.require("events:synthetic", environment_id)
        if not 1 <= len(records) <= 1000 or any(
            len(x.record.encode("utf-8", "surrogatepass")) > 262144 for x in records
        ):
            raise ReferenceError("raw batch size limit")
        now, trace = received_at or datetime.now(UTC), str(uuid4())
        results: list[dict[str, Any]] = []
        with self.db.begin():
            env = self.db.scalar(
                select(EnvironmentRow)
                .where(EnvironmentRow.environment_id == environment_id)
                .with_for_update()
            )
            if env is None:
                raise ReferenceError("environment not bootstrapped")
            candidates: dict[str, list[str]] = {}
            endpoint_candidates: dict[tuple[str, int, str], list[str]] = {}
            for resource in self.db.scalars(
                select(ResourceRow).where(ResourceRow.environment_id == environment_id)
            ):
                for key in ("address", "ip", "host"):
                    value = resource.locator.get(key)
                    if not isinstance(value, str):
                        continue
                    try:
                        address = str(ip_address(value))
                    except (ValueError, TypeError):
                        continue
                    if resource.resource_type == "NETWORK_ENDPOINT":
                        endpoint = (address, int(resource.locator["port"]), resource.locator["protocol"])
                        endpoint_candidates.setdefault(endpoint, []).append(resource.resource_id)
                    else:
                        candidates.setdefault(address, []).append(resource.resource_id)
            # Ambiguous locators stay observables; never arbitrarily bind one asset.
            resources = {ip: ids[0] for ip, ids in candidates.items() if len(set(ids)) == 1}
            endpoints = {
                endpoint: ids[0] for endpoint, ids in endpoint_candidates.items() if len(set(ids)) == 1
            }
            provenance = principal.provenance_roots.get(
                f"{collector_id}/{source_type}", f"{collector_id}/{source_type}"
            )
            registry = AdapterRegistry()
            for index, item in enumerate(records):
                digest = hashlib.sha256(item.record.encode("utf-8", "surrogatepass")).hexdigest()
                raw_id = "raw-" + canonical_hash([environment_id, collector_id, source_type, digest])
                self.db.execute(
                    insert(RawRecordRow)
                    .values(
                        raw_id=raw_id,
                        environment_id=environment_id,
                        collector_id=collector_id,
                        source_type=source_type,
                        content=item.record.encode("utf-8", "surrogatepass"),
                        integrity_hash=digest,
                        received_at=now,
                    )
                    .on_conflict_do_nothing()
                )
                raw_ref = f"db://raw_records/{raw_id}"
                result: dict[str, Any] = {
                    "index": index,
                    "raw_ref": raw_ref,
                    "event_id": None,
                    "disposition": "ERROR",
                    "error_code": None,
                    "error_field": None,
                }
                start = perf_counter()
                duration = 0.0
                try:
                    event = registry.normalize(
                        item.record,
                        AdapterContext(
                            environment_id,
                            collector_id,
                            source_type,
                            now,
                            raw_ref,
                            provenance,
                            data_origin,
                            item.origin_event_id,
                            resources,
                            endpoints,
                        ),
                    )
                    duration = (perf_counter() - start) * 1000
                    saved = EventIngestService(self.db).ingest([event], principal=principal, nested=True)
                    result.update(
                        event_id=saved.event_ids[0], disposition="ACCEPTED" if saved.accepted else "DUPLICATE"
                    )
                except AdapterError as exc:
                    duration = (perf_counter() - start) * 1000
                    result.update(error_code=exc.code, error_field=exc.field)
                except (ConflictError, ReferenceError, AccessDenied) as exc:
                    result.update(error_code="contract_validation_error", error_field=exc.code)
                self.db.add(
                    RawDeliveryRow(
                        delivery_id=str(uuid4()),
                        environment_id=environment_id,
                        raw_id=raw_id,
                        trace_id=trace,
                        normalization_ms=duration,
                        created_at=now,
                        **{
                            key: result[key]
                            for key in ("event_id", "disposition", "error_code", "error_field")
                        },
                    )
                )
                results.append(result)
            counts = {
                key: sum(x["disposition"] == value for x in results)
                for key, value in (("accepted", "ACCEPTED"), ("duplicates", "DUPLICATE"), ("errors", "ERROR"))
            }
            AuditRepository(self.db).append(
                environment_id=environment_id,
                trace_id=trace,
                actor_id=principal.principal_id,
                object_kind="RawBatch",
                object_id=trace,
                operation="NORMALIZE",
                reason=f"raw={len(records)};accepted={counts['accepted']};duplicates={counts['duplicates']};errors={counts['errors']}",
            )
            self.db.flush()
        return {"trace_id": trace, **counts, "results": results}
