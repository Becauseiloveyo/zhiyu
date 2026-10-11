"""Small PostgreSQL-backed worker. Process restart preserves all scheduling authority."""

import argparse
import json
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.core.config import settings
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.session import get_engine
from zhiyu.response.authorization import AuthorizationService
from zhiyu.response.gateway import ActionGateway
from zhiyu.response.scheduler import TaskScheduler


class ResponseWorker:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def tick(self, environment_id: str, principal: ServicePrincipal) -> dict[str, Any]:
        with Session(self.engine) as db:
            lease = TaskScheduler(db).claim(environment_id, principal)
        if lease is None:
            if "response:reconcile" in principal.permissions:
                from zhiyu.db.models import ActionAttemptRow
                from zhiyu.db.response_authority import ActionControlRow

                with Session(self.engine) as db:
                    pending = db.scalar(
                        select(ActionAttemptRow.attempt_id)
                        .join(ActionControlRow, ActionControlRow.action_id == ActionAttemptRow.action_id)
                        .where(
                            ActionControlRow.environment_id == environment_id,
                            ActionControlRow.status == "EXECUTION_UNKNOWN",
                            ActionAttemptRow.reconciliation_state == "PENDING",
                        )
                        .order_by(ActionAttemptRow.started_at)
                        .limit(1)
                    )
                if pending:
                    return {
                        "status": "RECOVERY",
                        "result": ActionGateway(self.engine).reconcile(environment_id, pending, principal),
                    }
            return {"status": "IDLE"}
        with Session(self.engine) as db:
            decision = AuthorizationService(db).authorize_task(
                environment_id, lease["task_id"], generation=lease["generation"], principal=principal
            )
        result = ActionGateway(self.engine).dispatch(
            environment_id, lease["task_id"], lease["generation"], decision.authorization_id, principal
        )
        return {
            "status": "PROCESSED",
            "lease": lease,
            "authorization_id": decision.authorization_id,
            "policy_outcome": decision.outcome,
            "result": result,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the configured local response worker; no arbitrary identities or commands"
    )
    parser.add_argument("--environment", required=True)
    parser.add_argument(
        "--principal",
        required=True,
        help="existing principal_id in local protected ZHIYU_SERVICE_TOKENS configuration",
    )
    parser.add_argument("--poll", action="store_true", help="continue polling; otherwise execute one tick")
    args = parser.parse_args()
    matches = [
        p
        for p in settings.service_tokens.values()
        if p.principal_id == args.principal and args.environment in p.environment_ids
    ]
    if len(matches) != 1:
        print(json.dumps({"status": "ERROR", "error_code": "configured_worker_identity_required"}))
        return 1
    worker = ResponseWorker(get_engine())
    try:
        while True:
            print(json.dumps(worker.tick(args.environment, matches[0]), ensure_ascii=False), flush=True)
            if not args.poll:
                return 0
            time.sleep(1)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
