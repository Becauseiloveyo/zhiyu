"""Bounded recovery monitoring; not the separate Gate D soak test."""

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from runtime_acceptance import ROOT


def main():
    state = json.loads((ROOT.parent / ".work/m6-safety-state.json").read_text())
    directory = Path(state["directory"])
    assert directory.name == "gate-c-002"
    name = state["project"] + "-local-model-1"
    started = time.monotonic()
    output = directory / "model-recovery-resources.jsonl"
    while time.monotonic() - started < 14400:
        row = {"observed_at": datetime.now(UTC).isoformat(), "elapsed_seconds": time.monotonic() - started}
        command = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        row["docker_stats"] = (
            json.loads(command.stdout)
            if command.returncode == 0 and command.stdout.strip()
            else {"returncode": command.returncode}
        )
        command = subprocess.run(
            ["docker", "inspect", name, "--format", "{{json .State}}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        row["container_state"] = (
            json.loads(command.stdout) if command.returncode == 0 else {"returncode": command.returncode}
        )
        command = subprocess.run(
            [
                "docker",
                "exec",
                name,
                "sh",
                "-c",
                "cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak /sys/fs/cgroup/memory.swap.current /sys/fs/cgroup/memory.events; cat /proc/1/status",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        row["cgroup_and_model_status"] = command.stdout
        with output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")
        if not row["container_state"].get("Running"):
            raise RuntimeError("model stopped during recovery; retained actual state")
        progress = directory / "evaluation.json"
        if progress.exists():
            try:
                complete = json.loads(progress.read_text())["status"] == "COMPLETED"
            except json.JSONDecodeError:
                complete = False  # Concurrent progress-file write; next bounded observation retries.
            if complete:
                print("PASS: recovery monitoring completed; see actual memory/CPU/OOM samples", flush=True)
                return
        time.sleep(30)
    raise RuntimeError("recovery monitoring deadline exceeded")


if __name__ == "__main__":
    main()
