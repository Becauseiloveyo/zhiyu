"""Compare release metadata, retained tests and frozen artifacts against immutable inputs."""

import hashlib
import json
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    archive = ROOT.parent / "artifacts/智御_Project_v0.5.0_AI_Decision_Brain.zip"
    assert (
        hashlib.sha256(archive.read_bytes()).hexdigest()
        == "dba02bafea018ca8e114d26bf9e2da010850dd709d3abb701a95655e2f7efb48"
    )
    with zipfile.ZipFile(archive) as package:
        old = tomllib.loads(package.read("zhiyu_v0.5.0/uv.lock").decode())
    current = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    before = next(p for p in old["package"] if p["name"] == "zhiyu")
    after = next(p for p in current["package"] if p["name"] == "zhiyu")
    assert before["version"] == "0.5.0" and after["version"] == "0.6.0"
    before["version"] = "0.6.0"
    assert old == current, "dependency resolution changed beyond own version"
    assert tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"] == after["version"]
    rc = json.loads((ROOT / "docs/m6-runtime/rc/RC4.json").read_text())
    retained = {k: v for k, v in rc["controlled_files"].items() if k.startswith("tests/")}
    for group in (retained, rc["frozen_files"]):
        for name, digest in group.items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    report = {
        "status": "PASS",
        "lock_own_version": "0.5.0 -> 0.6.0",
        "all_other_uv_fields_identical": True,
        "historical_test_files_unchanged": len(retained),
        "historical_test_inventory": rc["test_inventory_count"],
        "frozen_files_unchanged": len(rc["frozen_files"]),
        "architecture_change": False,
    }
    path = ROOT / "docs/m6-runtime/remediation-development/integrity.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
