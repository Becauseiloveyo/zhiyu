"""Operator entry point for the local controlled Lab profile (disabled in default API settings).

prepare installs the product schema, builds a source-baked image and binds an owned database.
serve exposes the existing Web Console on loopback; worker is a separate Docker-owning process.
run is an acceptance driver using the very same controller and worker as the browser.
"""

import argparse
import hashlib
import json
import os
import secrets
import time
from uuid import uuid4

from m9_lab_adapter import CONTROL_NETWORK, OWNER, PRIVATE, ROOT, ControlledLab, checked, docker

CONFIG = PRIVATE / "deployment.private.json"


def install():
    import psycopg
    from psycopg import sql

    PRIVATE.mkdir(parents=True, exist_ok=True)
    owner = json.loads((ROOT.parent / ".work/m9-validation/local-secrets.json").read_text())
    container = owner["container"]
    detail = json.loads(checked("inspect", container))[0]
    if detail["Config"]["Labels"].get("zhiyu.owner") != "m9-validation":
        raise RuntimeError("canonical_database_not_owned")
    checked("start", container)
    for _ in range(30):
        if docker("exec", container, "pg_isready", "-U", "zhiyu").returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError("canonical_database_not_ready")
    port = int(checked("port", container, "5432/tcp").decode().strip().rsplit(":", 1)[1])
    if CONFIG.exists():
        config = json.loads(CONFIG.read_text())
    else:
        config = {
            "database": "zhiyu_demo_" + secrets.token_hex(6),
            "username": "operator",
            "access_key": secrets.token_urlsafe(40),
            "parent_environment": "v09-demo-control",
        }
    database = config["database"]
    if not database.startswith("zhiyu_demo_") or len(database) != 23:
        raise RuntimeError("owned_database_identity_invalid")
    with psycopg.connect(
        host="127.0.0.1", port=port, user="zhiyu", password=owner["password"], dbname="zhiyu", autocommit=True
    ) as db:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
            db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    found = docker("network", "inspect", CONTROL_NETWORK)
    if found.returncode:
        checked("network", "create", "--internal", "--label", "zhiyu.owner=" + OWNER, CONTROL_NETWORK)
    elif json.loads(found.stdout)[0]["Labels"].get("zhiyu.owner") != OWNER:
        raise RuntimeError("foreign_control_network")
    detail = json.loads(checked("inspect", container))[0]
    if CONTROL_NETWORK not in detail["NetworkSettings"]["Networks"]:
        checked("network", "connect", "--alias", "canonical-postgres", CONTROL_NETWORK, container)
    for kind in ("model", "lab"):
        path = PRIVATE / (kind + "-key.private")
        if not path.exists():
            path.write_text(secrets.token_urlsafe(40), encoding="utf-8")
        config[kind + "_key_path"] = str(path)
    config.update(
        database_url=f"postgresql+psycopg://zhiyu:{owner['password']}@127.0.0.1:{port}/{database}",
        container_database_url=f"postgresql+psycopg://zhiyu:{owner['password']}@canonical-postgres:5432/{database}",
        model_path=str(ROOT.parent / ".work/m5-model/qwen2.5-1.5b-instruct-q4_k_m.gguf"),
    )
    build = docker("build", "--target", "runtime", "-t", "zhiyu-v09-demo:local", ".", timeout=600)
    (PRIVATE / "build.log").write_bytes(build.stdout + build.stderr)
    if build.returncode:
        raise RuntimeError("source_image_build_failed")
    config["image_id"] = json.loads(checked("image", "inspect", "zhiyu-v09-demo:local"))[0]["Id"]
    CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
    engine, principal, _ = load()
    from alembic import command
    from alembic.config import Config
    from m6_sensor_ingest import prepare
    from sqlalchemy.orm import Session

    from zhiyu.db.models import EnvironmentRow
    from zhiyu.product.demo_store import initialize

    migration = Config(str(ROOT / "alembic.ini"))
    migration.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        migration.attributes["connection"] = connection
        command.upgrade(migration, "head")
    initialize(engine)
    with Session(engine) as db:
        exists = db.get(EnvironmentRow, config["parent_environment"]) is not None
    if not exists:
        prepare(engine, config["parent_environment"])
    print(
        json.dumps(
            {
                "status": "PREPARED",
                "profile_id": "controlled-lab",
                "image_id": config["image_id"],
                "url": "http://127.0.0.1:8000",
                "credentials": "PRIVATE_OPERATOR_FILE_ONLY",
            }
        )
    )


