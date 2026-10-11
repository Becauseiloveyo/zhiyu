"""Explicit acceptance-only process crashes around durable model boundaries."""

import os
import sys
import threading
import time

from zhiyu.ai.analysis import AISituationAnalyzer
from zhiyu.ai.gateway import ModelGateway
from zhiyu.ai.provider import OpenAICompatibleProvider
from zhiyu.core.config import settings
from zhiyu.db.session import get_engine


class InterruptProvider(OpenAICompatibleProvider):
    def complete(self, config, request):
        # Send a real HTTP request, then kill this worker during provider generation.
        def invoke():
            try:
                super(InterruptProvider, self).complete(config, request)
            except Exception:
                pass

        threading.Thread(target=invoke, daemon=True).start()
        time.sleep(1)
        os._exit(31)


if __name__ == "__main__":
    mode, env, context = sys.argv[1:4]
    if not env.startswith("m3-m5-"):
        raise ValueError("isolated acceptance environment required")
    from pathlib import Path

    key_file = os.environ.get("ZHIYU_MODEL_KEY_FILE")
    if key_file:
        os.environ["ZHIYU_LOCAL_MODEL_KEY"] = Path(key_file).read_text().strip()
    policy = settings.ai_policies[env]
    p = next(p for p in settings.service_tokens.values() if p.principal_id == "compose-smoke")
    gateway = ModelGateway(
        get_engine(),
        policy,
        settings.ai_providers[policy.provider_id],
        adapter=InterruptProvider() if mode == "interrupt" else None,
    )
    AISituationAnalyzer(get_engine(), gateway).analyze(env, context, p)
    if mode == "after-commit":
        os._exit(32)
    raise ValueError("unexpected acceptance mode")
