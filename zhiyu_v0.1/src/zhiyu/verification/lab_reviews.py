"""Durable initial and post-TTL observations, scheduled from immutable execution receipts."""

import math
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import ActionRow, EnvironmentRow
from zhiyu.db.response_execution import ActionDispatchRow, ActionResultRow
from zhiyu.db.verification_runtime import VerificationRuntimeRow
from zhiyu.domain.contracts import ActionRequest
from zhiyu.response.lab_protocol import CAPABILITY
from zhiyu.verification.policy import VerificationPolicy
from zhiyu.verification.runtime import VerificationService, containment_spec


def schedule_reviews(engine: Engine, env: str, principal: ServicePrincipal) -> list[str]:
    principal.require("verification:write", env)
    pending = []
    with Session(engine) as db:
        environment = db.get(EnvironmentRow, env)
        if not environment:
            return []
        sensors = environment.required_sensor_ids
        rows = db.execute(
            select(ActionRow, ActionResultRow)
            .join(ActionDispatchRow, ActionDispatchRow.action_id == ActionRow.action_id)
            .join(ActionResultRow, ActionResultRow.attempt_id == ActionDispatchRow.attempt_id)
            .where(
                ActionRow.environment_id == env,
                ActionRow.capability_id == CAPABILITY,
                ActionResultRow.execution_outcome == "EXECUTION_SUCCESS",
            )
            .order_by(ActionResultRow.completed_at)
        )
        for action_row, result in rows:
            action = contract_from(action_row, ActionRequest)
            if action.parameters.get("operation", "contain") != "contain":
                continue
            target_receipt = result.output.get("observed", {}).get("receipt") or result.output
            expires = target_receipt.get("after", {}).get("expires_at")
            if not expires:
                continue
            for phase in ("active", "ttl-expired"):
                spec = containment_spec(action, sensors, "lab-" + phase)
                if db.get(VerificationRuntimeRow, spec.verification_spec_id):
                    continue
                pending.append((result.attempt_id, spec, expires, phase))
            if len(pending) >= 20:
                break
    service, ids = VerificationService(engine), []
    for result_id, spec, expires, phase in pending:
        now = datetime.now(UTC)
        delay = (
            max(1, min(65, math.ceil((datetime.fromisoformat(expires) - now).total_seconds()) + 1))
            if phase == "ttl-expired"
            else 0
        )
        policy = VerificationPolicy(minimum_window_seconds=1, start_after_seconds=delay)
        ids.append(service.create(env, result_id, spec, principal, policy, now=now))
    return ids
