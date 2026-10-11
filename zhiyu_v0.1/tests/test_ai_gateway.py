"""Gateway failures use real HTTP/PostgreSQL; scripted text is labeled, not real AI evaluation."""

# ruff: noqa: F811
import hashlib
import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_ai_context import AT, CANARY, ai_principal, build
from test_response_authorization import authority_environment  # noqa: F401
from test_response_planner import ENV, response_environment  # noqa: F401

from zhiyu.ai.gateway import ModelGateway
from zhiyu.ai.policy import AIBudget, AIPolicy
from zhiyu.ai.provider import OpenAICompatibleProvider, ProviderConfig
from zhiyu.db.ai_gateway import AIIncidentBudgetRow, ModelReceiptRow, ModelRequestRow
from zhiyu.db.models import ActionRow, AuditEntryRow, EnvironmentRow, ModelRunRow, PlanRow


def analysis_output():
    return {
        "incident_summary": "Authentication signals require investigation",
        "supported_findings": [],
        "hypotheses": [],
        "evidence_gaps": ["Hostile intent unproven"],
        "affected_resources": [],
        "recommended_next_steps": ["collect scoped context"],
        "risk_observations": ["No containment established"],
        "uncertainty": "Evidence is incomplete",
        "confidence_semantics": "MODEL_SELF_REPORTED_UNCALIBRATED",
    }


@pytest.fixture
def http_provider():
    state = {
        "calls": 0,
        "requests": [],
        "fault": None,
        "delay": 0,
        "output": analysis_output(),
        "auth_seen": False,
    }

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            state["calls"] += 1
            state["requests"].append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            state["auth_seen"] = self.headers.get("Authorization", "").startswith("Bearer ")
            time.sleep(state["delay"])
            fault = state["fault"]
            if fault == "connection":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            code = (
                500
                if fault == "http500"
                else 429
                if fault == "rate_limit"
                else 302
                if fault == "redirect"
                else 200
            )
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            envelope = {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": json.dumps(state["output"])},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 80},
            }
            if fault == "refusal":
                envelope["choices"][0]["message"]["refusal"] = "Cannot help"
            if fault == "tool_call":
                envelope["choices"][0]["message"]["tool_calls"] = [{"function": {"name": "shell"}}]
            if fault == "truncated":
                envelope["choices"][0]["finish_reason"] = "length"
            if fault == "no_usage":
                envelope.pop("usage")
            raw = json.dumps(envelope).encode()
            if fault == "invalid_json":
                raw = b'{"broken":'
            if fault == "empty":
                raw = b"{}"
            if fault == "utf8":
                raw = b"\xff\xfe"
            if fault == "oversized":
                raw = b"x" * 131073
            if state.get("content_length"):
                self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = ProviderConfig(
        provider="scripted-http-test",
        location="LOCAL",
        endpoint=f"http://127.0.0.1:{server.server_port}/v1",
        model="SCRIPTED_NOT_AI",
        revision="fixture-v1",
        timeout_seconds=2,
    )
    yield state, config
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def gateway(fixture, provider, *, budget=AIBudget(), enabled=True):
    return ModelGateway(
        fixture[0], AIPolicy(enabled=enabled, provider_id=provider.provider, budget=budget), provider
    )


def test_http10_content_length_complete_response_is_not_connection_failure(http_provider):
    state, config = http_provider
    state["content_length"] = True
    response = OpenAICompatibleProvider().complete(config, {"model": config.model, "messages": []})
    assert json.loads(response.content) == state["output"]
    assert response.usage_known and response.output_tokens == 80


@pytest.mark.postgres
def test_http_model_run_persistence_tokens_replay_and_no_actions(authority_environment, http_provider):
    state, config = http_provider
    ctx = build(authority_environment)
    service = gateway(authority_environment, config)
    result = service.analyze(ENV, ctx["context_id"], ai_principal(), now=AT)
    assert result["status"] == "COMPLETED" and not result["fallback"] and state["calls"] == 1
    authority_environment[0].dispose()
    assert service.analyze(ENV, ctx["context_id"], ai_principal(), now=AT) == result
    with Session(authority_environment[0]) as db:
        run = db.get(ModelRunRow, result["model_run_id"])
        assert (run.input_tokens, run.output_tokens, run.schema_valid) == (100, 80, True)
        assert run.provider == config.provider and run.model_revision == "fixture-v1"
        assert db.scalar(select(func.count()).select_from(PlanRow)) == 1
        assert db.scalar(select(func.count()).select_from(ActionRow)) == 0
        assert db.scalar(select(AIIncidentBudgetRow.charged_tokens)) == 180
        receipt = db.get(ModelReceiptRow, result["request_id"])
        assert hashlib.sha256(receipt.output["original_text"].encode()).hexdigest() == run.output_hash
        assert {"ModelRunStarted", "ModelRunCompleted"} <= set(db.scalars(select(AuditEntryRow.operation)))
    assert all(set(m) == {"role", "content"} for m in state["requests"][0]["messages"])
    assert "tools" not in state["requests"][0]


