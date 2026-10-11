"""Seal candidate identity and verify retained inputs without runtime claims."""

import ast
import hashlib
import json
import tomllib
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT.parent / "artifacts/智御_Project_v0.9.0_Competition_Product.zip"
BASELINE_SHA = "a33895ca9566f89be118ea8d4dc8600e7692286e49972e39300273d29cbd14b0"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(mapping):
    return sha(json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode())


def inventory(folder, suffix=None):
    return {
        p.relative_to(ROOT).as_posix(): sha(p.read_bytes())
        for p in sorted((ROOT / folder).rglob("*"))
        if p.is_file()
        and "__pycache__" not in p.parts
        and "node_modules" not in p.parts
        and (suffix is None or p.suffix == suffix)
    }


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default="RC1_v1.0.0")
    args = parser.parse_args()
    assert sha(BASELINE.read_bytes()) == BASELINE_SHA
    with zipfile.ZipFile(BASELINE) as package:
        assert package.testzip() is None
        old_tests = {
            n.removeprefix("zhiyu_v0.9.0/"): sha(package.read(n))
            for n in package.namelist()
            if n.startswith("zhiyu_v0.9.0/tests/") and not n.endswith("/")
        }
        nodeids = [
            c.attrib["classname"].replace(".", "/") + ".py::" + c.attrib["name"]
            for c in ET.fromstring(package.read("zhiyu_v0.9.0/artifacts/v0.9/final-backend.xml")).findall(
                ".//testcase"
            )
        ]
        old_lock = tomllib.loads(package.read("zhiyu_v0.9.0/uv.lock").decode())
        old_front = json.loads(package.read("zhiyu_v0.9.0/frontend/package-lock.json"))
    assert len(nodeids) == 464
    assert all(sha((ROOT / n).read_bytes()) == h for n, h in old_tests.items())
    frozen = json.loads((ROOT / "RC_STATE_v0.6.0.json").read_text())["frozen_files"]
    assert all(sha((ROOT / n).read_bytes()) == h for n, h in frozen.items())
    current_lock = tomllib.loads((ROOT / "uv.lock").read_text())
    next(p for p in old_lock["package"] if p["name"] == "zhiyu")["version"] = "1.0.0"
    assert old_lock == current_lock
    current_front = json.loads((ROOT / "frontend/package-lock.json").read_text())
    old_front["version"] = old_front["packages"][""]["version"] = "1.0.0"
    assert old_front == current_front
    source = inventory("src", ".py")
    tools = inventory("tools", ".py")
    for name in [*source, *tools]:
        ast.parse((ROOT / name).read_text("utf-8"), filename=name)
    front = {n: h for folder in ("frontend/src", "frontend/public") for n, h in inventory(folder).items()}
    for name in (
        "package.json",
        "package-lock.json",
        "index.html",
        "vite.config.js",
        "tsconfig.json",
        "eslint.config.js",
    ):
        path = ROOT / "frontend" / name
        if path.exists():
            front[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    migrations = inventory("migrations")
    schemas = inventory("schema")
    locks = {
        name: sha((ROOT / name).read_bytes())
        for name in (
            "uv.lock",
            "requirements-runtime.lock",
            "requirements-dev.lock",
            "requirements-build.lock",
            "requirements-operator.lock",
            "frontend/package-lock.json",
        )
    }
    compose = {p.name: sha(p.read_bytes()) for p in ROOT.glob("docker-compose*.yml")}
    dockerfiles = {
        p.relative_to(ROOT).as_posix(): sha(p.read_bytes())
        for p in [
            ROOT / "Dockerfile",
            ROOT / "Dockerfile.release",
            ROOT / "lab/real-sensors/Dockerfile",
            ROOT / "lab/real-sensors/Dockerfile.wazuh-manager",
        ]
    }
    runtime = yaml.safe_load((ROOT / "docker-compose.ai.yml").read_text())["services"]["local-model"]
    controlled = {
        **source,
        **tools,
        **front,
        **migrations,
        **schemas,
        **locks,
        **dockerfiles,
        **compose,
        **inventory("tests"),
        **inventory("config"),
        **inventory("lab"),
    }
    for name in ("pyproject.toml", ".dockerignore", ".env.example", "alembic.ini"):
        controlled[name] = sha((ROOT / name).read_bytes())
    result = {
        "revision": args.revision,
        "version": "1.0.0",
        "frozen_at": datetime.now(UTC).isoformat(),
        "architecture": "2026.09.12-ai.5",
        "architecture_change": False,
        "backend_source_digest": digest(source),
        "frontend_source_digest": digest(front),
        "migration_head": "0016_lab_remediation",
        "schema_digest": digest(schemas),
        "migration_digest": digest(migrations),
        "backend_lock_digest": locks["uv.lock"],
        "frontend_lock_digest": locks["frontend/package-lock.json"],
        "locks": locks,
        "dockerfiles": dockerfiles,
        "compose": compose,
        "model_runtime": {
            "image": runtime["image"],
            "alias": "zhiyu-qwen2.5-1.5b",
            "weights_sha256": "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e",
            "revision": "91cad51170dc346986eccefdc2dd33a9da36ead9",
            "location": "LOCAL",
        },
        "prompt_policy": {n: h for n, h in source.items() if n.startswith("src/zhiyu/ai/")},
        "ai_policy_version": "ai-policy/1.0.0",
        "scenario_version": "0.9.0 unchanged",
        "scenario_definition_sha256": source["src/zhiyu/product/demo_contracts.py"],
        "report_template_sha256": source["src/zhiyu/product/reports.py"],
        "ai5_frozen_digest": digest(frozen),
        "frozen_files": frozen,
        "ui_build_digest": digest(inventory("frontend/dist")),
        "original_tests": old_tests,
        "original_test_nodeids": nodeids,
        "controlled_files": controlled,
        "known_limitations": [
            "CONTROLLED_LAB",
            "Production/Customer/SLA/Cloud/Windows Sensor/OT-ICS NOT_VALIDATED",
            "HA/Multi-tenancy NOT_IMPLEMENTED",
            "general AI semantic correctness NOT_PROVEN",
            "closed-loop superiority NOT_CLAIMED",
            "Linux host clean install NOT_RUN",
        ],
        "gate_a_review": {
            "scope": "PASS",
            "architecture_conformance": "PASS",
            "ai_value": "OPTION_B",
            "g0": "NOT_INCLUDED_IN_V1.0_CLAIM",
            "all_464_original_tests_unchanged": True,
            "frozen_files_unchanged": len(frozen),
            "dependency_changes_beyond_own_version": False,
        },
        "baseline_v09_zip_sha256": BASELINE_SHA,
        "runtime_validation": "NOT_RUN_AT_FREEZE",
    }
    destination = ROOT / "artifacts/RC_STATE_v1.0.0.json"
    destination.parent.mkdir(exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    destination.write_text(payload, encoding="utf-8")
    history = ROOT / "artifacts/v1.0/rc"
    history.mkdir(parents=True, exist_ok=True)
    (history / (args.revision + ".json")).write_text(payload, encoding="utf-8")
    (ROOT / "docs/RC_STATE_v1.0.0.md").write_text(
        "# v1.0 Release Candidate\n\n"
        + args.revision
        + "，CONTROLLED LAB，当前全版本仍 NOT PASS。\n\n机器冻结：[RC_STATE](../artifacts/RC_STATE_v1.0.0.json)。\n\n"
        + "冻结源码、前端输入与产物、迁移/schema、依赖锁、Docker/Compose、模型/Prompt/策略、场景和报告模板；原464测试与28冻结文件原始字节不变。\n\n"
        + "范围仅为版本元数据、参考部署/升级/恢复、文档与供应链交付，不新增产品功能。"
        + "No ai.5 architecture change required。AI Value选择[OPTION B](AI_VALUE_FINAL_POSITION_v1.0.md)。\n\n"
        + "冻结是候选身份，不代表运行验收通过。后续修复须记录 Finding、更新RC并重新执行受影响Gate。\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "revision": args.revision,
                "gate_a": "PASS",
                "source_digest": result["backend_source_digest"],
                "original_tests_retained": len(nodeids),
                "frozen_files_unchanged": len(frozen),
            }
        )
    )


if __name__ == "__main__":
    main()