def load():
    config = json.loads(CONFIG.read_text())
    os.environ["ZHIYU_DATABASE_URL"] = config["database_url"]
    os.environ["ZHIYU_WEB_DIST"] = str(ROOT / "frontend/dist")
    from zhiyu.core.config import settings
    from zhiyu.core.identity import ServicePrincipal
    from zhiyu.db.session import get_engine
    from zhiyu.product.access import product_settings
    from zhiyu.product.contracts import ReadGrant
    from zhiyu.product.demo_contracts import DemoProfile
    from zhiyu.product.sessions import BrowserAccount

    settings.database_url = config["database_url"]
    principal = ServicePrincipal(
        principal_id="v09-demo-operator",
        environment_ids={config["parent_environment"]},
        permissions={"product:read", "demo:run"},
    )
    product_settings.browser_users = {
        config["username"]: BrowserAccount(
            principal=principal, access_key_sha256=hashlib.sha256(config["access_key"].encode()).hexdigest()
        )
    }
    product_settings.grants = {
        principal.principal_id: {
            config["parent_environment"]: ReadGrant(
                version="v09-local-controlled-lab/1", scope_ids={"scope-lab-web"}
            )
        }
    }
    product_settings.demo_profiles = {
        "controlled-lab": DemoProfile(
            environment_id=config["parent_environment"],
            scope_id="scope-lab-web",
            scenarios={"A", "B", "C", "D", "E"},
            enabled=True,
        )
    }
    product_settings.recording_root = str(ROOT / "artifacts/v0.9/recordings")
    return get_engine(), principal, config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["prepare", "serve", "worker", "run", "cleanup", "status"])
    parser.add_argument("--scenario", choices=list("ABCDE"), default="B")
    parser.add_argument("--run-id")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.operation == "prepare":
        return install()
    engine, principal, config = load()
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from zhiyu.db.demo_control import DemoRunRow
    from zhiyu.product import demo_control as controller
    from zhiyu.product.contracts import Query
    from zhiyu.product.demo_contracts import DemoCommand, StartDemo
    from zhiyu.product.demo_worker import once

    adapter = ControlledLab(engine, config)
    query = Query(environment_id=config["parent_environment"], scope_id="scope-lab-web")
    if args.operation == "serve":
        import uvicorn

        from zhiyu.main import app

        return uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)
    if args.operation == "worker":
        while True:
            identifier = once(engine, "controlled-lab", adapter)
            if args.once:
                print(json.dumps({"processed_run": identifier}))
                return
            if identifier is None:
                time.sleep(2)
    if args.operation == "status":
        with Session(engine) as db:
            rows = list(db.scalars(select(DemoRunRow).order_by(DemoRunRow.created_at.desc()).limit(10)))
            print(json.dumps([controller.public_run(db, row) for row in rows], default=str))
        return
    with Session(engine) as db, db.begin():
        if args.operation == "run":
            row = controller.start(
                db,
                principal,
                query,
                StartDemo(
                    scenario_id=args.scenario, profile_id="controlled-lab", idempotency_key=uuid4().hex
                ),
            )
        else:
            row = controller.read_run(db, args.run_id, controller.authorize(db, principal, query))
            row = controller.command(
                db, principal, query, row.run_id, "cleanup", DemoCommand(expected_version=row.version)
            )
        identifier = row.run_id
    print(json.dumps({"run_id": identifier, "status": "QUEUED"}), flush=True)
    for _ in range(5):
        processed = once(engine, "controlled-lab", adapter)
        with Session(engine) as db:
            row = db.get(DemoRunRow, identifier)
            result = controller.public_run(db, row)
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in (
                        "run_id",
                        "status",
                        "step_index",
                        "cleanup_status",
                        "actual_outcome",
                        "error_code",
                    )
                }
            ),
            flush=True,
        )
        if not processed or result["status"] in controller.TERMINAL and result["cleanup_status"] != "QUEUED":
            break
    (ROOT / "artifacts/v0.9/lab" / identifier / "controller-result.json").write_text(
        json.dumps(result, default=str, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
