"""Record an immutable release candidate; commits never substitute for byte evidence."""

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime

from runtime_acceptance import ROOT

from zhiyu.services.health import SCHEMA_REVISION


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("revision")
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    destination = ROOT / "docs/m6-runtime/rc" / (args.revision + ".json")
    assert not destination.exists()
    records = []
    inventory = []
    for command in [
        ["git", "status", "--short"],
        ["git", "rev-parse", "--show-toplevel"],
        [sys.executable, "-X", "utf8", "-m", "alembic", "heads"],
        [sys.executable, "-X", "utf8", "tools/schema_snapshot.py", "--check"],
        [sys.executable, "-X", "utf8", "-m", "pytest", "--collect-only", "-q"],
    ]:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120
        )
        assert result.returncode == 0, result.stderr
        records.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        if "--collect-only" in command:
            inventory = [line for line in result.stdout.splitlines() if "::test_" in line]
    archive = ROOT.parent / "artifacts/智御_Project_v0.5.0_AI_Decision_Brain.zip"
    assert sha(archive.read_bytes()) == "dba02bafea018ca8e114d26bf9e2da010850dd709d3abb701a95655e2f7efb48"
    frozen = {}
    with zipfile.ZipFile(archive) as package:
        for name in package.namelist():
            relative = name.split("/", 1)[-1]
            if relative.startswith(("baseline/", "migrations/versions/", "schema/")) or relative in {
                "src/zhiyu/domain/contracts.py",
                "docs/AI_CONTEXT_ai.5.md",
                "docs/PROJECT_STATE_ai.5.yaml",
                "requirements-runtime.lock",
                "requirements-dev.lock",
            }:
                content = package.read(name)
                assert content == (ROOT / relative).read_bytes(), relative
                frozen[relative] = sha(content)
    tracked = {}
    for directory in ["src", "migrations", "schema", "config", "tests", "tools", "lab"]:
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
                tracked[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    for path in [
        *(ROOT.glob("docker-compose*.yml")),
        *(ROOT.glob("*.lock")),
        ROOT / "Dockerfile",
        ROOT / "pyproject.toml",
        ROOT / "alembic.ini",
    ]:
        tracked[path.name] = sha(path.read_bytes())
    source = sha(
        b"".join(
            p.relative_to(ROOT / "src").as_posix().encode() + p.read_bytes()
            for p in sorted((ROOT / "src").rglob("*.py"))
        )
    )
    prior_path = ROOT / "RC_STATE_v0.6.0.json"
    previous = json.loads(prior_path.read_text()) if prior_path.exists() else None
    report = {
        "revision": args.revision,
        "timestamp": datetime.now(UTC).isoformat(),
        "reason": args.reason,
        "previous_revision": previous["revision"] if previous else None,
        "source_digest": source,
        "digest_algorithm": "SHA256(concat(sorted relative src Python path UTF8 + raw file bytes)); no newline canonicalization",
        "migration_head": SCHEMA_REVISION,
        "previous_stable_head": "0015_ai_decisions",
        "dependency_lock_digest": {k: v for k, v in tracked.items() if k.endswith(".lock")},
        "frozen_contract_digest": frozen["src/zhiyu/domain/contracts.py"],
        "schema_digest": {k: v for k, v in tracked.items() if k.startswith("schema/")},
        "dockerfile_digest": tracked["Dockerfile"],
        "docker_compose_digest": {k: v for k, v in tracked.items() if k.startswith("docker-compose")},
        "runtime_config_digest": {k: v for k, v in tracked.items() if k.startswith("config/")},
        "test_inventory_count": len(inventory),
        "test_inventory": inventory,
        "frozen_files": frozen,
        "controlled_files": tracked,
        "inspection": records,
        "changes_since_previous": {
            k: {"before": previous["controlled_files"].get(k), "after": tracked.get(k)}
            for k in sorted(set(tracked) | set(previous["controlled_files"]))
            if previous["controlled_files"].get(k) != tracked.get(k)
        }
        if previous
        else {},
        "known_limitations": [
            "Controlled Lab only; no production/SLA/customer/cloud/Windows/OT acceptance.",
            "4 concurrent model requests: 2 TIMEOUT with safe fallback; high-risk execution 0.",
            "Response resource sampling tail gap 153.813523 seconds; durable Outbox backlog 398200 and 45 intentional tasks.",
            "REFERENCE_GROUNDED is reference integrity, not semantic truth; AI default OFF, enabled default SHADOW.",
            "Lab HTTP containment is opt-in and still requires fresh final acceptance; no production control capability.",
            "Workspace files are untracked in Git; this freeze records bytes, not a clean committed tree.",
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    destination.write_text(payload, encoding="utf-8")
    prior_path.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "revision": args.revision,
                "source_digest": source,
                "tests": len(inventory),
                "frozen_files": len(frozen),
            }
        )
    )


if __name__ == "__main__":
    main()
