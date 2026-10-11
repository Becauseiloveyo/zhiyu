"""Durable bounded model calls. Failures are receipts, never partially accepted plans."""

import hashlib
import os
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.ai.context_policy import ContextRedactor, messages, serialized
from zhiyu.ai.outputs import OUTPUTS
from zhiyu.ai.policy import AIPolicy
from zhiyu.ai.provider import (
    ModelProviderAdapter,
    OpenAICompatibleProvider,
    ProviderConfig,
    ProviderFailure,
    ProviderResponse,
    strict_json,
)
from zhiyu.core.canonical import canonical_hash
from zhiyu.core.errors import ConflictError, ReferenceError
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.ai_context import DecisionContextRow
from zhiyu.db.ai_gateway import AIIncidentBudgetRow, ModelReceiptRow, ModelRequestRow
from zhiyu.db.mapping import values_for
from zhiyu.db.models import ContextRow, EnvironmentRow, IncidentRow, ModelRunRow, ScopeRow
from zhiyu.domain.contracts import ModelRun
from zhiyu.response.planner import emit, identity
from zhiyu.verification.runtime import instant, lock_environment


def context_current(db: Session, context: DecisionContextRow, env: EnvironmentRow, at: datetime) -> bool:
    incident = db.get(IncidentRow, context.incident_id)
    scope = db.get(ScopeRow, (context.scope_id, env.environment_id))
    constraints = context.body["constraints"]
    return bool(
        incident
        and scope
        and context.created_at <= at < context.valid_until
        and incident.state_version == context.body["incident"]["state_version"]
        and env.version == constraints["environment_version"]
        and env.policy_version == constraints["policy_version"]
        and scope.version == constraints["scope_version"]
        and scope.scope_id in env.scope_ids
        and scope.valid_from <= at < scope.valid_until
        and canonical_hash(context.body) == context.context_hash
    )


def provider_allowed(
    env: EnvironmentRow, classification: str, policy: AIPolicy, config: ProviderConfig | None
) -> str | None:
    if not policy.enabled or not config or policy.provider_id != config.provider:
        return "MODEL_UNAVAILABLE"
    if config.location == "CLOUD":
        if (
            env.connectivity != "CONNECTED"
            or env.model_policy == "LOCAL_ONLY"
            or env.data_egress_policy == "DENY"
        ):
            return "CLOUD_EGRESS_DENIED"
        if classification not in policy.cloud_classifications:
            return "DATA_CLASSIFICATION_DENIED"
        if policy.budget.max_cost_usd is not None:
            return "COST_BOUND_UNAVAILABLE"
    return None


