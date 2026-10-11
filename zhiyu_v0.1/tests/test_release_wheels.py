"""Reject inconsistent or untrusted frozen artifacts before downloading them."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_wheels", ROOT / "tools/release_wheels.py")
wheels = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wheels)


@pytest.fixture
def locks(tmp_path):
    for name in (*wheels.LOCKS, "uv.lock", "config/reference-build-wheel.json"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return tmp_path


def change_build(locks, field, value):
    path = locks / "config/reference-build-wheel.json"
    data = json.loads(path.read_text())
    data["wheels"][0][field] = value
    path.write_text(json.dumps(data))


def test_original_locks_select_official_hashed_urls(locks):
    selected = wheels.selected(locks)
    assert len(selected) == 28
    assert all(" @ https://files.pythonhosted.org/" in line and " --hash=sha256:" in line for line in selected)


def test_artifact_digest_disagreement_fails_closed(locks):
    change_build(locks, "hash", "sha256:" + "0" * 64)
    with pytest.raises(RuntimeError, match="reference_wheel_hash_not_in_lock"):
        wheels.selected(locks)


def test_foreign_artifact_origin_fails_closed(locks):
    change_build(locks, "url", "https://example.org/setuptools-84.0.0-py3-none-any.whl")
    with pytest.raises(RuntimeError, match="reference_wheel_source_invalid"):
        wheels.selected(locks)


def test_filename_version_disagreement_fails_closed(locks):
    change_build(locks, "url", "https://files.pythonhosted.org/setuptools-85.0.0-py3-none-any.whl")
    with pytest.raises(RuntimeError, match="reference_wheel_identity_invalid"):
        wheels.selected(locks)


def test_no_compatible_artifact_rejected_before_download(locks):
    with pytest.raises(RuntimeError, match="reference_compatible_wheel_missing"):
        wheels.selected(locks, tags=[])
