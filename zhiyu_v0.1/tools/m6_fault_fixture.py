"""SYNTHETIC fixtures and database readback for isolated fault experiments."""

import json
import sys

from ai_fixture import snapshot, spec
from response_fixture import prepare, refresh_health

from zhiyu.core.config import settings
from zhiyu.db.session import get_engine


def main():
    verb, environment = sys.argv[1:3]
    if not environment.startswith("m3-m6-"):
        raise ValueError("M6 fault namespace required")
    principal = next(p for p in settings.service_tokens.values() if p.principal_id == "compose-smoke")
    principal.require("response:admin", environment)
    engine = get_engine()
    if verb in {"seed", "empty"}:
        result = prepare(
            engine,
            environment,
            principal,
            target=sys.argv[3],
            source=sys.argv[4],
            port=8081,
            seed=verb == "seed",
        )
    elif verb == "snapshot":
        result = snapshot(engine, environment)
    elif verb == "spec":
        result = spec(engine, environment)
    elif verb == "refresh":
        refresh_health(engine, environment, principal)
        result = {"data_origin": "SYNTHETIC"}
    else:
        raise ValueError("unknown fixture verb")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