class ModelGateway:
    def __init__(
        self,
        engine: Engine,
        policy: AIPolicy,
        provider: ProviderConfig | None,
        *,
        adapter: ModelProviderAdapter | None = None,
    ) -> None:
        self.engine, self.policy, self.provider = engine, policy, provider
        self.adapter = adapter or OpenAICompatibleProvider()

    def analyze(
        self, env: str, context_id: str, principal: ServicePrincipal, *, now: datetime | None = None
    ) -> dict[str, Any]:
        return self.call(env, context_id, "ANALYSIS", principal, now=now)

    def propose_plan(
        self,
        env: str,
        context_id: str,
        principal: ServicePrincipal,
        *,
        analysis: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        return self.call(env, context_id, "PLAN", principal, analysis=analysis, now=now)

    def call(
        self,
        env: str,
        context_id: str,
        task: str,
        principal: ServicePrincipal,
        *,
        analysis: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if task not in OUTPUTS:
            raise ConflictError("unregistered model task")
        principal.require("ai:analyze" if task == "ANALYSIS" else "ai:plan", env)
        timer = perf_counter()
        owner = principal.principal_id + ":" + uuid4().hex
        with Session(self.engine) as db, db.begin():
            profile = lock_environment(db, env)
            at = instant(db, now)
            context = db.get(DecisionContextRow, context_id)
            if not context or context.environment_id != env:
                raise ReferenceError("context not found in environment")
            config = self.provider
            configuration = {
                "policy": self.policy.model_dump(mode="json"),
                "provider": config.public() if config else None,
            }
            body = self._input(context, task, analysis)
            request_id = identity(
                "model-request",
                [
                    env,
                    context.incident_id,
                    context.body["incident"]["state_version"],
                    context.context_hash,
                    self.policy.routing_version,
                    task,
                ],
            )
            previous = db.get(ModelRequestRow, request_id)
            if previous:
                if previous.configuration_hash != canonical_hash(
                    configuration
                ) or previous.input_hash != canonical_hash(body):
                    raise ConflictError("model request identity has changed inputs/configuration")
                receipt = db.get(ModelReceiptRow, request_id)
                if receipt:
                    return self._public(previous, receipt)
                if previous.lease_until > at:
                    return {
                        "request_id": request_id,
                        "status": "IN_PROGRESS",
                        "model_run_id": None,
                        "output": None,
                    }
                # Interrupted calls never automatically replay provider sampling. Reservation remains charged.
                return self._finish(db, previous, None, "INTERRUPTED_CALL", at, principal, timer, 0)
            frozen_context = db.get(ContextRow, context_id)
            assert frozen_context is not None
            denied = provider_allowed(profile, frozen_context.data_classification, self.policy, config)
            if not context_current(db, context, profile, at):
                denied = "STALE_CONTEXT"
            budget = db.get(AIIncidentBudgetRow, context.incident_id)
            limits = self.policy.budget
            if budget is None:
                budget = AIIncidentBudgetRow(
                    incident_id=context.incident_id,
                    environment_id=env,
                    configuration=limits.model_dump(mode="json"),
                    call_count=0,
                    charged_tokens=0,
                    input_tokens=0,
                    output_tokens=0,
                    ai_replans=0,
                    started_at=at,
                )
                db.add(budget)
            elif budget.configuration != limits.model_dump(mode="json"):
                denied = "BUDGET_CONFIGURATION_CHANGED"
            reservation = len(serialized(body).encode()) + (config.max_output_tokens if config else 0)
            is_replan = task == "PLAN" and context.body["incident"]["status"] == "VERIFYING"
            if not denied and is_replan and budget.ai_replans >= limits.max_ai_replans:
                denied = "AI_REPLAN_BUDGET_EXHAUSTED"
                emit(
                    db,
                    env,
                    "Incident",
                    context.incident_id,
                    "AIBudgetExceeded",
                    denied,
                    principal.principal_id,
                )
            if not denied and (
                budget.call_count >= limits.max_calls
                or budget.charged_tokens + reservation > limits.max_tokens
                or (at - budget.started_at).total_seconds() >= limits.max_wall_seconds
            ):
                denied = "AI_BUDGET_EXHAUSTED"
                emit(
                    db,
                    env,
                    "Incident",
                    context.incident_id,
                    "AIBudgetExceeded",
                    denied,
                    principal.principal_id,
                )
            row = ModelRequestRow(
                request_id=request_id,
                environment_id=env,
                incident_id=context.incident_id,
                context_id=context_id,
                task_type=task,
                routing_version=self.policy.routing_version,
                configuration_hash=canonical_hash(configuration),
                configuration=configuration,
                input_body=body,
                input_hash=canonical_hash(body),
                status="FALLBACK" if denied else "RUNNING",
                worker_id=None if denied else owner,
                reserved_tokens=0 if denied else reservation,
                started_at=at,
                lease_until=at + timedelta(seconds=(config.timeout_seconds if config else 1) + 15),
            )
            db.add(row)
            db.flush()
            if denied:
                return self._finish(db, row, None, denied, at, principal, timer, 0, attempted=False)
            budget.call_count += 1
            if is_replan:
                budget.ai_replans += 1
            budget.charged_tokens += reservation
            emit(
                db,
                env,
                "ModelRun",
                identity("model-run", request_id),
                "ModelRunStarted",
                "durable reservation before provider call; no executor privilege",
                principal.principal_id,
            )
        assert config is not None
        response: ProviderResponse | None = None
        error: str | None = None
        validation_ms = 0.0
        try:
            response = self.adapter.complete(config, body)
            check_start = perf_counter()
            parsed = strict_json(response.content)
            # Pydantic JSON mode accepts ISO aware timestamps while enforcing scalar/list types.
            validated = OUTPUTS[task].model_validate_json(serialized(parsed))
            content = validated.model_dump(mode="json")
            secrets = (os.environ.get(config.api_key_env, ""),) if config.api_key_env else ()
            if ContextRedactor(secrets).clean(content) != content:
                raise ProviderFailure("UNSAFE_MODEL_OUTPUT")
            if response.usage_known and (
                response.input_tokens > reservation - config.max_output_tokens
                or response.output_tokens > config.max_output_tokens
                or response.cached_tokens > response.input_tokens
            ):
                raise ProviderFailure("INVALID_TOKEN_ACCOUNTING")
            validation_ms = (perf_counter() - check_start) * 1000
        except ProviderFailure as exc:
            error = exc.code
            response = exc.response or response
        except (ValidationError, ValueError, TypeError, RecursionError):
            error = "SCHEMA_INVALID"
        except Exception:
            # Never persist provider exception text, request headers or raw error responses.
            error = "PROVIDER_INTERNAL_ERROR"
        with Session(self.engine) as db, db.begin():
            profile = lock_environment(db, env)
            finished = instant(db, None) if now is None else now + timedelta(seconds=perf_counter() - timer)
            current = db.get(ModelRequestRow, request_id)
            assert current is not None
            receipt = db.get(ModelReceiptRow, request_id)
            if receipt:
                return self._public(current, receipt)
            if current.worker_id != owner or current.lease_until <= finished:
                error = "INTERRUPTED_CALL"
            ctx = db.get(DecisionContextRow, context_id)
            assert ctx is not None
            if not context_current(db, ctx, profile, finished):
                error = "STALE_CONTEXT"
            route_error = provider_allowed(
                profile, ctx.body["constraints"]["classification"], self.policy, config
            )
            if route_error:
                error = route_error
            budget = db.get(AIIncidentBudgetRow, current.incident_id)
            assert budget is not None
            if (finished - budget.started_at).total_seconds() > self.policy.budget.max_wall_seconds:
                error = "AI_WALL_BUDGET_EXHAUSTED"
            return self._finish(db, current, response, error, finished, principal, timer, validation_ms)

    def _input(
        self, context: DecisionContextRow, task: str, analysis: dict[str, Any] | None
    ) -> dict[str, Any]:
        config = self.provider
        document = {**context.body, "task_type": task}
        if analysis is not None:
            document["prior_model_analysis_not_fact"] = (
                OUTPUTS["ANALYSIS"].model_validate_json(serialized(analysis)).model_dump(mode="json")
            )
        secrets = (os.environ.get(config.api_key_env, ""),) if config and config.api_key_env else ()
        if not ContextRedactor(secrets).safe_scalars(document):
            raise ConflictError("model input contains unredacted or oversized data")
        request: dict[str, Any] = {
            "model": config.model if config else "UNAVAILABLE",
            "messages": messages(document),
            "temperature": config.temperature if config else 0,
            "max_tokens": config.max_output_tokens if config else 0,
            "stream": False,
        }
        request["messages"][0]["content"] += (
            "\nTask: " + task + ". Be concise. Return at most ONE supported finding, ONE hypothesis, "
            "and ONE proposed task. Each narrative should be under 100 characters; other lists at most two items. "
            "Copy exact evidence/resource identifiers and observation times from the context. "
            "Prefer evidence gaps to guesses; a plan may choose only a listed read-only capability."
        )
        schema = OUTPUTS[task].model_json_schema()
        request["response_format"] = (
            {"type": "json_object", "schema": schema}
            if config and config.structured_format == "JSON_OBJECT_SCHEMA"
            else {
                "type": "json_schema",
                "json_schema": {"name": task.lower(), "strict": True, "schema": schema},
            }
        )
        return request

    def _finish(
        self,
        db: Session,
        request: ModelRequestRow,
        response: ProviderResponse | None,
        error: str | None,
        at: datetime,
        principal: ServicePrincipal,
        timer: float,
        validation_ms: float,
        *,
        attempted: bool = True,
    ) -> dict[str, Any]:
        output: dict[str, Any] | None = None
        if response and error is None:
            output = OUTPUTS[request.task_type].model_validate_json(response.content).model_dump(mode="json")
        run_id = identity("model-run", request.request_id) if attempted else None
        if run_id:
            config = request.configuration["provider"]
            run = ModelRun(
                run_id=run_id,
                environment_id=request.environment_id,
                incident_id=request.incident_id,
                task_id=None,
                provider=config["provider"],
                model=config["model"],
                model_revision=config["revision"],
                prompt_version="evidence-brain/1.0.0",
                context_id=request.context_id,
                input_hash=request.input_hash,
                output_hash=hashlib.sha256(response.content.encode()).hexdigest()
                if response
                else canonical_hash(None),
                route_reason="explicit route; " + (error or "structured output; proposal only"),
                started_at=request.started_at,
                finished_at=at,
                input_tokens=response.input_tokens if response else 0,
                output_tokens=response.output_tokens if response else 0,
                cached_tokens=response.cached_tokens if response else 0,
                latency_ms=max(0, int((at - request.started_at).total_seconds() * 1000)),
                cost_usd=response.cost_usd if response else None,
                schema_valid=error is None,
                safety_status="PASS" if error is None else "DEGRADED",
            )
            db.add(ModelRunRow(**values_for(run, ModelRunRow)))
            budget = db.get(AIIncidentBudgetRow, request.incident_id)
            assert budget is not None
            if response and response.usage_known and error != "INVALID_TOKEN_ACCOUNTING":
                used = response.input_tokens + response.output_tokens
                budget.charged_tokens += used - request.reserved_tokens
                budget.input_tokens += response.input_tokens
                budget.output_tokens += response.output_tokens
            db.flush()
            emit(
                db,
                request.environment_id,
                "ModelRun",
                run_id,
                "ModelRunCompleted" if error is None else "ModelRunFailed",
                error or "structured proposal; no execution authority",
                principal.principal_id,
            )
        request.status = "FALLBACK" if error else "COMPLETED"
        request.worker_id = None
        receipt = ModelReceiptRow(
            request_id=request.request_id,
            model_run_id=run_id,
            status=request.status,
            error_code=error,
            output={"validated": output, "original_text": response.content} if output and response else None,
            usage_known=response.usage_known if response else False,
            completed_at=at,
            provider_ms=response.latency_ms if response else 0,
            overhead_ms=max(0, (perf_counter() - timer) * 1000 - (response.latency_ms if response else 0)),
            schema_validation_ms=validation_ms,
        )
        db.add(receipt)
        if error:
            emit(
                db,
                request.environment_id,
                "ModelRequest",
                request.request_id,
                "ModelFallbackTriggered",
                error + "; deterministic path remains available",
                principal.principal_id,
            )
        return self._public(request, receipt)

    @staticmethod
    def _public(request: ModelRequestRow, receipt: ModelReceiptRow) -> dict[str, Any]:
        return {
            "request_id": request.request_id,
            "context_id": request.context_id,
            "model_run_id": receipt.model_run_id,
            "status": receipt.status,
            "error_code": receipt.error_code,
            "output": (receipt.output.get("validated", receipt.output) if receipt.output else None),
            "usage_known": receipt.usage_known,
            "fallback": receipt.status == "FALLBACK",
        }
