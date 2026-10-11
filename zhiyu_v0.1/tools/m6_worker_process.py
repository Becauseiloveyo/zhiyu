"""Child process fault points. Only imported by the isolated acceptance harness."""

import json
import os
import sys
import time

from sqlalchemy import event
from sqlalchemy.orm import Session

from zhiyu.ai.gateway import ModelGateway
from zhiyu.ai.provider import OpenAICompatibleProvider
from zhiyu.core.config import settings
from zhiyu.core.errors import LeaseLostError
from zhiyu.db.session import get_engine
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.executors import ExecutorRegistry
from zhiyu.response.gateway import ActionGateway
from zhiyu.response.scheduler import TaskScheduler
from zhiyu.response.worker import ResponseWorker
from zhiyu.services.event_intelligence import EventIntelligenceEngine
from zhiyu.verification.runtime import VerificationCheckExecutor, VerificationService


def emit(kind, value):
    print(json.dumps({"kind": kind, "value": value}, default=str), flush=True)


def crash(boundary):
    emit("crash", {"boundary": boundary, "pid": os.getpid()})
    os._exit(71)


def main():
    task = json.loads(sys.argv[1])
    env, kind, stage = task["environment"], task["worker"], task["stage"]
    if not env.startswith("m3-m6-worker-") or os.environ.get("ZHIYU_M6_FAULT_LAB") != "1":
        raise RuntimeError("isolated M6 worker acceptance required")
    engine = get_engine()
    principal = next(p for p in settings.service_tokens.values() if p.principal_id == "compose-smoke")
    principal.require("response:execute", env)
    if kind == "event":

        def after_sql(connection, cursor, statement, parameters, context, many):
            sql = statement.lower()
            if stage == "lease" and "from environments" in sql and "for update" in sql:
                crash("environment_row_lock_acquired_no_worker_lease_design")
            if stage == "before" and sql.startswith("insert into event_groups"):
                crash("first_group_insert_before_transaction_commit")
            if stage == "after" and sql.startswith("insert into intelligence_runs"):
                crash("all_processing_done_before_transaction_commit")

        event.listen(engine, "after_cursor_execute", after_sql)
        with Session(engine) as db:
            result = EventIntelligenceEngine(db).process(env, principal=principal)
        emit("result", result)
        if stage == "commit":
            crash("intelligence_transaction_committed")
        return
    if kind in {"task", "action"}:
        original_claim = TaskScheduler.claim
        original_authorize = AuthorizationService.authorize_task
        original_complete = ActionGateway.complete

        def claim(self, *args, **kwargs):
            lease = original_claim(self, *args, **kwargs)
            emit("lease", lease)
            if stage == "lease":
                crash("durable_task_lease")
            if kind == "task" and stage == "stale":
                time.sleep(21)
            return lease

        def authorize(self, *args, **kwargs):
            decision = original_authorize(self, *args, **kwargs)
            emit("authorization", decision.model_dump(mode="json"))
            if kind == "task" and stage == "before":
                crash("authorization_committed_before_dispatch")
            return decision

        def complete(self, *args, **kwargs):
            emit("executed", {"attempt_id": args[1], "generation": args[2], "output": args[4].output})
            if stage == "after":
                crash("executor_returned_before_result_commit")
            if kind == "action" and stage == "stale":
                time.sleep(21)
            value = original_complete(self, *args, **kwargs)
            emit("receipt", value)
            if stage == "commit":
                crash("action_result_committed")
            return value

        class Registry(ExecutorRegistry):
            def resolve(self, action):
                original = super().resolve(action)

                class Wrapped:
                    version = original.version

                    def execute(self, request):
                        emit("executor_entry", {"action_id": request.action_id})
                        if kind == "action" and stage == "before":
                            crash("durable_dispatch_before_executor")
                        return original.execute(request)

                return Wrapped()

        TaskScheduler.claim, AuthorizationService.authorize_task = claim, authorize
        ActionGateway.complete = complete
        import zhiyu.response.gateway as gateway_module

        gateway_module.ExecutorRegistry = Registry
        try:
            emit("result", ResponseWorker(engine).tick(env, principal))
        except LeaseLostError:
            emit("fenced", {"stage": stage})
            if stage != "stale":
                raise
        return
    if kind == "verification":
        service = VerificationService(engine)
        lease = service.claim(env, principal, spec_id=task["spec_id"])
        emit("lease", lease)
        if stage == "lease":
            crash("durable_verification_lease")
        original = VerificationCheckExecutor.execute

        def execute(self, *args, **kwargs):
            if stage == "before":
                crash("before_independent_check")
            value = original(self, *args, **kwargs)
            emit("observed", value)
            if stage == "after":
                crash("observation_collected_before_evidence_commit")
            if stage == "stale":
                time.sleep(11)
            return value

        VerificationCheckExecutor.execute = execute
        try:
            result = service.run_claim(env, lease, principal)
            emit("result", result)
        except LeaseLostError:
            emit("fenced", {"stage": stage})
            if stage != "stale":
                raise
        if stage == "commit":
            crash("observation_evidence_audit_committed")
        return
    if kind == "ai":
        policy = settings.ai_policies[env]
        provider = settings.ai_providers[policy.provider_id]
        original = OpenAICompatibleProvider.complete

        def complete(self, config, request):
            emit("reservation", {"stage": stage})
            if stage in {"lease", "before"}:
                crash("durable_model_reservation_before_http")
            response = original(self, config, request)
            emit("provider_returned", {"usage_known": response.usage_known})
            if stage == "after":
                crash("real_http_response_before_model_result_commit")
            if stage == "stale":
                time.sleep(18)
            return response

        OpenAICompatibleProvider.complete = complete
        result = ModelGateway(engine, policy, provider).analyze(env, task["context_id"], principal)
        emit("result", result)
        if stage == "commit":
            crash("model_result_committed")
        return
    raise ValueError("unknown worker")


if __name__ == "__main__":
    main()
