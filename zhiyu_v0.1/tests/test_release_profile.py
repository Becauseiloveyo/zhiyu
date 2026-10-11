"""Restore rejects damaged or ambiguous backups before touching services/data."""

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_profile", ROOT / "tools/release_profile.py")
profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile)


def archive(
    tmp_path,
    *,
    name="database.dump",
    payload=b"dump",
    extra=False,
    digest=None,
    head=profile.HEAD,
    duplicate=False,
):
    path = tmp_path / "backup.zip"
    manifest = {
        "format": "zhiyu-logical-backup/1",
        "head": head,
        "members": {name: {"sha256": digest or hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}},
    }
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(name, payload)
        z.writestr("BACKUP_MANIFEST.json", json.dumps(manifest))
        if extra:
            z.writestr("unregistered", b"x")
        if duplicate:
            z.writestr(name.upper(), payload)
    return path


def test_verified_backup_members(tmp_path):
    assert profile.verify_backup(archive(tmp_path))["head"] == profile.HEAD


def test_damaged_payload_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="backup_hash_invalid"):
        profile.verify_backup(archive(tmp_path, digest="0" * 64))


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/private", "folder\\escape"])
def test_unsafe_restore_paths_rejected(tmp_path, name):
    with pytest.raises(RuntimeError, match="backup_path_invalid"):
        profile.verify_backup(archive(tmp_path, name=name))


def test_unregistered_backup_member_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="backup_manifest_members_differ"):
        profile.verify_backup(archive(tmp_path, extra=True))


def test_case_duplicate_backup_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="backup_duplicate_paths"):
        profile.verify_backup(archive(tmp_path, duplicate=True))


def test_unsupported_schema_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="backup_format_not_supported"):
        profile.verify_backup(archive(tmp_path, head="unknown"))


def test_nonempty_install_rejected_before_commands(tmp_path):
    (tmp_path / "user-data").write_text("preserve")
    with pytest.raises(RuntimeError, match="clean_install_requires_new_empty_directory"):
        profile.install(tmp_path, tmp_path / "absent-model", 18010)
    assert (tmp_path / "user-data").read_text() == "preserve"
