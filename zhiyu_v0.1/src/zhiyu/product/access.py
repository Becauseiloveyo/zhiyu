"""Current read grants, distinct from historical execution authorization."""

import hashlib
import json
import re
from dataclasses import dataclass

from fastapi import HTTPException
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import and_, exists, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.incident_intelligence import IncidentEventRow
from zhiyu.db.infrastructure import EventResourceRow, ScopeResourceRow
from zhiyu.db.models import EventRow, IncidentRow, ScopeRow, TaskRow, VerificationResultRow
from zhiyu.product.contracts import DTO, Query, ReadGrant
from zhiyu.product.demo_contracts import DemoProfile
from zhiyu.product.sessions import BrowserAccount


# Defined here to avoid a circular dependency between the archive reader and authorization.
class RecordingRegistration(DTO):
    environment_id: str
    scope_id: str
    title: str = Field(min_length=1, max_length=160)
    filename: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}\.json$")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_run_id: str = Field(min_length=1, max_length=160)
    model_source: str = Field(pattern=r"^(NONE|REAL_LOCAL_MODEL|SCRIPTED_NOT_AI|UNKNOWN)$")


class ProductSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZHIYU_PRODUCT_", extra="ignore")
    grants: dict[str, dict[str, ReadGrant]] = Field(default_factory=dict)
    browser_users: dict[str, BrowserAccount] = Field(default_factory=dict, repr=False)
    allowed_origins: frozenset[str] = frozenset(
        {"http://127.0.0.1:8000", "http://localhost:8000", "http://127.0.0.1:8772", "http://localhost:8772"}
    )
    cookie_secure: bool = False
    recording_root: str = "artifacts/v0.9/recordings"
    recordings: dict[str, RecordingRegistration] = Field(default_factory=dict)
    demo_profiles: dict[str, DemoProfile] = Field(default_factory=dict)


product_settings = ProductSettings()


@dataclass(frozen=True)
class Access:
    principal_id: str
    environment_id: str
    scope_ids: frozenset[str]
    resources: tuple[str, ...]
    unrestricted: bool
    version: str
    fingerprint: str


def read_grant(db: Session, principal: ServicePrincipal, environment_id: str) -> tuple[ReadGrant, str | None]:
    """Demo child reads inherit only a registered parent's current scope and resource ceiling.

    This never expands the principal for core writes or execution APIs.
    """
    from zhiyu.db.demo_control import DemoRunRow

    configured = product_settings.grants.get(principal.principal_id, {})
    grant = configured.get(environment_id)
    if grant:
        principal.require("product:read", environment_id)
        return grant, None
    if product_settings.demo_profiles and re.fullmatch(r"m6-real-demo-[a-f0-9]{32}", environment_id):
        row = db.get(DemoRunRow, environment_id.removeprefix("m6-real-"))
        if row:
            profile = product_settings.demo_profiles.get(row.profile_id)
            parent = configured.get(row.environment_id)
            if (
                profile
                and profile.environment_id == row.environment_id
                and profile.scope_id == row.scope_id
                and parent
                and (parent.whole_environment or row.scope_id in parent.scope_ids)
            ):
                principal.require("product:read", row.environment_id)
                version = hashlib.sha256(
                    (parent.version + row.run_id + row.template_sha256).encode()
                ).hexdigest()
                return ReadGrant(version="demo-" + version, scope_ids=frozenset({row.scope_id})), row.environment_id
    raise HTTPException(403, "product_read_not_granted")


