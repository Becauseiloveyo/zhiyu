"""Browser sessions cannot inherit worker access, leak keys or survive account revocation."""

import hashlib
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from zhiyu.core.config import settings
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.session import get_db
from zhiyu.main import app
from zhiyu.product import sessions
from zhiyu.product.access import product_settings
from zhiyu.product.contracts import ReadGrant
from zhiyu.product.sessions import BrowserAccount

KEY = "only-for-tests-" + "q" * 40
ORIGIN = "http://127.0.0.1:8000"


@pytest.fixture
def browser(monkeypatch):
    sessions._sessions.clear()
    sessions._attempts.clear()
    account = BrowserAccount(
        access_key_sha256=hashlib.sha256(KEY.encode()).hexdigest(),
        principal=ServicePrincipal(
            principal_id="viewer", environment_ids={"lab"}, permissions={"product:read"}
        ),
    )
    monkeypatch.setattr(product_settings, "browser_users", {"viewer": account})
    monkeypatch.setattr(settings, "service_tokens", {"1" * 64: account.principal})
    monkeypatch.setattr(
        product_settings,
        "grants",
        {
            "viewer": {
                "lab": ReadGrant(version="one", scope_ids={"scope-a"}),
                "foreign": ReadGrant(version="one", whole_environment=True),
            }
        },
    )
    def no_database():
        yield None

    app.dependency_overrides[get_db] = no_database
    try:
        with TestClient(app, headers={"Origin": ORIGIN}) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
    sessions._sessions.clear()
    sessions._attempts.clear()


def login(client, **overrides):
    return client.post("/v1/product/session", json={"username": "viewer", "access_key": KEY, **overrides})


def test_cookie_scope_csrf_and_logout(browser):
    assert browser.get("/v1/product/access").status_code == 401
    response = login(browser)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/v1/product" in cookie
    assert KEY not in response.text and hashlib.sha256(KEY.encode()).hexdigest() not in response.text
    assert response.headers["Cache-Control"] == "no-store"
    session = browser.get("/v1/product/session").json()
    assert session["principal_id"] == "viewer"
    access = browser.get("/v1/product/access")
    assert access.headers["Cache-Control"] == "no-store"
    assert access.json()["environments"] == [
        {"environment_id": "lab", "scope_ids": ["scope-a"], "whole_environment": False, "version": "one"}
    ]
    # The core API does not accept this browser cookie as a worker credential.
    assert browser.get("/v1/incidents", params={"environment_id": "lab"}).status_code == 401
    assert browser.delete("/v1/product/session").status_code == 403
    assert (
        browser.delete(
            "/v1/product/session",
            headers={"X-Zhiyu-CSRF": session["csrf"], "Origin": "https://foreign.invalid"},
        ).status_code
        == 403
    )
    assert browser.delete("/v1/product/session", headers={"X-Zhiyu-CSRF": session["csrf"]}).status_code == 200
    assert browser.get("/v1/product/session").status_code == 401


def test_login_rejects_untrusted_origin_unknown_user_and_secret_errors(browser):
    assert (
        browser.post(
            "/v1/product/session",
            json={"username": "viewer", "access_key": KEY},
            headers={"Origin": "https://foreign.invalid"},
        ).status_code
        == 403
    )
    assert login(browser, username="unknown").status_code == 401
    assert login(browser, access_key="z" * 40).status_code == 401
    invalid = login(browser, access_key="secret")
    assert invalid.status_code == 422 and "secret" not in invalid.text


@pytest.mark.parametrize("change", ["delete", "rotate", "elevate", "revoke", "expire"])
def test_active_account_changes_take_effect_immediately(browser, monkeypatch, change):
    assert login(browser).status_code == 200
    account = product_settings.browser_users["viewer"]
    if change == "expire":
        for digest, record in sessions._sessions.copy().items():
            sessions._sessions[digest] = replace(record, expires=0)
    elif change == "delete":
        monkeypatch.setattr(product_settings, "browser_users", {})
    elif change == "rotate":
        monkeypatch.setattr(
            product_settings,
            "browser_users",
            {"viewer": account.model_copy(update={"access_key_sha256": "0" * 64})},
        )
    else:
        permissions = {"product:read", "actions:execute"} if change == "elevate" else set()
        monkeypatch.setattr(
            product_settings,
            "browser_users",
            {
                "viewer": account.model_copy(
                    update={
                        "principal": account.principal.model_copy(
                            update={"permissions": frozenset(permissions)}
                        )
                    }
                )
            },
        )
    assert browser.get("/v1/product/access").status_code in {401, 403}


def test_privileged_browser_account_refused_and_attempts_bounded(browser, monkeypatch):
    account = product_settings.browser_users["viewer"]
    monkeypatch.setattr(
        product_settings,
        "browser_users",
        {
            "viewer": account.model_copy(
                update={
                    "principal": account.principal.model_copy(
                        update={"permissions": frozenset({"product:read", "actions:execute"})}
                    )
                }
            )
        },
    )
    assert login(browser).status_code == 403
    for _ in range(9):
        assert login(browser, access_key="wrong" * 8).status_code == 401
    limited = login(browser)
    assert limited.status_code == 429 and limited.headers["Retry-After"] == "60"
