"""A separate worker commits intent, then calls an installed fixed adapter outside transactions."""

import logging
import threading
from collections.abc import Callable
from typing import Protocol
from uuid import uuid4

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from zhiyu.db.demo_control import DemoRunRow
from zhiyu.product import demo_control as controller
from zhiyu.product.demo_contracts import StepOutput, WorkItem

LOG = logging.getLogger(__name__)


class FixedAdapter(Protocol):
    def perform(self, work: WorkItem, current: Callable[[], bool]) -> StepOutput: ...


def once(engine: Engine, profile_id: str, adapter: FixedAdapter) -> str | None:
    owner = "demo-worker-" + uuid4().hex
    with Session(engine) as db, db.begin():
        controller.recover_expired(db, profile_id)
        work = controller.claim(db, profile_id, owner)
    if work is None:
        return None
    stopped, lost = threading.Event(), threading.Event()

    def heartbeat() -> None:
        while not stopped.wait(10):
            try:
                with Session(engine) as db, db.begin():
                    if not controller.renew(db, work):
                        lost.set()
                        return
            except Exception:
                lost.set()
                return

    thread = threading.Thread(target=heartbeat, name=owner, daemon=True)
    thread.start()

    def current() -> bool:
        if lost.is_set():
            return False
        try:
            with Session(engine) as db, db.begin():
                if not controller.renew(db, work):
                    lost.set()
                    return False
                row = db.get(DemoRunRow, work.run_id)
                if work.operation == "CLEANUP":
                    return True
                if row is None or row.cancel_requested:
                    return False
                from zhiyu.core.config import settings
                from zhiyu.product.access import authorize, product_settings
                from zhiyu.product.contracts import Query

                profile = product_settings.demo_profiles.get(work.profile_id)
                actors = [a.principal for a in product_settings.browser_users.values()]
                actors += list(settings.service_tokens.values())
                actor = next(
                    (actor for actor in actors if actor.principal_id == row.actor_id),
                    None,
                )
                if (
                    not profile
                    or not profile.enabled
                    or not actor
                    or (
                        profile.environment_id != work.environment_id
                        or profile.scope_id != work.scope_id
                        or row.template_sha256 != controller.template_hash(work.scenario_id)
                    )
                ):
                    return False
                actor.require("demo:run", work.environment_id)
                authorize(db, actor, Query(environment_id=work.environment_id, scope_id=work.scope_id))
                return work.scenario_id in profile.scenarios
        except Exception:
            return False

    failed = False
    try:
        output = adapter.perform(work, current)
        # Adapters return metadata references only; never raw subprocess output or arbitrary JSON.
        output = StepOutput.model_validate(output)
    except Exception:
        failed, output = True, StepOutput()
        # Do not leak exception messages, URLs or commands that may contain private deployment values.
        LOG.error("fixed_demo_step_failed run=%s operation=%s", work.run_id, work.operation)
    finally:
        stopped.set()
        thread.join(timeout=2)
    if lost.is_set():
        return work.run_id  # Recovery marks UNKNOWN; no stale acknowledgment and no re-execution.
    with Session(engine) as db, db.begin():
        controller.finish(db, work, output, failed=failed)
    return work.run_id
