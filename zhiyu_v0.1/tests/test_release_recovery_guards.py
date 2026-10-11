"""Check protected destinations and coordination before any database/service mutation."""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_profile", ROOT / "tools/release_profile.py")
profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile)


def test_backup_outside_private_directory_preserves_existing_user_file(tmp_path, monkeypatch):
    deployment = tmp_path / "deployment"
    deployment.mkdir()
    output = tmp_path / "user-data.zip"
    output.write_bytes(b"preserve")
    monkeypatch.setattr(profile, "protected", lambda _: pytest.fail("must not alter unrelated ACL"))
    with pytest.raises(RuntimeError, match="backup_destination_outside_private_backups"):
        profile.backup(deployment, output)
    assert output.read_bytes() == b"preserve"


def test_existing_private_archive_is_never_overwritten(tmp_path, monkeypatch):
    folder = tmp_path / "backups"
    folder.mkdir()
    output = folder / "backup.zip"
    output.write_bytes(b"original backup")
    monkeypatch.setattr(profile, "protected", lambda _: pytest.fail("must reject before altering ACL"))
    with pytest.raises(RuntimeError, match="backup_destination_invalid_or_exists"):
        profile.backup_destination(tmp_path, output)
    assert output.read_bytes() == b"original backup"


def test_missing_backup_path_rejected_before_service_commands(tmp_path):
    with pytest.raises(RuntimeError, match="backup_destination_required"):
        profile.backup(tmp_path, None)


def test_concurrent_operator_rejected_without_releasing_first_operators_lock(tmp_path):
    with profile.operation_lock(tmp_path):
        content = (tmp_path / "operator.lock").read_bytes()
        with pytest.raises(RuntimeError, match="reference_operator_operation_already_active"):
            with profile.operation_lock(tmp_path):
                pytest.fail("second operator entered")
        assert (tmp_path / "operator.lock").read_bytes() == content
    assert not (tmp_path / "operator.lock").exists()


def test_credential_bearing_command_result_remains_usable_but_log_has_no_secrets(tmp_path, monkeypatch):
    password, key = "random-database-password-actual", "random-browser-key-actual"
    (tmp_path / "deployment.private.json").write_text(json.dumps({"password": password, "access_key": key}))
    (tmp_path / "model-key.private").write_text("random-model-key-actual")
    raw = ("POSTGRES_PASSWORD=" + password + '\npostgresql+psycopg://user:' + password + '@db/zhiyu\n'
           + key + '\nrandom-model-key-actual').encode()
    monkeypatch.setattr(profile.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, raw, b""))
    assert profile.command(["docker", "inspect", "owned"], tmp_path) == raw
    log = (tmp_path / "operations.log").read_bytes()
    assert password.encode() not in log and key.encode() not in log and b"random-model-key-actual" not in log


def test_pg_dump_binary_is_returned_intact_without_writing_payload_to_log(tmp_path, monkeypatch):
    binary = b"PGDMP\x00\xffprivate-backup-payload"
    monkeypatch.setattr(profile.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, binary, b""))
    assert profile.command(["docker", "exec", "owned", "pg_dump"], tmp_path) == binary
    log = (tmp_path / "operations.log").read_bytes()
    assert binary not in log and profile.sha(binary).encode() in log


def test_timeout_diagnostics_redact_password_and_retain_error_context(tmp_path, monkeypatch):
    (tmp_path / "deployment.private.json").write_text(json.dumps({"password": "timeout-password-actual"}))
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1, output=b"timeout-password-actual", stderr=b"timed out contacting database")
    monkeypatch.setattr(profile.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="reference_command_timed_out"):
        profile.command(["docker", "inspect", "owned"], tmp_path)
    log = (tmp_path / "operations.log").read_bytes()
    assert b"timeout-password-actual" not in log and b"timed out contacting database" in log