@pytest.mark.postgres
@pytest.mark.parametrize(
    "fault,code",
    [
        ("http500", "HTTP_FAILURE"),
        ("rate_limit", "RATE_LIMIT"),
        ("invalid_json", "INVALID_JSON_OR_ENVELOPE"),
        ("empty", "EMPTY_OR_INVALID_RESPONSE"),
        ("utf8", "MALFORMED_UTF8"),
        ("refusal", "MODEL_REFUSAL"),
        ("tool_call", "TOOL_CALL_REJECTED"),
        ("truncated", "INCOMPLETE_RESPONSE"),
        ("oversized", "RESPONSE_TOO_LARGE"),
        ("redirect", "HTTP_FAILURE"),
    ],
)
def test_provider_failures_fallback_without_plan(authority_environment, http_provider, fault, code):
    state, config = http_provider
    state["fault"] = fault
    ctx = build(authority_environment)
    result = gateway(authority_environment, config).analyze(ENV, ctx["context_id"], ai_principal(), now=AT)
    assert result["status"] == "FALLBACK" and result["error_code"] == code and result["output"] is None
    with Session(authority_environment[0]) as db:
        assert db.scalar(select(func.count()).select_from(ModelRunRow)) == 1
        assert db.scalar(select(func.count()).select_from(PlanRow)) == 1


@pytest.mark.postgres
@pytest.mark.parametrize("fault", ["timeout", "connection", "schema", "secret"])
def test_timeout_invalid_output_and_secret_never_accepted(authority_environment, http_provider, fault):
    state, config = http_provider
    if fault == "timeout":
        state["delay"] = 0.3
        config = config.model_copy(update={"timeout_seconds": 0.1})
    elif fault == "connection":
        state["fault"] = "connection"
    elif fault == "schema":
        state["output"]["command"] = "disable firewall"
    else:
        state["output"]["incident_summary"] = CANARY
    result = gateway(authority_environment, config).analyze(
        ENV, build(authority_environment)["context_id"], ai_principal(), now=AT
    )
    expected = {
        "timeout": "TIMEOUT",
        "connection": "CONNECTION_FAILURE",
        "schema": "SCHEMA_INVALID",
        "secret": "UNSAFE_MODEL_OUTPUT",
    }
    assert result["error_code"] == expected[fault]
    assert CANARY not in json.dumps(result)
    with Session(authority_environment[0]) as db:
        assert CANARY not in json.dumps(db.scalar(select(ModelReceiptRow)).output)


@pytest.mark.postgres
def test_private_provider_credential_not_in_request_receipt_or_log(
    authority_environment, http_provider, monkeypatch, caplog
):
    state, config = http_provider
    monkeypatch.setenv("ZHIYU_SCRIPTED_PROVIDER_KEY", CANARY)
    config = config.model_copy(update={"api_key_env": "ZHIYU_SCRIPTED_PROVIDER_KEY"})
    result = gateway(authority_environment, config).analyze(
        ENV, build(authority_environment)["context_id"], ai_principal(), now=AT
    )
    assert result["status"] == "COMPLETED" and state["auth_seen"]
    assert CANARY not in json.dumps(state["requests"]) and CANARY not in caplog.text
    with Session(authority_environment[0]) as db:
        row = db.scalar(select(ModelRequestRow))
        assert CANARY not in json.dumps(row.input_body) and CANARY not in json.dumps(row.configuration)


@pytest.mark.postgres
@pytest.mark.parametrize("case", ["airgap", "classification", "disabled", "call_budget", "token_budget"])
def test_route_and_budget_deny_before_network(authority_environment, http_provider, case):
    state, config = http_provider
    engine, _ = authority_environment
    with Session(engine) as db, db.begin():
        env = db.get(EnvironmentRow, ENV)
        if case == "airgap":
            env.connectivity, env.model_policy, env.data_egress_policy = "AIR_GAPPED", "LOCAL_ONLY", "DENY"
        elif case == "classification":
            env.connectivity, env.model_policy, env.data_egress_policy = (
                "CONNECTED",
                "CLOUD_ALLOWED",
                "REDACT_THEN_ALLOW",
            )
    if case in {"airgap", "classification"}:
        config = config.model_copy(update={"location": "CLOUD", "endpoint": "https://provider.example/v1"})
    limits = (
        AIBudget(max_calls=0)
        if case == "call_budget"
        else AIBudget(max_tokens=1)
        if case == "token_budget"
        else AIBudget()
    )
    result = gateway(authority_environment, config, enabled=case != "disabled", budget=limits).analyze(
        ENV, build(authority_environment)["context_id"], ai_principal(), now=AT
    )
    assert result["fallback"] and state["calls"] == 0 and result["model_run_id"] is None
    with Session(engine) as db:
        assert db.scalar(select(AIIncidentBudgetRow.call_count)) == 0


