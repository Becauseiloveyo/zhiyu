"""Auditable single-host reference installation and protected logical backups.

The operator owns this CLI. It exposes no new product endpoint or arbitrary
execution input. Docker permissions stay in the separately run host Worker.
"""

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
import venv
import zipfile
from datetime import UTC, datetime
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PG_IMAGE = "postgres:17.11@sha256:67f41722b7a8cbdb868a44a4995c846eddfdc2973bccb291ce937dce88ad5675"
MODEL_SHA = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
HEAD = "0016_lab_remediation"
PUBLIC_OPERATIONS = {
    "install",
    "start",
    "stop",
    "status",
    "worker",
    "run",
    "cleanup",
    "snapshot",
    "backup",
    "restore",
    "upgrade",
    "serve",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def protected(directory):
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        user = os.environ["USERNAME"]
        result = subprocess.run(
            ["icacls", str(directory), "/inheritance:r", "/grant:r", user + ":(OI)(CI)F", "SYSTEM:(OI)(CI)F"],
            capture_output=True,
        )
        if result.returncode:
            raise RuntimeError("private_directory_acl_failed")
    else:
        directory.chmod(0o700)


def diagnostic_bytes(deployment, data):
    """Redact diagnostics without altering command results used by the operator."""
    values = []
    for directory in (deployment, deployment / "legacy-source"):
        try:
            cfg = read(directory / "deployment.private.json")
            values.extend(str(cfg[k]) for k in ("password", "access_key") if cfg.get(k))
        except (OSError, ValueError):
            pass
        for kind in ("model", "lab"):
            try:
                values.append((directory / (kind + "-key.private")).read_text(encoding="utf-8").strip())
            except OSError:
                pass
    for value in values:
        if value:
            data = data.replace(value.encode(), b"<redacted>")
    data = re.sub(rb"(postgres(?:ql)?(?:\+[a-z]+)?://[^\s:/@\"']+:)[^\s@\"']+(@)", rb"\1<redacted>\2", data)
    return re.sub(rb"(POSTGRES_PASSWORD=)[^\s\"']+", rb"\1<redacted>", data)


def log_command(deployment, args, stdout, stderr, log):
    if "pg_dump" in args:
        stdout = ("[binary pg_dump stdout omitted; bytes=" + str(len(stdout)) + "; sha256=" + sha(stdout) + "]\n").encode()
    with (deployment / log).open("ab") as stream:
        stream.write(diagnostic_bytes(deployment, stdout + stderr))


def command(args, deployment, *, env=None, timeout=600, input_bytes=None, log="operations.log"):
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            input=input_bytes,
            capture_output=True,
            env=env,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        log_command(deployment, args, exc.stdout or b"", exc.stderr or b"", log)
        raise RuntimeError("reference_command_timed_out:" + Path(str(args[0])).name) from None
    # Diagnostics remain private; credential-bearing results are redacted only in logs.
    log_command(deployment, args, result.stdout, result.stderr, log)
    if result.returncode:
        raise RuntimeError("reference_command_failed:" + Path(str(args[0])).name)
    return result.stdout


def python(deployment):
    return deployment / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def configuration(deployment):
    cfg = read(deployment / "deployment.private.json")
    if not re.fullmatch(r"zhiyu-v1-[a-f0-9]{12}", cfg["project"]):
        raise RuntimeError("invalid_reference_project")
    if cfg["owner"] != cfg["project"] or cfg["database"] != "zhiyu":
        raise RuntimeError("invalid_reference_ownership")
    return cfg


def docker(deployment, *args, **kwargs):
    return command(["docker", *args], deployment, **kwargs)


def compose(deployment, *args, **kwargs):
    cfg = configuration(deployment)
    child_env = {**os.environ, "POSTGRES_PASSWORD": cfg["password"]}
    return docker(
        deployment,
        "compose",
        "-p",
        cfg["project"],
        "-f",
        str(deployment / "compose.private.json"),
        *args,
        env=child_env,
        **kwargs,
    )


def owned_database(deployment):
    cfg = configuration(deployment)
    identifier = compose(deployment, "ps", "-q", "postgres").decode().strip()
    if not identifier:
        raise RuntimeError("reference_database_not_running")
    detail = json.loads(docker(deployment, "inspect", identifier))[0]
    if detail["Config"]["Labels"].get("zhiyu.owner") != cfg["owner"]:
        raise RuntimeError("foreign_reference_database")
    return identifier, detail


def refresh(deployment):
    cfg = configuration(deployment)
    owned_database(deployment)
    identifier = compose(deployment, "ps", "-q", "ingress").decode().strip()
    if not identifier:
        raise RuntimeError("reference_ingress_not_running")
    detail = json.loads(docker(deployment, "inspect", identifier))[0]
    if detail["Config"]["Labels"].get("zhiyu.owner") != cfg["owner"]:
        raise RuntimeError("foreign_reference_ingress")
    port = loopback_port(detail, "5432/tcp")
    loopback_port(detail, "8000/tcp")
    cfg["database_url"] = (
        "postgresql+psycopg://zhiyu:"
        + cfg["password"]
        + "@127.0.0.1:"
        + port
        + "/zhiyu"
    )
    save(deployment / "deployment.private.json", cfg)
    container = {**cfg, "database_url": cfg["container_database_url"]}
    save(deployment / "api.private.json", container)
    return cfg


def loopback_port(detail, container_port):
    bindings = detail["NetworkSettings"]["Ports"].get(container_port) or []
    if len(bindings) != 1 or bindings[0].get("HostIp") != "127.0.0.1":
        raise RuntimeError("reference_port_not_loopback_published")
    port = bindings[0].get("HostPort", "")
    if not port.isdecimal() or not 1024 <= int(port) <= 65535:
        raise RuntimeError("reference_port_not_loopback_published")
    return port


def setup(deployment, *, container=False):
    import m9_demo
    import m9_lab_adapter

    m9_demo.CONFIG = deployment / ("api.private.json" if container else "deployment.private.json")
    cfg = read(m9_demo.CONFIG)
    m9_lab_adapter.PRIVATE = deployment / "demo-private"
    m9_lab_adapter.EVIDENCE = ROOT / "artifacts/v1.0/lab"
    m9_lab_adapter.CONTROL_NETWORK = cfg["control_network"]
    engine, principal, cfg = m9_demo.load()
    from zhiyu.product.access import product_settings

    product_settings.allowed_origins = {cfg["origin"]}
    product_settings.recording_root = "/recordings" if container else str(deployment / "recordings")
    return engine, principal, cfg


def bootstrap(deployment):
    from alembic import command as migration
    from alembic.config import Config
    from m6_sensor_ingest import prepare
    from sqlalchemy.orm import Session

    from zhiyu.db.models import EnvironmentRow
    from zhiyu.product.demo_store import initialize

    engine, _, cfg = setup(deployment)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        migration.upgrade(config, "head")
    initialize(engine)
    with Session(engine) as session:
        exists = session.get(EnvironmentRow, cfg["parent_environment"]) is not None
    if not exists:
        prepare(engine, cfg["parent_environment"])


def install(deployment, model_path, port, restore_path=None):
    if deployment.exists() and any(deployment.iterdir()):
        raise RuntimeError("clean_install_requires_new_empty_directory")
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("reference_requires_python_3_12")
    if not 1024 <= port <= 65535:
        raise RuntimeError("invalid_loopback_port")
    model_path = model_path.resolve(strict=True)
    with model_path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != MODEL_SHA:
            raise RuntimeError("model_weight_digest_mismatch")
    protected(deployment)
    start = time.monotonic()
    command(["docker", "version"], deployment)
    command(["docker", "compose", "version"], deployment)
    command(["node", "--version"], deployment)
    project = "zhiyu-v1-" + secrets.token_hex(6)
    cfg = {
        **read(ROOT / "config/reference-profile.json"),
        "project": project,
        "owner": project,
        "password": secrets.token_urlsafe(40),
        "access_key": secrets.token_urlsafe(40),
        "container_database_url": "pending",
        "model_path": str(model_path),
        "origin": "http://127.0.0.1:" + str(port),
        "control_network": project + "_control",
        "installed_version": "1.0.0",
        "install_state": "PREPARING",
    }
    for kind in ("model", "lab"):
        path = deployment / (kind + "-key.private")
        path.write_text(secrets.token_urlsafe(40), encoding="utf-8")
        cfg[kind + "_key_path"] = str(path)
    cfg["container_database_url"] = (
        "postgresql+psycopg://zhiyu:" + cfg["password"] + "@canonical-postgres:5432/zhiyu"
    )
    save(deployment / "deployment.private.json", cfg)
    print("Creating fresh Python environment and installing hashed dependencies", flush=True)
    venv.EnvBuilder(with_pip=True).create(deployment / "venv")
    wheels = deployment / "reference-wheels.lock"
    command([str(python(deployment)), str(ROOT / "tools/release_wheels.py"), "--output", str(wheels)], deployment)
    command(
        [
            str(python(deployment)),
            "-m",
            "pip",
            "install",
            "--timeout",
            "120",
            "--retries",
            "5",
            "--no-cache-dir",
            "--no-index",
            "--only-binary",
            ":all:",
            "--require-hashes",
            "-r",
            str(wheels),
        ],
        deployment,
        timeout=7200,
    )
    command([str(python(deployment)), "-m", "pip", "check"], deployment)
    command(
        [
            str(python(deployment)),
            "-m",
            "pip",
            "install",
            "--timeout",
            "120",
            "--retries",
            "5",
            "--no-cache-dir",
            "--no-deps",
            "--no-build-isolation",
            str(ROOT),
        ],
        deployment,
    )
    print("Installing/building frontend with a new npm cache", flush=True)
    frontend = deployment / "frontend-build"
    shutil.copytree(ROOT / "frontend", frontend, ignore=shutil.ignore_patterns("node_modules", "dist"))
    npm = shutil.which("npm.cmd") if os.name == "nt" else shutil.which("npm")
    if not npm:
        raise RuntimeError("npm_not_available")
    command(
        [npm, "--prefix", str(frontend), "ci", "--cache", str(deployment / "npm-cache")],
        deployment,
        timeout=7200,
    )
    for operation in ("lint", "typecheck", "test", "build"):
        command([npm, "--prefix", str(frontend), "run", operation], deployment)
    expected = {
        p.relative_to(ROOT / "frontend/dist").as_posix(): sha(p.read_bytes())
        for p in (ROOT / "frontend/dist").rglob("*")
        if p.is_file()
    }
    actual = {
        p.relative_to(frontend / "dist").as_posix(): sha(p.read_bytes())
        for p in (frontend / "dist").rglob("*")
        if p.is_file()
    }
    if actual != expected:
        raise RuntimeError("clean_frontend_build_differs_from_candidate")
    print("Building backend and Sensor images without layer/cache reuse", flush=True)
    image = project + ":1.0.0"
    docker(deployment, "build", "--no-cache", "-f", "Dockerfile.release", "-t", image, ".", timeout=7200)
    cfg["image_id"] = json.loads(docker(deployment, "image", "inspect", image))[0]["Id"]
    sensors = {}
    for service, dockerfile in (("sensor", "Dockerfile"), ("wazuh", "Dockerfile.wazuh-manager")):
        tag = project + "-" + service + ":1.0.0"
        docker(
            deployment,
            "build",
            "--no-cache",
            "-f",
            str(ROOT / "lab/real-sensors" / dockerfile),
            "-t",
            tag,
            str(ROOT / "lab/real-sensors"),
            timeout=7200,
        )
        sensors[service] = json.loads(docker(deployment, "image", "inspect", tag))[0]["Id"]
    cfg["sensor_images"] = sensors
    save(deployment / "deployment.private.json", cfg)
    (deployment / "recordings").mkdir()
    labels = {"zhiyu.owner": project}
    spec = {
        "services": {
            "postgres": {
                "image": PG_IMAGE,
                "labels": labels,
                "environment": {"POSTGRES_DB": "zhiyu", "POSTGRES_USER": "zhiyu", "POSTGRES_PASSWORD": None},
                "volumes": ["database:/var/lib/postgresql/data"],
                "networks": {"control": {"aliases": ["canonical-postgres"]}},
                "healthcheck": {
                    "test": ["CMD", "pg_isready", "-U", "zhiyu"],
                    "interval": "3s",
                    "timeout": "3s",
                    "retries": 30,
                },
            },
            "api": {
                "image": cfg["image_id"],
                "labels": labels,
                "volumes": [
                    str(deployment / "api.private.json") + ":/run/reference/api.private.json:ro",
                    str(deployment / "recordings") + ":/recordings:ro",
                ],
                "networks": ["control"],
                "read_only": True,
                "tmpfs": ["/tmp"],
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges:true"],
                "depends_on": {"postgres": {"condition": "service_healthy"}},
            },
            "ingress": {
                "image": cfg["image_id"],
                "command": ["python", "tools/reference_ingress.py"],
                "labels": labels,
                "ports": ["127.0.0.1::5432", "127.0.0.1:" + str(port) + ":8000"],
                "networks": ["control", "ingress"],
                "read_only": True,
                "tmpfs": ["/tmp"],
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges:true"],
                "sysctls": {"net.ipv4.ip_forward": "0"},
                "mem_limit": "128m",
                "cpus": 1,
                "healthcheck": {
                    "test": [
                        "CMD", "python", "-c",
                        "import socket; [socket.create_connection(('127.0.0.1', p), 2).close() for p in (5432, 8000)]",
                    ],
                    "interval": "3s",
                    "timeout": "5s",
                    "retries": 30,
                },
            },
        },
        "networks": {
            "control": {"internal": True, "labels": labels},
            "ingress": {"labels": labels},
        },
        "volumes": {"database": {"labels": labels}},
    }
    save(deployment / "compose.private.json", spec)
    compose(deployment, "up", "-d", "--wait", "postgres", "ingress")
    refresh(deployment)
    if restore_path:
        command(
            [
                str(python(deployment)),
                str(__file__),
                "restore",
                "--deployment",
                str(deployment),
                "--backup",
                str(restore_path),
            ],
            deployment,
        )
    command(
        [
            str(python(deployment)),
            str(__file__),
            "upgrade",
            "--deployment",
            str(deployment),
            "--bootstrap-only",
        ],
        deployment,
    )
    cfg = configuration(deployment)
    cfg["install_state"] = "INSTALLED"
    save(deployment / "deployment.private.json", cfg)
    start_api(deployment)
    save(
        deployment / "install-result.json",
        {
            "status": "PASS",
            "version": "1.0.0",
            "project": project,
            "fresh_database_volume": True,
            "fresh_python_environment": True,
            "fresh_npm_cache": True,
            "no_cache_docker_build": True,
            "frontend_byte_reproduction": "PASS",
            "seconds": time.monotonic() - start,
            "images": {"backend": cfg["image_id"], **sensors},
            "url": cfg["origin"],
            "credentials": "PRIVATE_OPERATOR_FILE",
            "linux_host_clean_install": "NOT_RUN",
        },
    )
    print(json.dumps({"status": "INSTALLED", "project": project, "url": cfg["origin"]}), flush=True)


def start_api(deployment):
    cfg = refresh(deployment)
    compose(deployment, "up", "-d", "api")
    for _ in range(60):
        try:
            with urllib.request.urlopen(cfg["origin"] + "/ready", timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError("reference_api_not_ready")


def snapshot(deployment):
    from sqlalchemy import inspect, text
    from sqlalchemy.orm import Session

    from zhiyu.repositories.audit import AuditRepository

    engine, _, _ = setup(deployment)
    tables = {}
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn, conn.begin():
        conn.execute(text("SET TRANSACTION READ ONLY"))
        conn.execute(text("SET LOCAL TIME ZONE 'UTC'"))
        for schema in ("public", "zhiyu_product"):
            for name in inspect(conn).get_table_names(schema=schema):
                q = engine.dialect.identifier_preparer
                qualified = q.quote(schema) + "." + q.quote(name)
                rows = conn.scalars(
                    text("SELECT row_to_json(r)::text FROM " + qualified + " r ORDER BY row_to_json(r)::text")
                ).all()
                tables[schema + "." + name] = {"count": len(rows), "sha256": sha("\n".join(rows).encode())}
        head = conn.scalar(text("SELECT version_num FROM alembic_version"))
        invalid = conn.scalar(
            text("SELECT count(*) FROM pg_constraint WHERE contype='f' AND NOT convalidated")
        )
        envs = list(conn.scalars(text("SELECT environment_id FROM environments")))
    with Session(engine) as session:
        chains = {environment: AuditRepository(session).verify_chain(environment) for environment in envs}
    if invalid or not all(chains.values()) or head != HEAD:
        raise RuntimeError("snapshot_schema_or_audit_invalid")
    return {
        "tables": tables,
        "audit_chains": chains,
        "migration_head": head,
        "unvalidated_foreign_keys": invalid,
    }


def idle(deployment):
    from sqlalchemy import text

    engine, _, _ = setup(deployment)
    if (deployment / "worker.lock").exists():
        raise RuntimeError("stop_worker_before_backup_or_upgrade")
    with engine.connect() as conn:
        if conn.scalar(text("SELECT count(*) FROM zhiyu_product.demo_runs WHERE cleanup_status <> 'CLEAN'")):
            raise RuntimeError("cleanup_all_demo_runs_before_backup_or_upgrade")


@contextmanager
def operation_lock(deployment):
    path = deployment / "operator.lock"
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(str(os.getpid()))
    except FileExistsError:
        raise RuntimeError("reference_operator_operation_already_active") from None
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def backup_destination(deployment, output):
    if output is None:
        raise RuntimeError("backup_destination_required")
    root = (deployment / "backups").resolve()
    output = output.resolve()
    if not root.is_relative_to(deployment.resolve()) or not output.is_relative_to(root):
        raise RuntimeError("backup_destination_outside_private_backups")
    if output.suffix.lower() != ".zip" or output.exists():
        raise RuntimeError("backup_destination_invalid_or_exists")
    protected(root)
    protected(output.parent)
    return output


def backup(deployment, output):
    output = backup_destination(deployment, output)
    from release_recovery import complete_backup

    return complete_backup(deployment, output)




def verify_backup(path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("backup_crc_invalid")
        names = archive.namelist()
        if len(names) != len({n.casefold() for n in names}):
            raise RuntimeError("backup_duplicate_paths")
        metadata = json.loads(archive.read("BACKUP_MANIFEST.json"))
        if metadata["format"] != "zhiyu-logical-backup/1" or metadata["head"] != HEAD:
            raise RuntimeError("backup_format_not_supported")
        for name in [*names, *metadata["members"]]:
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name:
                raise RuntimeError("backup_path_invalid")
        if set(names) != set(metadata["members"]) | {"BACKUP_MANIFEST.json"}:
            raise RuntimeError("backup_manifest_members_differ")
        for name, value in metadata["members"].items():
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name:
                raise RuntimeError("backup_path_invalid")
            data = archive.read(name)
            if sha(data) != value["sha256"] or len(data) != value["bytes"]:
                raise RuntimeError("backup_hash_invalid")
        return metadata


def restore(deployment, path):
    verify_backup(path)  # Before stopping any service or modifying the database.
    from sqlalchemy import text

    engine, _, cfg = setup(deployment)
    with engine.connect() as conn:
        if conn.scalar(text("SELECT count(*) FROM pg_tables WHERE schemaname IN ('public','zhiyu_product')")):
            raise RuntimeError("restore_requires_empty_database")
    identifier, _ = owned_database(deployment)
    with zipfile.ZipFile(path) as archive:
        expected = json.loads(archive.read("database-state.json"))
        original = json.loads(archive.read("configuration/deployment.private.json"))
        docker(
            deployment,
            "exec",
            "-i",
            identifier,
            "pg_restore",
            "-U",
            "zhiyu",
            "-d",
            "zhiyu",
            "--exit-on-error",
            "--single-transaction",
            "--no-owner",
            "--no-privileges",
            input_bytes=archive.read("database.dump"),
        )
        cfg.update(
            username=original["username"],
            access_key=original["access_key"],
            parent_environment=original["parent_environment"],
        )
        save(deployment / "deployment.private.json", cfg)
        for kind in ("model", "lab"):
            (deployment / (kind + "-key.private")).write_bytes(
                archive.read("configuration/" + kind + "-key.private")
            )
        for name in archive.namelist():
            if name.startswith("recordings/"):
                target = deployment / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
            elif name.startswith(("artifacts/", "scenario/", "configuration/public/")):
                target = deployment / "restored-evidence" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
    if snapshot(deployment) != expected:
        raise RuntimeError("restore_snapshot_differs")
    cfg["installed_version"] = "1.0.0"
    save(deployment / "deployment.private.json", cfg)
    refresh(deployment)
    save(
        deployment / "restore-result.json",
        {
            "status": "PASS",
            "head": HEAD,
            "all_table_digests_unchanged": True,
            "audit_chains": "PASS",
            "backup_sha256": sha(path.read_bytes()),
        },
    )


def worker(deployment, *, scenario=None, cleanup=None):
    from uuid import uuid4

    from m9_lab_adapter import ControlledLab
    from sqlalchemy.orm import Session

    from zhiyu.db.demo_control import DemoRunRow
    from zhiyu.product import demo_control as controller
    from zhiyu.product.contracts import Query
    from zhiyu.product.demo_contracts import DemoCommand, StartDemo
    from zhiyu.product.demo_worker import once

    engine, principal, cfg = setup(deployment)
    adapter = ControlledLab(engine, cfg)
    query = Query(environment_id=cfg["parent_environment"], scope_id="scope-lab-web")
    identifier = None
    if scenario or cleanup:
        with Session(engine) as session, session.begin():
            if scenario:
                row = controller.start(
                    session,
                    principal,
                    query,
                    StartDemo(scenario_id=scenario, profile_id="controlled-lab", idempotency_key=uuid4().hex),
                )
            else:
                row = controller.read_run(session, cleanup, controller.authorize(session, principal, query))
                controller.command(
                    session,
                    principal,
                    query,
                    row.run_id,
                    "cleanup",
                    DemoCommand(expected_version=row.version),
                )
            identifier = row.run_id
        print(json.dumps({"run_id": identifier}), flush=True)
    lock = deployment / "worker.lock"
    with lock.open("x") as stream:
        stream.write(str(os.getpid()))
    try:
        while True:
            processed = once(engine, "controlled-lab", adapter)
            if identifier:
                with Session(engine) as session:
                    row = session.get(DemoRunRow, identifier)
                    result = controller.public_run(session, row)
                if result["status"] in controller.TERMINAL and result["cleanup_status"] != "QUEUED":
                    print(
                        json.dumps(
                            {
                                k: result[k]
                                for k in (
                                    "run_id",
                                    "status",
                                    "cleanup_status",
                                    "actual_outcome",
                                    "error_code",
                                )
                            }
                        ),
                        flush=True,
                    )
                    return
            if not processed:
                time.sleep(2)
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=sorted(PUBLIC_OPERATIONS))
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--port", type=int, default=18010)
    parser.add_argument("--scenario", choices=list("ABCDE"), default="B")
    parser.add_argument("--run-id")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--container", action="store_true")
    parser.add_argument("--bootstrap-only", action="store_true")
    args = parser.parse_args()
    deployment = args.deployment.resolve()
    if args.operation in {"worker", "run", "cleanup", "backup", "restore", "upgrade"}:
        with operation_lock(deployment):
            return execute(args, deployment)
    return execute(args, deployment)


def execute(args, deployment):
    if args.operation == "install":
        return install(deployment, args.model, args.port, args.backup)
    if args.operation == "serve":
        setup(deployment, container=args.container)
        import uvicorn

        from zhiyu.main import app

        return uvicorn.run(
            app, host="0.0.0.0" if args.container else "127.0.0.1", port=8000, access_log=False
        )
    if args.operation == "start":
        return start_api(deployment)
    if args.operation == "stop":
        return compose(deployment, "stop", "api")
    if args.operation == "status":
        cfg = configuration(deployment)
        print(
            json.dumps(
                {
                    "project": cfg["project"],
                    "version": cfg["installed_version"],
                    "url": cfg["origin"],
                    "services": [
                        json.loads(line)
                        for line in compose(deployment, "ps", "--format", "json").decode().splitlines()
                        if line.strip()
                    ],
                }
            )
        )
        return
    if args.operation == "worker":
        return worker(deployment)
    if args.operation in {"run", "cleanup"}:
        return worker(
            deployment,
            scenario=args.scenario if args.operation == "run" else None,
            cleanup=args.run_id if args.operation == "cleanup" else None,
        )
    if args.operation == "snapshot":
        print(json.dumps(snapshot(deployment)), flush=True)
        return
    if args.operation == "backup":
        print(json.dumps(backup(deployment, args.backup)), flush=True)
        return
    if args.operation == "restore":
        return restore(deployment, args.backup)
    if args.operation == "upgrade":
        if not args.bootstrap_only:
            idle(deployment)
            if not args.backup or not args.backup.exists():
                raise RuntimeError("verified_pre_upgrade_backup_required")
            verify_backup(args.backup)
        return bootstrap(deployment)


if __name__ == "__main__":
    main()
