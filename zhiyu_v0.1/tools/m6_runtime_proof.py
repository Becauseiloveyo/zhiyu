"""Minimal public runtime provenance, explicitly excluding container credential env."""

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from m5_runtime_acceptance import MODEL_SHA
from runtime_acceptance import ROOT


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main(gate="C"):
    state_file = "m6-load-state.json" if gate == "D" else "m6-safety-state.json"
    state = json.loads((ROOT.parent / ".work" / state_file).read_text())
    directory = Path(state["directory"])
    assert directory.name == ("gate-d-001" if gate == "D" else "gate-c-002")
    assert not (directory / "runtime-provenance.json").exists(), "preserve sealed provenance"
    model = Path(state["env"]["ZHIYU_MODEL_PATH"])
    weight_hash = sha(model)
    assert weight_hash == MODEL_SHA
    containers = {}
    for service in ["api", "local-model", "postgres", "response-target"]:
        info = json.loads(
            subprocess.run(
                ["docker", "inspect", state["project"] + "-" + service + "-1"],
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            ).stdout
        )[0]
        containers[service] = {
            "id": info["Id"],
            "image": info["Image"],
            "status": info["State"]["Status"],
            "started_at": info["State"]["StartedAt"],
            "oom_killed": info["State"]["OOMKilled"],
            "restart_count": info["RestartCount"],
            "user": info["Config"]["User"],
            "entrypoint": info["Path"],
            "args": info["Args"],
            "memory_bytes": info["HostConfig"]["Memory"],
            "memory_swap_bytes": info["HostConfig"]["MemorySwap"],
            "cpu_nanos": info["HostConfig"]["NanoCpus"],
            "ports": info["HostConfig"]["PortBindings"],
            "networks": list(info["NetworkSettings"]["Networks"]),
        }
    command = containers["local-model"]["args"]
    assert command[command.index("--cache-ram") + 1] == "256"
    assert containers["local-model"]["memory_bytes"] == 4 * 1024**3
    assert not containers["local-model"]["ports"]
    assert containers["api"]["args"] == ["tools/ai_api.py"]
    source_hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT / "src").rglob("*.py"))}
    contract = ROOT / "src/zhiyu/domain/contracts.py"
    assert sha(contract) == "663a7a597d2ef03fd2db25278858c25a5ce92fe30e55f0d3f21125503a9d85fb"
    document = ROOT.parent / "zhiyu_ai5/智御_AI_CONTEXT_v2026.09.12_ai.5.md"
    manifest = json.loads((ROOT.parent / "zhiyu_ai5/MANIFEST.json").read_text(encoding="utf-8"))
    expected_doc = next(row["sha256"] for row in manifest["files"] if row["path"] == document.name)
    assert sha(document) == expected_doc
    report = {
        "status": "PASS",
        "observed_at": datetime.now(UTC).isoformat(),
        "weights_sha256": weight_hash,
        "ai5_contract_sha256": sha(contract),
        "ai5_context_document_sha256": sha(document),
        "containers": containers,
        "source_sha256": source_hashes,
        "configuration_sha256": {
            name: sha(ROOT / name) for name in ["docker-compose.yml", "docker-compose.ai.yml", "Dockerfile"]
        },
        "limits": "Current source is bind-mounted read-only over a dependency image. Final source-baked image acceptance is Gate E.",
    }
    payload = json.dumps(report, indent=2)
    for secret in [
        state["token"],
        state["password"],
        Path(state["env"]["ZHIYU_MODEL_KEY_FILE"]).read_text().strip(),
    ]:
        assert secret not in payload
    (directory / "runtime-provenance.json").write_text(payload, encoding="utf-8")
    print("PASS: model weights, actual cache/RAM bounds, container identities and frozen ai.5 hash")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", choices=["C", "D"], default="C")
    main(parser.parse_args().gate)
