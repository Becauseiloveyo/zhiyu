"""Local Web Console sessions. Browser users never receive control-plane service tokens."""

import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field

from zhiyu.api.security import bearer, require_principal
from zhiyu.core.identity import ServicePrincipal


class BrowserAccount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    access_key_sha256: str = Field(pattern=r"^[a-f0-9]{64}$", repr=False)
    principal: ServicePrincipal


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    access_key: str = Field(min_length=32, max_length=128, repr=False)


@dataclass(frozen=True)
class SessionRecord:
    username: str
    account_digest: str
    expires: float
    csrf: str


router = APIRouter(prefix="/v1/product/session", tags=["product-session"])
_sessions: dict[str, SessionRecord] = {}
_attempts: dict[str, list[float]] = {}
_lock = threading.Lock()
COOKIE = "zhiyu_session"
TTL = 1800


def origin_check(request: Request) -> None:
    from zhiyu.product.access import product_settings

    if request.headers.get("origin") not in product_settings.allowed_origins:
        raise HTTPException(403, "origin_not_allowed")


def session_record(request: Request) -> tuple[SessionRecord, ServicePrincipal]:
    from zhiyu.product.access import product_settings

    digest = hashlib.sha256(request.cookies.get(COOKIE, "").encode()).hexdigest()
    with _lock:
        record = _sessions.get(digest)
        account = product_settings.browser_users.get(record.username) if record else None
        if (
            not record
            or record.expires <= time.monotonic()
            or not account
            or not hmac.compare_digest(record.account_digest, account.access_key_sha256)
        ):
            _sessions.pop(digest, None)
            raise HTTPException(401, "session_expired")
    if not account.principal.permissions <= {"product:read", "demo:run"}:
        raise HTTPException(403, "browser_account_misconfigured")
    if "product:read" not in account.principal.permissions:
        raise HTTPException(403, "product_read_not_granted")
    return record, account.principal


def require_product_principal(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> ServicePrincipal:
    if credentials is not None:
        return require_principal(credentials)
    return session_record(request)[1]


def require_mutation(request: Request) -> ServicePrincipal:
    origin_check(request)
    record, principal = session_record(request)
    if not hmac.compare_digest(request.headers.get("x-zhiyu-csrf", ""), record.csrf):
        raise HTTPException(403, "csrf_required")
    return principal


@router.post("")
def login(body: Login, request: Request, response: Response) -> dict[str, object]:
    from zhiyu.product.access import product_settings

    origin_check(request)
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _lock:
        for key in [k for k, values in _attempts.items() if not values or values[-1] < now - 60]:
            del _attempts[key]
        attempts = _attempts.setdefault(client, [])
        attempts[:] = [at for at in attempts if at > now - 60]
        if len(attempts) >= 10 or len(_attempts) > 256:
            raise HTTPException(429, "login_rate_limited", headers={"Retry-After": "60"})
        attempts.append(now)
    account = product_settings.browser_users.get(body.username)
    digest = hashlib.sha256(body.access_key.encode()).hexdigest()
    if not hmac.compare_digest(digest, account.access_key_sha256 if account else "0" * 64):
        raise HTTPException(401, "invalid_credentials")
    assert account is not None
    # Browser identities cannot inherit arbitrary worker/admin permissions.
    if not account.principal.permissions <= {"product:read", "demo:run"}:
        raise HTTPException(403, "browser_account_misconfigured")
    if "product:read" not in account.principal.permissions:
        raise HTTPException(403, "product_read_not_granted")
    key, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with _lock:
        for identifier in [k for k, record in _sessions.items() if record.expires <= now]:
            del _sessions[identifier]
        if len(_sessions) >= 256:
            raise HTTPException(429, "session_capacity_exceeded")
        _sessions[hashlib.sha256(key.encode()).hexdigest()] = SessionRecord(
            body.username, account.access_key_sha256, now + TTL, csrf
        )
    response.set_cookie(
        COOKIE,
        key,
        max_age=TTL,
        httponly=True,
        samesite="strict",
        secure=product_settings.cookie_secure,
        path="/v1/product",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"principal_id": account.principal.principal_id, "csrf": csrf, "expires_in": TTL}


@router.get("")
def read_session(request: Request, response: Response) -> dict[str, object]:
    record, principal = session_record(request)
    response.headers["Cache-Control"] = "no-store"
    return {
        "principal_id": principal.principal_id,
        "csrf": record.csrf,
        "expires_in": max(0, int(record.expires - time.monotonic())),
    }


@router.delete("")
def logout(request: Request, response: Response) -> dict[str, bool]:
    require_mutation(request)
    digest = hashlib.sha256(request.cookies.get(COOKIE, "").encode()).hexdigest()
    with _lock:
        _sessions.pop(digest, None)
    response.delete_cookie(COOKIE, path="/v1/product")
    response.headers["Cache-Control"] = "no-store"
    return {"logged_out": True}
