"""Owned historical export and fresh-volume restore; no business execution API."""

import argparse
import copy
import hashlib
import json
import os
import re
import secrets
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import release_profile as profile


def canonical_runs(url):
    from sqlalchemy import create_engine, text

    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 3})
    try:
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn, conn.begin():
            conn.execute(text("SET TRANSACTION READ ONLY"))
            values = conn.scalars(text("SELECT row_to_json(r)::text FROM zhiyu_product.demo_runs r ORDER BY run_id")).all()
        runs = [json.loads(v) for v in values]
        if any(r["cleanup_status"] != "CLEAN" for r in runs):
            raise RuntimeError("cleanup_all_historical_runs_before_backup")
        if any(not re.fullmatch(r"demo-[a-f0-9]{32}", r["run_id"]) for r in runs):
            raise RuntimeError("unregistered_historical_run_identity")
        return runs
    finally:
        engine.dispose()


def state(deployment, source):
    return json.loads(profile.command(
        [sys.executable, str(profile.ROOT / "tools/release_profile.py"), "snapshot", "--deployment", str(source)],
        deployment,
    ))


def legacy_source(deployment, config_path, owner_path):
    cfg, owner = profile.read(config_path), profile.read(owner_path)
    if not re.fullmatch(r"zhiyu_demo_[a-f0-9]{12}", cfg["database"]):
        raise RuntimeError("unregistered_legacy_database")
    if not re.fullmatch(r"zhiyu-m9-tests-[a-f0-9]{10}", owner["container"]):
        raise RuntimeError("unregistered_legacy_container")
    detail = json.loads(profile.docker(deployment, "inspect", owner["container"]))[0]
    if detail["Config"]["Labels"].get("zhiyu.owner") != "m9-validation":
        raise RuntimeError("foreign_legacy_database_container")
    port = profile.loopback_port(detail, "5432/tcp")
    cfg.update(database_url="postgresql+psycopg://zhiyu:" + owner["password"] + "@127.0.0.1:" + port + "/" + cfg["database"],
               control_network="zhiyu-m9-demo-control", origin="http://127.0.0.1:8000")
    directory = deployment / "legacy-source"
    profile.protected(directory)
    profile.save(directory / "deployment.private.json", cfg)
    return directory, cfg, owner["container"]


def complete_backup(deployment, output, *, legacy_config=None, owner_record=None):
    output = profile.backup_destination(deployment, output)
    profile.idle(deployment)
    legacy = legacy_config is not None
    if legacy != (owner_record is not None):
        raise RuntimeError("legacy_backup_requires_config_and_owner_record")
    if legacy:
        source, cfg, container = legacy_source(deployment, legacy_config, owner_record)
        version, evidence_root = "0.9.0", profile.ROOT / "artifacts/v0.9/lab"
        recording_root = profile.ROOT / "artifacts/v0.9/recordings"
    else:
        source, cfg = deployment, profile.configuration(deployment)
        container, _ = profile.owned_database(deployment)
        version, evidence_root = cfg["installed_version"], profile.ROOT / "artifacts/v1.0/lab"
        recording_root = deployment / "recordings"
        profile.compose(deployment, "stop", "api")
    try:
        if not legacy:
            profile.idle(deployment)  # Close the window between the first idle check and API stop.
        runs = canonical_runs(cfg["database_url"])
        before = state(deployment, source)
        dump = profile.docker(deployment, "exec", container, "pg_dump", "-U", "zhiyu", "-d", cfg["database"],
                              "-Fc", "--no-owner", "--no-privileges")
        members = {"database.dump": dump, "database-state.json": json.dumps(before, sort_keys=True).encode(),
                   "configuration/deployment.private.json": (source / "deployment.private.json").read_bytes(),
                   "scenario/runs.json": json.dumps(runs, sort_keys=True).encode()}
        for kind in ("model", "lab"):
            key = Path(cfg[kind + "_key_path"]) if legacy else deployment / (kind + "-key.private")
            members["configuration/" + kind + "-key.private"] = key.read_bytes()
        for run in runs:
            identifier = run["run_id"]
            recording = recording_root / (identifier + ".json")
            if recording.exists():
                if not recording.resolve().is_relative_to(recording_root.resolve()):
                    raise RuntimeError("recording_path_outside_owned_root")
                members["recordings/" + recording.name] = recording.read_bytes()
            elif run["status"] == "COMPLETED":
                raise RuntimeError("completed_run_recording_missing")
            folder = evidence_root / identifier
            root = evidence_root
            if not legacy and not folder.exists():
                root = deployment / "restored-evidence/artifacts"
                folder = root / identifier
            for path in folder.rglob("*"):
                if path.is_file():
                    if not path.resolve().is_relative_to(root.resolve()):
                        raise RuntimeError("evidence_path_outside_owned_root")
                    members["artifacts/" + path.relative_to(root).as_posix()] = path.read_bytes()
            if run["status"] == "COMPLETED" and any("artifacts/" + identifier + "/" + n not in members
                                                     for n in ("report.json", "report.md")):
                raise RuntimeError("completed_run_reports_missing")
        freeze = profile.read(profile.ROOT / "artifacts/RC_STATE_v1.0.0.json")
        identities = {k: freeze[k] for k in ("architecture", "migration_head", "model_runtime", "prompt_policy",
                                            "ai_policy_version", "scenario_version", "scenario_definition_sha256",
                                            "report_template_sha256", "ai5_frozen_digest", "baseline_v09_zip_sha256")}
        members["scenario/version-identities.json"] = json.dumps(identities, sort_keys=True).encode()
        for name in ("src/zhiyu/product/demo_contracts.py", "src/zhiyu/product/reports.py"):
            members["scenario/" + Path(name).name] = (profile.ROOT / name).read_bytes()
        for name in freeze["controlled_files"]:
            if name.startswith("config/"):
                members["configuration/public/" + name[7:]] = (profile.ROOT / name).read_bytes()
        if state(deployment, source) != before:
            raise RuntimeError("backup_database_changed_during_dump")
        metadata = {"format": "zhiyu-logical-backup/1", "version": version,
                    "created_at": datetime.now(UTC).isoformat(), "head": profile.HEAD,
                    "members": {n: {"sha256": profile.sha(v), "bytes": len(v)} for n, v in members.items()},
                    "included": ["PostgreSQL", "configuration and credentials", "reports", "observed artifacts",
                                 "recordings", "scenario manifests and frozen identities"],
                    "excluded": ["model weights (external pinned SHA256)", "images", "sessions/snapshot cache",
                                 "virtualenv/npm caches", "private command logs", "disposable Lab volumes"],
                    "protection": "PRIVATE UNENCRYPTED; ACL directory; encrypted storage required for transport"}
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, payload in members.items():
                archive.writestr(name, payload)
            archive.writestr("BACKUP_MANIFEST.json", json.dumps(metadata, indent=2))
        profile.verify_backup(output)
        result = {"status": "PASS", "version": version, "head": profile.HEAD, "sha256": profile.sha(output.read_bytes()),
                  "bytes": output.stat().st_size, "members": len(members) + 1, "timestamp": metadata["created_at"],
                  "historical_tables": len(before["tables"]), "runs": len(runs), "database_unchanged": True,
                  "included": metadata["included"]}
        profile.save(deployment / ("legacy-backup-result.json" if legacy else "backup-result.json"), result)
        return result
    finally:
        if not legacy:
            profile.start_api(deployment)


