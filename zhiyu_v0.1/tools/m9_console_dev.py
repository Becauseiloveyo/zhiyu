"""Local v0.9 integration workspace. Canonical ingestion, explicitly SYNTHETIC sources.

Uses only the owned m9-validation PostgreSQL container. No production database is touched.
Credentials remain under the ignored workspace .work directory; never bundled with the UI.
"""

import hashlib
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / ".work/m9-validation"
sys.path.insert(0, str(ROOT / "tests"))


def main():
    import psycopg
    from alembic import command
    from alembic.config import Config
    from psycopg import sql
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    owner = json.loads((WORK / "local-secrets.json").read_text())
    name = owner["container"]
    run = lambda args: subprocess.check_output(["docker", *args], text=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).strip()
    if run(["inspect", "-f", '{{index .Config.Labels "zhiyu.owner"}}', name]) != "m9-validation":
        raise RuntimeError("owned container identity mismatch")
    port = int(run(["port", name, "5432/tcp"]).rsplit(":", 1)[1])
    path = WORK / "console-private.json"
    if not path.exists():
        path.write_text(json.dumps({"database": "zhiyu_console_" + secrets.token_hex(5),
                                   "username": "viewer", "access_key": secrets.token_urlsafe(32)}))
    config = json.loads(path.read_text())
    database = config["database"]
    assert database.startswith("zhiyu_console_") and len(database) == 24
    with psycopg.connect(host="127.0.0.1", port=port, user="zhiyu", password=owner["password"],
                        dbname="zhiyu", autocommit=True) as db:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
            db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    os.environ["ZHIYU_DATABASE_URL"] = f"postgresql+psycopg://zhiyu:{owner['password']}@127.0.0.1:{port}/{database}"
    os.environ["ZHIYU_WEB_DIST"] = str(ROOT / "frontend/dist")
    from zhiyu.core.config import settings
    from zhiyu.core.identity import ServicePrincipal
    from zhiyu.db.models import EnvironmentRow, IncidentRow
    from zhiyu.db.session import get_engine
    from zhiyu.product.access import product_settings
    from zhiyu.product.contracts import ReadGrant
    from zhiyu.product.sessions import BrowserAccount
    from zhiyu.services.bootstrap import BootstrapBundle, BootstrapService

    engine = get_engine()
    migration = Config(str(ROOT / "alembic.ini"))
    migration.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        migration.attributes["connection"] = connection
        command.upgrade(migration, "head")
    with Session(engine) as db:
        if db.get(EnvironmentRow, "lab-zhiyu-01") is None:
            db.rollback()
            BootstrapService(db).apply(BootstrapBundle.model_validate_json(
                (ROOT / "config/bootstrap.lab.json").read_text(encoding="utf-8")), actor_id="v09-local-bootstrap")
        seeded = db.scalar(select(IncidentRow.incident_id).limit(1))
    from fastapi.testclient import TestClient
    from test_incident_api import http_chain
    from test_raw_ingest import sensor_principal
    from zhiyu.main import app

    key = secrets.token_urlsafe(40)
    settings.service_tokens = {hashlib.sha256(key.encode()).hexdigest(): sensor_principal()}
    if not seeded:
        with TestClient(app, headers={"Authorization": "Bearer " + key}) as client:
            seeded = http_chain(client)
    # Remove the temporary ingest identity before serving the console.
    settings.service_tokens = {}
    principal = ServicePrincipal(principal_id="console-viewer", environment_ids={"lab-zhiyu-01"},
                                 permissions={"product:read"})
    product_settings.browser_users = {config["username"]: BrowserAccount(
        access_key_sha256=hashlib.sha256(config["access_key"].encode()).hexdigest(), principal=principal)}
    product_settings.grants = {principal.principal_id: {"lab-zhiyu-01": ReadGrant(
        version="console-local-v1", scope_ids={"scope-lab-web"})}}
    from zhiyu.product.access import RecordingRegistration, authorize
    from zhiyu.product.contracts import Query
    from zhiyu.product.demo_store import initialize
    from zhiyu.product.queries import create_snapshot

    initialize(engine)
    # A read-only development recording, pinned once. Never label this core fixture as real Sensor acceptance.
    archive_directory = ROOT / "artifacts/v0.9/recordings"
    archive_directory.mkdir(parents=True, exist_ok=True)
    manifest_path = WORK / "recording-manifest.json"
    if not manifest_path.exists():
        query = Query(environment_id="lab-zhiyu-01", scope_id="scope-lab-web", hours=168)
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            with connection.begin():
                from sqlalchemy import text
                connection.execute(text("SET TRANSACTION READ ONLY"))
                with Session(bind=connection) as db:
                    snapshot = create_snapshot(db, query, authorize(db, principal, query), seeded)
        content = snapshot.model_dump_json().encode()
        (archive_directory / "console-canonical.json").write_bytes(content)
        registration = RecordingRegistration(environment_id=query.environment_id, scope_id=query.scope_id,
            title="核心摄取历史快照 · SYNTHETIC 开发验证", filename="console-canonical.json",
            sha256=hashlib.sha256(content).hexdigest(), source_run_id="local-console-capture-" + snapshot.snapshot_id,
            model_source="NONE")
        manifest_path.write_text(registration.model_dump_json(), encoding="utf-8")
    product_settings.recording_root = str(archive_directory)
    product_settings.recordings = {"console-canonical": RecordingRegistration.model_validate_json(
        manifest_path.read_text(encoding="utf-8"))}
    (ROOT / "artifacts/v0.9/console-local.json").write_text(json.dumps({
        "url": "http://127.0.0.1:8000", "environment_id": "lab-zhiyu-01", "incident_id": seeded,
        "data_origin": "SYNTHETIC", "run_mode": "LIVE", "source": "canonical PostgreSQL core ingestion",
        "acceptance": "DEVELOPMENT_ONLY_NOT_REAL_SENSOR_ACCEPTANCE"}, indent=2), encoding="utf-8")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)


if __name__ == "__main__":
    main()
