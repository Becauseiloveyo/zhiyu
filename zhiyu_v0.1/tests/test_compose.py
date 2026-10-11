import os
import re
import subprocess
import sys

import pytest
import yaml
from conftest import ROOT


def test_compose_static_wiring():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert services["migrate"]["command"] == ["python", "-m", "alembic", "upgrade", "head"]
    assert services["bootstrap"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert services["api"]["depends_on"]["postgres"]["condition"] == "service_started"
    assert services["api"]["ports"][0].startswith("127.0.0.1:")
    assert "ports" not in services["postgres"]
    assert services["api"]["build"]["target"] == "runtime"
    assert services["tests"]["build"]["target"] == "tests"


def test_model_prompt_cache_budget_fits_container():
    """Prevent reverting to llama.cpp's 8 GiB default inside a smaller container.

    This only checks the cache allocation budget. Actual total memory is measured
    by the recovery/soak harness, including weights, working buffers and KV cache.
    """
    service = yaml.safe_load((ROOT / "docker-compose.ai.yml").read_text(encoding="utf-8"))["services"][
        "local-model"
    ]
    memory = re.fullmatch(r"([0-9]+)([kmg])", str(service["mem_limit"]).lower())
    assert memory is not None, "explicit container RAM limit required"
    memory_bytes = int(memory[1]) * 1024 ** ({"k": 1, "m": 2, "g": 3}[memory[2]])
    command = service["command"]
    assert command.count("--cache-ram") == 1, "do not rely on an oversized upstream default cache"
    cache_mib = int(command[command.index("--cache-ram") + 1])
    assert 0 <= cache_mib * 1024 * 1024 < memory_bytes, "cache must leave RAM for the model and buffers"


@pytest.mark.compose
def test_live_compose_smoke():
    if os.environ.get("ZHIYU_RUN_COMPOSE") != "1":
        pytest.skip("set ZHIYU_RUN_COMPOSE=1 on a Docker host; static wiring is not a smoke test")
    result = subprocess.run([sys.executable, str(ROOT / "tools/compose_smoke.py")], cwd=ROOT, timeout=3600)
    assert result.returncode == 0