def authorize(db: Session, principal: ServicePrincipal, query: Query) -> Access:
    grant, parent_environment = read_grant(db, principal, query.environment_id)
    if not grant or (not grant.whole_environment and not grant.scope_ids):
        raise HTTPException(403, "product_read_not_granted")
    scopes = grant.scope_ids
    if query.scope_id:
        if not grant.whole_environment and query.scope_id not in scopes:
            raise HTTPException(403, "product_scope_not_granted")
        scopes = frozenset({query.scope_id})
    unrestricted = grant.whole_environment and not query.scope_id
    # Resolve current bindings on EVERY request, including cached-snapshot reads.
    existing = set(
        db.scalars(
            select(ScopeRow.scope_id).where(
                ScopeRow.environment_id == query.environment_id, ScopeRow.scope_id.in_(scopes)
            )
        )
    )
    if not unrestricted and (not existing or existing != set(scopes)):
        raise HTTPException(403, "product_scope_not_granted")
    resources = tuple(
        db.scalars(
            select(ScopeResourceRow.resource_id)
            .where(
                ScopeResourceRow.environment_id == query.environment_id, ScopeResourceRow.scope_id.in_(scopes)
            )
            .distinct()
            .order_by(ScopeResourceRow.resource_id)
        )
    )
    if parent_environment:
        ceiling = set(
            db.scalars(
                select(ScopeResourceRow.resource_id).where(
                    ScopeResourceRow.environment_id == parent_environment,
                    ScopeResourceRow.scope_id.in_(scopes),
                )
            )
        )
        resources = tuple(resource for resource in resources if resource in ceiling)
    identity = [
        principal.principal_id,
        query.environment_id,
        grant.model_dump(mode="json"),
        sorted(scopes),
        resources,
        unrestricted,
    ]
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return Access(
        principal.principal_id,
        query.environment_id,
        scopes,
        resources,
        unrestricted,
        grant.version,
        fingerprint,
    )


def visible_incidents(access: Access):  # type: ignore[no-untyped-def]
    """Fail closed for mixed/unbound incident, event, task and verification resources."""
    from sqlalchemy import cast

    allowed = cast(list(access.resources), JSONB)
    criteria = [IncidentRow.environment_id == access.environment_id]
    if access.unrestricted:
        return criteria
    criteria += [
        func.jsonb_array_length(IncidentRow.affected_asset_ids) > 0,
        IncidentRow.affected_asset_ids.op("<@")(allowed),
    ]
    # Include denormalized Event references as well: incomplete lineage cannot hide resources.
    related_ids = func.jsonb_array_elements_text(IncidentRow.related_event_ids).table_valued("value")
    event_bound = exists(
        select(1).where(
            EventResourceRow.environment_id == EventRow.environment_id,
            EventResourceRow.event_id == EventRow.event_id,
        )
    )
    event_forbidden = exists(
        select(1).where(
            EventResourceRow.environment_id == EventRow.environment_id,
            EventResourceRow.event_id == EventRow.event_id,
            EventResourceRow.resource_id.not_in(access.resources),
        )
    )
    bad_event = (
        ~event_bound
        | event_forbidden
        | ~EventRow.source_resource_ids.op("<@")(allowed)
        | ~EventRow.target_resource_ids.op("<@")(allowed)
        | (EventRow.actor_resource_id.is_not(None) & EventRow.actor_resource_id.not_in(access.resources))
    )
    # Join FROM the small referenced ID set, not a correlated scan of the full event population.
    criteria.append(
        ~exists(
            select(1)
            .select_from(
                related_ids.outerjoin(
                    EventRow,
                    and_(
                        EventRow.environment_id == access.environment_id,
                        EventRow.event_id == related_ids.c.value,
                    ),
                )
            )
            .where(EventRow.event_id.is_(None) | bad_event)
            .correlate(IncidentRow)
        )
    )
    criteria.append(
        ~exists(
            select(1)
            .select_from(IncidentEventRow)
            .join(
                EventRow,
                and_(
                    EventRow.environment_id == IncidentEventRow.environment_id,
                    EventRow.event_id == IncidentEventRow.event_id,
                ),
            )
            .where(
                IncidentEventRow.environment_id == access.environment_id,
                IncidentEventRow.incident_id == IncidentRow.incident_id,
                bad_event,
            )
            .correlate(IncidentRow)
        )
    )
    criteria.append(
        ~exists(
            select(1).where(
                TaskRow.environment_id == access.environment_id,
                TaskRow.incident_id == IncidentRow.incident_id,
                (TaskRow.scope_id.not_in(access.scope_ids) | ~TaskRow.target_resource_ids.op("<@")(allowed)),
            )
        )
    )
    criteria.append(
        ~exists(
            select(1).where(
                VerificationResultRow.environment_id == access.environment_id,
                VerificationResultRow.incident_id == IncidentRow.incident_id,
                (
                    VerificationResultRow.scope_id.not_in(access.scope_ids)
                    | ~VerificationResultRow.target_ids.op("<@")(allowed)
                ),
            )
        )
    )
    return criteria