def restore_environment(deployment, reference, archive, port):
    profile.verify_backup(archive)  # Reject before creating any runtime resources.
    if deployment.exists() and any(deployment.iterdir()):
        raise RuntimeError("restore_environment_requires_new_empty_directory")
    if not 1024 <= port <= 65535:
        raise RuntimeError("invalid_loopback_port")
    source = profile.configuration(reference)
    if source["install_state"] != "INSTALLED":
        raise RuntimeError("restore_requires_verified_installed_reference")
    profile.protected(deployment)
    with Path(source["model_path"]).open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != profile.MODEL_SHA:
            raise RuntimeError("model_weight_digest_mismatch")
    for image in (source["image_id"], *source["sensor_images"].values()):
        if json.loads(profile.docker(deployment, "image", "inspect", image))[0]["Id"] != image:
            raise RuntimeError("restore_image_identity_mismatch")
    project = "zhiyu-v1-" + secrets.token_hex(6)
    cfg = {**source, "project": project, "owner": project, "password": secrets.token_urlsafe(40),
           "access_key": secrets.token_urlsafe(40), "control_network": project + "_control",
           "origin": "http://127.0.0.1:" + str(port), "api_port": port, "install_state": "RESTORING"}
    for kind in ("model", "lab"):
        path = deployment / (kind + "-key.private")
        path.write_text(secrets.token_urlsafe(40), encoding="utf-8")
        cfg[kind + "_key_path"] = str(path)
    cfg["container_database_url"] = "postgresql+psycopg://zhiyu:" + cfg["password"] + "@canonical-postgres:5432/zhiyu"
    profile.save(deployment / "deployment.private.json", cfg)
    (deployment / "recordings").mkdir()
    spec = copy.deepcopy(profile.read(reference / "compose.private.json"))
    for collection in (spec["services"], spec["networks"], spec["volumes"]):
        for value in collection.values():
            value["labels"] = {"zhiyu.owner": project}
    spec["services"]["api"]["volumes"] = [str(deployment / "api.private.json") + ":/run/reference/api.private.json:ro",
                                           str(deployment / "recordings") + ":/recordings:ro"]
    spec["services"]["ingress"]["ports"] = ["127.0.0.1::5432", "127.0.0.1:" + str(port) + ":8000"]
    profile.save(deployment / "compose.private.json", spec)
    profile.compose(deployment, "up", "-d", "--wait", "postgres", "ingress")
    profile.refresh(deployment)
    profile.command([sys.executable, str(profile.ROOT / "tools/release_profile.py"), "restore", "--deployment",
                     str(deployment), "--backup", str(archive)], deployment)
    profile.command([sys.executable, str(profile.ROOT / "tools/release_profile.py"), "upgrade", "--deployment",
                     str(deployment), "--backup", str(archive)], deployment)
    cfg = profile.configuration(deployment)
    cfg["install_state"] = "INSTALLED"
    cfg["operator_python"] = sys.executable
    profile.save(deployment / "deployment.private.json", cfg)
    profile.start_api(deployment)
    return {"status": "RESTORED", "project": project, "url": cfg["origin"], "version": "1.0.0",
            "new_database_volume": True, "operator_and_images": "REUSED_VERIFIED_REFERENCE_NOT_CLEAN_INSTALL_CLAIM"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["legacy-backup", "restore-environment"])
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--legacy-config", type=Path)
    parser.add_argument("--owner-record", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--port", type=int, default=18011)
    args = parser.parse_args()
    deployment = args.deployment.resolve()
    if args.operation == "legacy-backup":
        if not args.legacy_config or not args.owner_record:
            raise RuntimeError("legacy_backup_requires_config_and_owner_record")
        with profile.operation_lock(deployment):
            result = complete_backup(deployment, args.backup, legacy_config=args.legacy_config, owner_record=args.owner_record)
    else:
        if not args.reference:
            raise RuntimeError("restore_requires_verified_reference")
        result = restore_environment(deployment, args.reference.resolve(), args.backup.resolve(), args.port)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
