"""Configured worker identity; durable PostgreSQL leases survive process restart."""

import argparse
import json
import time
from typing import Any

from sqlalchemy.engine import Engine

from zhiyu.core.config import settings
from zhiyu.core.identity import ServicePrincipal
from zhiyu.db.session import get_engine
from zhiyu.verification.runtime import VerificationService


class VerificationWorker:
    def __init__(self, engine: Engine) -> None:
        self.service = VerificationService(engine)

    def tick(
        self, environment: str, principal: ServicePrincipal, spec_id: str | None = None
    ) -> dict[str, Any]:
        if "verification:write" in principal.permissions:
            from zhiyu.verification.lab_reviews import schedule_reviews

            schedule_reviews(self.service.engine, environment, principal)
        lease = self.service.claim(environment, principal, spec_id=spec_id)
        if lease is None:
            return {"status": "IDLE"}
        return {
            "status": "PROCESSED",
            "lease": lease,
            "result": self.service.run_claim(environment, lease, principal),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent bounded verification worker")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("--spec")
    parser.add_argument("--poll", action="store_true")
    args = parser.parse_args()
    matches = [
        p
        for p in settings.service_tokens.values()
        if p.principal_id == args.principal and args.environment in p.environment_ids
    ]
    if len(matches) != 1:
        print(json.dumps({"status": "ERROR", "error_code": "configured_worker_identity_required"}))
        return 1
    worker = VerificationWorker(get_engine())
    try:
        while True:
            print(json.dumps(worker.tick(args.environment, matches[0], args.spec)), flush=True)
            if not args.poll:
                return 0
            time.sleep(1)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
