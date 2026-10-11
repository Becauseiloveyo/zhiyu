from uuid import uuid4

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.core.errors import AccessDenied, ReferenceError
from zhiyu.db.models import EnvironmentRow
from zhiyu.domain.contracts import EnvironmentProfile, ResourceRef, ScopeDefinition
from zhiyu.repositories.audit import AuditRepository
from zhiyu.repositories.environments import EnvironmentRepository
from zhiyu.repositories.resources import ResourceRepository
from zhiyu.repositories.scopes import ScopeRepository


class BootstrapBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment: EnvironmentProfile
    resources: list[ResourceRef]
    scopes: list[ScopeDefinition]

    @model_validator(mode="after")
    def check_references(self) -> "BootstrapBundle":
        env = self.environment
        if any(r.environment_id != env.environment_id for r in self.resources) or any(
            s.environment_id != env.environment_id for s in self.scopes
        ):
            raise ValueError("bootstrap objects must belong to one environment")
        resource_ids = {r.resource_id for r in self.resources}
        scope_ids = {s.scope_id for s in self.scopes}
        if len(resource_ids) != len(self.resources) or len(scope_ids) != len(self.scopes):
            raise ValueError("duplicate bootstrap identity")
        if set(env.scope_ids) != scope_ids:
            raise ValueError("profile must name exactly the bundled scopes")
        for scope in self.scopes:
            if not set(scope.source_resource_ids + scope.target_resource_ids) <= resource_ids:
                raise ValueError("scope references resources absent from bootstrap")
            if not set(scope.allowed_capabilities) <= set(env.capability_allowlist):
                raise ValueError("scope capability list exceeds profile")
        return self


class BootstrapService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def apply(self, bundle: BootstrapBundle, *, actor_id: str) -> dict[str, int]:
        checked = BootstrapBundle.model_validate(bundle.model_dump())
        if (
            checked.environment.active_validation != "DISABLED"
            or checked.environment.autonomy_mode != "OBSERVE_ONLY"
        ):
            raise AccessDenied("M1 bootstrap registers passive environments only")
        trace_id = str(uuid4())
        counts = {"environments": 0, "resources": 0, "scopes": 0}
        with self.db.begin():
            env_repo = EnvironmentRepository(self.db)
            counts["environments"] = int(env_repo.create(checked.environment))
            # A single lock order covers bootstrap, event validation and binding updates.
            self.db.execute(
                select(EnvironmentRow)
                .where(
                    EnvironmentRow.environment_id == checked.environment.environment_id,
                )
                .with_for_update()
            ).one()
            audit = AuditRepository(self.db)
            if counts["environments"]:
                audit.append(
                    environment_id=checked.environment.environment_id,
                    trace_id=trace_id,
                    actor_id=actor_id,
                    object_kind="EnvironmentProfile",
                    object_id=checked.environment.environment_id,
                    operation="CREATE",
                    reason="passive M1 environment bootstrap",
                )
            for resource in sorted(checked.resources, key=lambda item: item.resource_id):
                if ResourceRepository(self.db).create(resource):
                    counts["resources"] += 1
                    audit.append(
                        environment_id=checked.environment.environment_id,
                        trace_id=trace_id,
                        actor_id=actor_id,
                        object_kind="ResourceRef",
                        object_id=resource.resource_id,
                        operation="CREATE",
                        reason="passive M1 bootstrap",
                    )
            for scope in sorted(checked.scopes, key=lambda item: item.scope_id):
                if ScopeRepository(self.db).create(scope):
                    counts["scopes"] += 1
                    audit.append(
                        environment_id=checked.environment.environment_id,
                        trace_id=trace_id,
                        actor_id=actor_id,
                        object_kind="ScopeDefinition",
                        object_id=scope.scope_id,
                        operation="CREATE",
                        reason="passive M1 bootstrap",
                    )
        return counts

    def rebind_resource(self, resource: ResourceRef, *, expected_version: int, actor_id: str) -> None:
        with self.db.begin():
            env = self.db.scalar(
                select(EnvironmentRow)
                .where(
                    EnvironmentRow.environment_id == resource.environment_id,
                )
                .with_for_update()
            )
            if env is None:
                raise ReferenceError("environment not found")
            ResourceRepository(self.db).replace_binding(resource, expected_version=expected_version)
            AuditRepository(self.db).append(
                environment_id=resource.environment_id,
                trace_id=str(uuid4()),
                actor_id=actor_id,
                object_kind="ResourceRef",
                object_id=resource.resource_id,
                operation="REBIND",
                reason=f"binding_version={resource.binding_version}",
            )
