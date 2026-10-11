"""Owned, loopback-only PostgreSQL test instance; credentials never enter logs/artifacts."""

import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / ".work" / "m9-validation"
ARTIFACTS = ROOT / "artifacts" / "v0.9"


def command(args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, check=True,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), **kwargs)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    config_path = WORK / "local-secrets.json"
    if not config_path.exists():
        config_path.write_text(json.dumps({"password": secrets.token_urlsafe(32),
                                         "container": "zhiyu-m9-tests-" + secrets.token_hex(5)}))
    config = json.loads(config_path.read_text())
    name = config["container"]
    found = command(["docker", "ps", "-a", "--filter", f"name=^{name}$", "--format", "{{.Names}}"])
    if not found.stdout.strip():
        # Password goes in child environment, not argv or exported artifacts.
        env = {**os.environ, "POSTGRES_PASSWORD": config["password"]}
        command(["docker", "run", "-d", "--name", name, "--label", "zhiyu.owner=m9-validation",
                 "-e", "POSTGRES_PASSWORD", "-e", "POSTGRES_USER=zhiyu", "-e", "POSTGRES_DB=zhiyu",
                 "-p", "127.0.0.1::5432", "postgres:17.11@sha256:67f41722b7a8cbdb868a44a4995c846eddfdc2973bccb291ce937dce88ad5675"], env=env, timeout=300)
    else:
        command(["docker", "start", name])
    port = command(["docker", "port", name, "5432/tcp"]).stdout.strip().rsplit(":", 1)[1]
    for _ in range(30):
        ready = subprocess.run(["docker", "exec", name, "pg_isready", "-U", "zhiyu"],
                               capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if ready.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError("owned PostgreSQL did not become ready")
    env = {**os.environ, "ZHIYU_REQUIRE_POSTGRES": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
           "ZHIYU_TEST_DATABASE_URL": f"postgresql+psycopg://zhiyu:{config['password']}@127.0.0.1:{port}/zhiyu"}
    inventory = ARTIFACTS / "original-test-inventory.json"
    if not inventory.exists():
        inventory.write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\', '/'):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "tests").rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and 'test_product_' not in p.name}, indent=2))
    args = sys.argv[1:] or ["-q"]
    if args == ["--ensure-only"]:
        print(json.dumps({"status": "DATABASE_READY", "container": name, "tests_executed": False}))
        return
    if "--with-compose" in args:
        args.remove("--with-compose")
        model = ROOT.parent / ".work/m5-model/qwen2.5-1.5b-instruct-q4_k_m.gguf"
        key = WORK / "model-key.private"
        if not key.exists():
            key.write_text(secrets.token_urlsafe(40), encoding="utf-8")
        env.update(ZHIYU_RUN_COMPOSE="1", ZHIYU_MODEL_PATH=str(model), ZHIYU_MODEL_KEY_FILE=str(key))
    result = subprocess.run([sys.executable, "-m", "pytest", *args], cwd=ROOT, env=env,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = (result.stdout + result.stderr).replace(config["password"], "<redacted>")
    label = time.strftime("pytest-%Y%m%dT%H%M%SZ", time.gmtime())
    (ARTIFACTS / (label + ".txt")).write_text(output, encoding="utf-8")
    (ARTIFACTS / "latest-pytest.txt").write_text(output, encoding="utf-8")
    print(output[-16000:])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
