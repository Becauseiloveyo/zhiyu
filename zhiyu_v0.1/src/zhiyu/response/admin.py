"""Explicit local operator setup; never changes Environment, Scope or sensor authority."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhiyu.core.config import settings
from zhiyu.core.errors import ConflictError, DomainError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.models import EnvironmentRow, ResourceRow
from zhiyu.db.response_authority import ResponseControlRow
from zhiyu.db.session import get_engine
from zhiyu.response.catalog import INPUTS
from zhiyu.response.config import ResponsePolicy
from zhiyu.response.planner import emit
from zhiyu.response.registry import CapabilityRegistry


class ControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment_id: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=0)
    policy_version: str = Field(min_length=1, max_length=128)
    enabled: bool = False
    configuration: ResponsePolicy
    valid_from: AwareDatetime
    valid_until: AwareDatetime


def configure(db: Session, request: ControlRequest, principal: ServicePrincipal) -> int:
    principal.require("response:admin", request.environment_id)
    with db.begin():
        env = db.scalar(
            select(EnvironmentRow)
            .where(EnvironmentRow.environment_id == request.environment_id)
            .with_for_update()
        )
        if env is None:
            raise ReferenceError("environment missing")
        now = db.scalar(select(func.clock_timestamp()))
        assert now is not None
        if (
            request.policy_version != env.policy_version
            or not request.valid_from <= now < request.valid_until
        ):
            raise ConflictError("current environment policy and active interval required")
        if (request.valid_until - request.valid_from).total_seconds() > 86400:
            raise ConflictError("response control interval exceeds one day")
        for resource_id in request.configuration.worker_sources.values():
            if db.get(ResourceRow, (resource_id, env.environment_id)) is None:
                raise ReferenceError("worker source must be a managed resource in this environment")
        for capability in set(env.capability_allowlist) & set(INPUTS):
            CapabilityRegistry(db).resolve(capability, "1.0.0")
        row = db.get(ResponseControlRow, env.environment_id)
        if request.expected_version != (row.row_version if row else 0):
            raise ConflictError("response control version changed")
        values = request.model_dump(exclude={"expected_version"})
        values["configuration"] = request.configuration.model_dump(mode="json")
        if row is None:
            row = ResponseControlRow(**values, next_probe_at=now)
            db.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        db.flush()
        emit(
            db,
            env.environment_id,
            "ResponseControl",
            f"{env.environment_id}:v{row.row_version}",
            "ResponseControlConfigured",
            "enabled" if row.enabled else "disabled",
            principal.principal_id,
        )
        return row.row_version


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--principal", required=True, help="existing configured local service principal")
    parser.add_argument(
        "--file", type=Path, help="strict ControlRequest JSON; expected_version=0 for first setup"
    )
    parser.add_argument("--install-catalog", action="store_true")
    parser.add_argument(
        "--refresh-health", action="store_true", help="measure local adapter/database availability only"
    )
    args = parser.parse_args()
    matches = [
        p
        for p in settings.service_tokens.values()
        if p.principal_id == args.principal and args.environment in p.environment_ids
    ]
    try:
        if len(matches) != 1:
            raise ReferenceError("configured operator identity required")
        principal = matches[0]
        principal.require("response:admin", args.environment)
        engine = get_engine()
        result: dict = {"environment_id": args.environment}
        if args.install_catalog:
            with Session(engine) as db:
                CapabilityRegistry(db).install(args.environment, principal)
            result["catalog"] = "INSTALLED"
        if args.file:
            request = ControlRequest.model_validate_json(args.file.read_text(encoding="utf-8"))
            if request.environment_id != args.environment:
                raise ReferenceError("configuration environment mismatch")
            with Session(engine) as db:
                result["version"] = configure(db, request, principal)
        if args.refresh_health:
            with Session(engine) as db:
                control = db.get(ResponseControlRow, args.environment)
                pool = (
                    ResponsePolicy.model_validate(control.configuration).worker_pool
                    if control
                    else "response"
                )
                observed = [
                    CapabilityRegistry(db).local_health(c, args.environment, pool, datetime.now(UTC))
                    for c in INPUTS
                ]
            for health in observed:
                with Session(engine) as db:
                    CapabilityRegistry(db).record_health(health, principal)
            result["local_health_observations"] = len(observed)
        print(json.dumps(result))
        return 0
    except DomainError as error:
        print(json.dumps({"status": "ERROR", "error_code": error.code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