@pytest.mark.postgres
def test_unknown_usage_keeps_conservative_reservation(authority_environment, http_provider):
    state, config = http_provider
    state["fault"] = "no_usage"
    result = gateway(authority_environment, config).analyze(
        ENV, build(authority_environment)["context_id"], ai_principal(), now=AT
    )
    assert result["status"] == "COMPLETED" and not result["usage_known"]
    with Session(authority_environment[0]) as db:
        assert db.scalar(select(AIIncidentBudgetRow.charged_tokens)) == db.scalar(
            select(ModelRequestRow.reserved_tokens)
        )
        assert db.scalar(select(ModelRunRow.input_tokens)) == 0


@pytest.mark.postgres
def test_two_workers_only_one_provider_call(authority_environment, http_provider):
    state, config = http_provider
    state["delay"] = 0.2
    service = gateway(authority_environment, config)
    ctx = build(authority_environment)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: service.analyze(ENV, ctx["context_id"], ai_principal(), now=AT), range(2))
        )
    assert state["calls"] == 1
    assert all(r["status"] in {"COMPLETED", "IN_PROGRESS"} for r in results)
    with Session(authority_environment[0]) as db:
        assert db.scalar(select(func.count()).select_from(ModelRunRow)) == 1


@pytest.mark.postgres
def test_interrupted_call_finishes_once_without_resampling(authority_environment, http_provider):
    _, config = http_provider

    class Crash(BaseException):
        pass

    class Interrupted:
        def complete(self, *args):
            raise Crash()

    ctx = build(authority_environment)
    policy = AIPolicy(enabled=True, provider_id=config.provider)
    service = ModelGateway(authority_environment[0], policy, config, adapter=Interrupted())
    with pytest.raises(Crash):
        service.analyze(ENV, ctx["context_id"], ai_principal(), now=AT)
    recovered = gateway(authority_environment, config)
    result = recovered.analyze(ENV, ctx["context_id"], ai_principal(), now=AT + timedelta(seconds=18))
    assert result["error_code"] == "INTERRUPTED_CALL" and result["fallback"]
    assert recovered.analyze(ENV, ctx["context_id"], ai_principal(), now=AT + timedelta(seconds=19)) == result
    with Session(authority_environment[0]) as db:
        assert db.scalar(select(func.count()).select_from(ModelRunRow)) == 1
        assert db.scalar(select(AIIncidentBudgetRow.call_count)) == 1


@pytest.mark.postgres
def test_failed_generation_still_accounts_provider_tokens(authority_environment, http_provider):
    state, config = http_provider
    state["fault"] = "truncated"
    result = gateway(authority_environment, config).analyze(
        ENV, build(authority_environment)["context_id"], ai_principal(), now=AT
    )
    assert result["fallback"] and result["usage_known"]
    with Session(authority_environment[0]) as db:
        run = db.get(ModelRunRow, result["model_run_id"])
        assert (run.input_tokens, run.output_tokens, run.cost_usd) == (100, 80, None)
        receipt = db.get(ModelReceiptRow, result["request_id"])
        assert receipt.provider_ms > 0 and receipt.output is None
        assert db.scalar(select(AIIncidentBudgetRow.charged_tokens)) == 180


@pytest.mark.postgres
@pytest.mark.parametrize(
    "table,key",
    [("model_runs", "run_id"), ("model_receipts", "request_id"), ("model_requests", "request_id")],
)
def test_model_receipts_and_terminal_requests_immutable(authority_environment, http_provider, table, key):
    _, config = http_provider
    result = gateway(authority_environment, config).analyze(
        ENV, build(authority_environment)["context_id"], ai_principal(), now=AT
    )
    value = result["model_run_id" if key == "run_id" else key]
    with pytest.raises(DBAPIError), authority_environment[0].begin() as db:
        db.execute(text(f"DELETE FROM {table} WHERE {key}=:id"), {"id": value})
